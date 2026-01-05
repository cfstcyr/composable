import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from omegaconf import OmegaConf
from packaging.version import Version

from py_docker_compose.libs.classes.provider import (
    Provider,
    ProviderContext,
    PythonFileProvider,
    YamlFileProvider,
)
from py_docker_compose.libs.schemas.docker_compose import DockerComposeModel
from py_docker_compose.libs.schemas.src import Src


def _collect_files(
    src: Src,
    *,
    file_name_pattern: str = r"^(?P<name>.+?)(?:[._:]+v(?P<version>[0-9]+(?:\.[0-9]+)*(?:[\w_-]+)?))?$",
) -> list[Path]:
    files = src.dir.glob(src.glob)

    for pattern in src.exclude_patterns:
        files = [f for f in files if not re.search(pattern, str(f))]

    files_index: dict[str, tuple[Version | None, Path]] = {}

    for file in files:
        file_name = str(file.relative_to(src.dir).with_suffix(""))
        match = re.match(file_name_pattern, file_name)

        if match is None:
            key = file_name
            version = None
        else:
            key = match.group("name")
            version = Version(match.group("version") or "0")

        if version:
            if not src.version_spec.contains(version):
                continue
            if key in src.version_spec_mapping and not src.version_spec_mapping[
                key
            ].contains(version):
                continue

        if key not in files_index:
            files_index[key] = (version, file)
        else:
            existing_version, _ = files_index[key]
            if version is not None and (
                existing_version is None or version > existing_version
            ):
                files_index[key] = (version, file)

    return sorted(file for _, file in files_index.values())


def load_compose(
    src: Src,
    *,
    data: dict[str, Any] = {},
    providers: list[Provider] = [
        YamlFileProvider(),
        PythonFileProvider(),
    ],
    invalid_file_format_ok: bool = False,
) -> DockerComposeModel:
    env = Environment(
        loader=FileSystemLoader(src.dir), undefined=StrictUndefined, autoescape=True
    )
    conf = OmegaConf.create()
    files = _collect_files(src)
    provider_context = ProviderContext(src=src, jinja_env=env, data=data)

    for file in files:
        for provider in providers:
            if provider.file_match(file):
                content = provider.load(file, context=provider_context)
                conf = OmegaConf.merge(conf, content)
                break
        else:
            if not invalid_file_format_ok:
                raise ValueError(f"No provider found for file: {file}")

    return DockerComposeModel.model_validate(OmegaConf.to_container(conf, resolve=True))
