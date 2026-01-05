from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from packaging.specifiers import SpecifierSet
from pydantic import AliasChoices, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from py_docker_compose.libs.schemas.src import Src


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        nested_model_default_partial_update=True,
    )

    src: Src = Field(
        default=Src(
            dir=Path("./compose"),
            glob="**/*.*",
            exclude_patterns=[r"\/_"],
            version_spec=SpecifierSet(">=0"),
            version_spec_mapping={},
        ),
        validation_alias=AliasChoices("src", "source"),
    )
    data: dict[str, Any] = Field(
        default={},
        validation_alias=AliasChoices("data", "globals", "values"),
    )
    data_files: list[Path] = Field(
        default=[
            Path("data.yaml"),
            Path("data.yml"),
            Path("globals.yaml"),
            Path("globals.yml"),
            Path("values.yaml"),
            Path("values.yml"),
        ],
        validation_alias=AliasChoices(
            "data_files",
            "globals_files",
            "values_files",
            "data-files",
            "globals-files",
            "values-files",
        ),
    )


@lru_cache(maxsize=1)
def load_app_config(paths: Sequence[Path]) -> AppConfig:
    class LoadedAppConfig(AppConfig):
        @classmethod
        def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ) -> tuple[PydanticBaseSettingsSource, ...]:
            return (
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
                *(
                    YamlConfigSettingsSource(
                        settings_cls, yaml_file=path, yaml_file_encoding="utf-8"
                    )
                    for path in paths
                ),
            )

    return LoadedAppConfig()
