from functools import cache
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


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file="pycd.yaml",
        yaml_file_encoding="utf-8",
        nested_model_default_partial_update=True,
    )

    default_src: Src = Field(
        default=Src(
            dir=Path("./compose"),
            glob="**/*.*",
            exclude_patterns=[r"\/_"],
            version_spec=SpecifierSet(">=0"),
            version_spec_mapping={},
        ),
        validation_alias=AliasChoices("default-src", "src"),
    )
    default_data: dict[str, Any] = Field(
        default={},
        validation_alias=AliasChoices("default-data", "data"),
    )

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
            YamlConfigSettingsSource(settings_cls),
        )


@cache
def get_app_settings() -> AppSettings:
    return AppSettings()
