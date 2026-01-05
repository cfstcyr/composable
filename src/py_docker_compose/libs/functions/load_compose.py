from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from omegaconf import OmegaConf

from py_docker_compose.libs.classes.provider import (
    Provider,
    ProviderContext,
    PythonFileProvider,
    YamlFileProvider,
)
from py_docker_compose.libs.schemas.docker_compose import DockerComposeModel


def _collect_files(src_dir: Path, src_patterns: list[str]) -> list[Path]:
    files = []
    for pattern in src_patterns:
        files.extend(src_dir.rglob(pattern))
    return sorted(files)


def load_compose(
    src_dir: Path,
    src_patterns: list[str],
    *,
    data: dict[str, Any] = {},
    providers: list[Provider] = [
        YamlFileProvider(),
        PythonFileProvider(),
    ],
) -> DockerComposeModel:
    env = Environment(
        loader=FileSystemLoader(src_dir), undefined=StrictUndefined, autoescape=True
    )
    conf = OmegaConf.create()
    files = _collect_files(src_dir, src_patterns)
    provider_context = ProviderContext(src_dir=src_dir, jinja_env=env)

    for file in files:
        for provider in providers:
            if provider.file_match(file):
                content = provider.load(file, data, context=provider_context)
                conf = OmegaConf.merge(conf, content)
                break

    return DockerComposeModel.model_validate(OmegaConf.to_container(conf, resolve=True))
