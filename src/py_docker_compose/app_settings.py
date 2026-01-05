from functools import cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file="pycd.yaml",
        yaml_file_encoding="utf-8",
    )

    default_src_dir: Path = Field(
        default=Path("./compose"),
        validation_alias=AliasChoices("default-src-dir", "src-dir"),
    )
    default_src_patterns: list[str] = Field(
        default=[
            "[!_]*.*",
            "[!_]**/[!_]*.*",
        ],
        validation_alias=AliasChoices("default-src-patterns", "src-patterns"),
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
