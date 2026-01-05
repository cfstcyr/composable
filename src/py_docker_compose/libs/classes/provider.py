import importlib.util
import inspect
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, ReadOnly, cast

from jinja2 import Environment
from omegaconf import DictConfig, OmegaConf
from pydantic import BaseModel, TypeAdapter

from py_docker_compose.libs.schemas.src import Src


@dataclass(kw_only=True)
class ProviderContext:
    src: Src
    jinja_env: Environment
    data: dict[str, Any]


@dataclass(kw_only=True)
class Provider(ABC):
    extensions: ClassVar[ReadOnly[set[str]]] = set()

    @classmethod
    def file_match(cls, path: Path) -> bool:
        return any(str(path).endswith(ext) for ext in cls.extensions)

    @abstractmethod
    def load(
        self, path: Path, context: ProviderContext
    ) -> dict[str, Any] | DictConfig: ...


@dataclass
class YamlFileProvider(Provider):
    extensions: ClassVar[ReadOnly[set[str]]] = {
        ".yaml",
        ".yml",
        ".yaml.jinja",
        ".yml.jinja",
    }
    parse_fn: Callable[[str], dict[str, Any] | DictConfig] = field(
        default=lambda content: cast(DictConfig, OmegaConf.create(content))
    )

    def load(self, path: Path, context: ProviderContext) -> dict[str, Any] | DictConfig:
        print(
            context.jinja_env.get_template(
                str(path.relative_to(context.src.dir))
            ).render(**context.data)
        )
        return self.parse_fn(
            context.jinja_env.get_template(
                str(path.relative_to(context.src.dir))
            ).render(**context.data)
        )


@dataclass
class PythonFileProvider(Provider):
    extensions: ClassVar[ReadOnly[set[str]]] = {".py"}
    symbols: list[str] = field(default_factory=lambda: ["compose", "COMPOSE"])

    def load(self, path: Path, context: ProviderContext) -> dict[str, Any] | DictConfig:
        sys.path.insert(0, str(context.src.dir))

        try:
            spec = importlib.util.spec_from_file_location(name="module", location=path)
            if spec is None or spec.loader is None:
                return {}

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)

        for symbol in self.symbols:
            if hasattr(module, symbol):
                compose = getattr(module, symbol)

                if isinstance(compose, dict):
                    return compose
                if callable(compose):
                    args = {}

                    sig = inspect.signature(compose)
                    for name, param in sig.parameters.items():
                        if name == "data":
                            value = context.data
                        elif name in context.data:
                            value = context.data[name]
                        else:
                            continue

                        type_adapter = TypeAdapter(param.annotation)
                        args[name] = type_adapter.validate_python(value)

                    result = compose(**args)
                    if isinstance(result, BaseModel):
                        result = result.model_dump()

                    if not isinstance(result, (dict, DictConfig)):
                        raise TypeError(
                            f"Unsupported compose return type: {type(result)}"
                        )

                    return result

                raise TypeError(f"Unsupported compose type: {type(compose)}")

        raise AttributeError(f"No compose symbol found in {path}: {self.symbols}")
