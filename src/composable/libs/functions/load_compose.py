import re
from pathlib import Path
from typing import Any

from omegaconf import OmegaConf
from packaging.version import Version

from composable.libs.classes.provider import (
    Provider,
    ProviderContext,
    PythonFileProvider,
    YamlFileProvider,
)
from composable.libs.schemas.docker_compose import DockerComposeModel
from composable.libs.schemas.src import Src
from composable.libs.schemas.versions_spec import Versions


def _collect_files(
    src: Src,
    versions_spec: Versions | None = None,
    *,
    file_name_pattern: str = r"^(?P<name>.+?)(?:[._:@]+v(?P<version>[0-9]+(?:\.[0-9]+)*(?:[\w_-]+)?))?$",
) -> list[Path]:
    files = [file for file in src.list_files()]
    files_index: dict[str, tuple[Version | None, Path]] = {}

    for file in files:
        file_path = (
            file.relative_to(Path.cwd())
            if file.is_relative_to(Path.cwd())
            else file.absolute()
        )
        if file_path.suffix == ".jinja":
            file_path = Path(str(file_path.with_suffix("")))

        file_name = str(file_path.with_suffix(""))
        match = re.match(file_name_pattern, file_name)

        if match is None:
            match_key = file_name
            match_version = None
        else:
            match_key = match.group("name")
            match_version = Version(match.group("version") or "0")

        if versions_spec and match_version:
            if not versions_spec.spec.contains(match_version):
                continue
            if (
                match_key in versions_spec.spec_mapping
                and not versions_spec.spec_mapping[match_key].contains(match_version)
            ):
                continue

        if match_key not in files_index:
            files_index[match_key] = (match_version, file)
        else:
            existing_version, _ = files_index[match_key]
            if match_version is not None and (
                existing_version is None or match_version > existing_version
            ):
                files_index[match_key] = (match_version, file)

    return sorted(file for _, file in files_index.values())


def load_compose(
    src: Src,
    versions_spec: Versions | None = None,
    *,
    data: dict[str, Any] = {},
    providers: list[Provider] = [
        YamlFileProvider(),
        PythonFileProvider(),
    ],
    invalid_file_format_ok: bool = False,
) -> DockerComposeModel:
    files = _collect_files(src, versions_spec)
    provider_context = ProviderContext(src=src, data=data)

    conf = OmegaConf.create()

    for file in files:
        for provider in providers:
            if provider.file_match(file):
                conf = OmegaConf.merge(
                    conf, provider.load(file, context=provider_context)
                )
                break
        else:
            if not invalid_file_format_ok:
                raise ValueError(f"No provider found for file: {file}")

    return DockerComposeModel.model_validate(OmegaConf.to_container(conf, resolve=True))
