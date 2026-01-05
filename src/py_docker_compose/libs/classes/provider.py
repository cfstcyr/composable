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


@dataclass(kw_only=True)
class ProviderContext:
    src_dir: Path
    jinja_env: Environment


@dataclass(kw_only=True)
class Provider(ABC):
    extensions: ClassVar[ReadOnly[list[str]]] = []

    @classmethod
    def file_match(cls, path: Path) -> bool:
        return any(path.suffix == ext for ext in cls.extensions)

    @abstractmethod
    def load(
        self, path: Path, data: dict[str, Any], context: ProviderContext
    ) -> dict[str, Any] | DictConfig: ...


@dataclass
class YamlFileProvider(Provider):
    extensions: ClassVar[ReadOnly[list[str]]] = [".yaml", ".yml"]
    parse_fn: Callable[[str], dict[str, Any] | DictConfig] = field(
        default=lambda content: cast(DictConfig, OmegaConf.create(content))
    )

    def load(
        self, path: Path, data: dict[str, Any], context: ProviderContext
    ) -> dict[str, Any] | DictConfig:
        return self.parse_fn(
            context.jinja_env.get_template(
                str(path.relative_to(context.src_dir))
            ).render(**data)
        )


@dataclass
class PythonFileProvider(Provider):
    extensions: ClassVar[ReadOnly[list[str]]] = [".py"]
    symbols: list[str] = field(default_factory=lambda: ["compose", "COMPOSE"])

    def load(
        self, path: Path, data: dict[str, Any], context: ProviderContext
    ) -> dict[str, Any] | DictConfig:
        sys.path.insert(0, str(context.src_dir))

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
                            value = data
                        elif name in data:
                            value = data[name]
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
