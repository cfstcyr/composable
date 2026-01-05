import json
import subprocess  # noqa: S404
from enum import Enum
from pathlib import Path
from sys import stdout
from tempfile import NamedTemporaryFile
from typing import Any, cast

import typer
import yaml
from omegaconf import OmegaConf
from rich.console import Console

from py_docker_compose.app_config import load_app_config
from py_docker_compose.app_state import AppState
from py_docker_compose.libs.functions.load_compose import load_compose
from py_docker_compose.libs.functions.load_data import load_data

app = typer.Typer(
    no_args_is_help=True,
)
console = Console(stderr=True)


@app.callback()
def main(
    ctx: typer.Context,
    config_paths: list[Path] = typer.Option(
        [
            Path("./pydc.yaml"),
            Path("./pydc.yml"),
            Path("./py-docker-compose.yaml"),
            Path("./py-docker-compose.yml"),
        ],
        "--config",
        "-c",
        help="Path to the application configuration file.",
    ),
    src_dir: Path | None = typer.Option(
        None,
        help="Source directory to find source docker-compose files.",
    ),
    src_glob: str | None = typer.Option(
        None,
        help="Source glob to find source docker-compose files.",
    ),
    src_exclude_patterns: list[str] | None = typer.Option(
        None,
        help="Source exclude patterns to ignore source docker-compose files.",
    ),
    src_version_spec: str | None = typer.Option(
        None,
        help="Source version spec to select source docker-compose files.",
    ),
    src_version_spec_mapping: list[str] | None = typer.Option(
        None,
        help="Source version spec mapping to select source docker-compose files. Format: key:specifier",
    ),
):
    app_config = load_app_config(tuple(config_paths))
    src_args = {
        "dir": src_dir,
        "glob": src_glob,
        "exclude_patterns": src_exclude_patterns,
        "version_spec": src_version_spec,
        "version_spec_mapping": src_version_spec_mapping,
    }
    ctx.obj = AppState(
        src=app_config.src.model_copy(
            update={k: v for k, v in src_args.items() if v is not None}
        ),
        app_config=app_config,
    )


@app.command()
def compose(
    ctx: typer.Context,
    command: list[str] = typer.Argument(
        ...,
        help="Command and arguments to pass to docker-compose.",
    ),
    *,
    data: list[str] = typer.Option(
        [],
        "-d",
        "--data",
        help="Additional data to pass to Jinja2 templates in key=value format.",
    ),
    dry_run: bool = typer.Option(
        False,  # noqa: FBT003
        "--dry-run",
        help="If set, only output the generated docker-compose YAML without executing the command.",
    ),
):
    app_state: AppState = ctx.obj

    loaded_data = load_data(
        data=[
            app_state.app_config.data,
            cast(dict[str, Any], dict(OmegaConf.from_dotlist(data))),
        ],
        data_files=app_state.app_config.data_files,
    )
    compose = load_compose(
        src=app_state.src,
        data=loaded_data,
    )

    with NamedTemporaryFile(
        "w+", dir=".", prefix="docker-compose-", suffix=".yaml", encoding="utf-8"
    ) as temp_file:
        yaml.dump(
            compose.model_dump(mode="json", exclude_unset=True, exclude_none=True),
            temp_file,
            width=float("inf"),
        )
        temp_file.flush()

        args = ["docker", "compose", "-f", temp_file.name] + command
        console.print(
            f"[green][bold]Running[/bold] '[italic]{' '.join(args)}[/italic]'[/green]"
        )

        if not dry_run:
            subprocess.run(args, check=False)  # noqa: S603
        else:
            console.print("[yellow]Dry run enabled, not executing command.[/yellow]")


class OutputFormat(Enum):
    YAML = "yaml"
    JSON = "json"


@app.command()
def output(
    ctx: typer.Context,
    *,
    data: list[str] = typer.Option(
        [],
        "-d",
        "--data",
        help="Additional data to pass to Jinja2 templates in key=value format.",
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.YAML,
        "--format",
        "-f",
        help="Output format.",
    ),
):
    app_state: AppState = ctx.obj

    loaded_data = load_data(
        data=[
            app_state.app_config.data,
            cast(dict[str, Any], OmegaConf.to_container(OmegaConf.from_dotlist(data))),
        ],
        data_files=app_state.app_config.data_files,
    )
    compose = load_compose(
        src=app_state.src,
        data=loaded_data,
    )

    console.print("[bold green]Generated Docker Compose YAML:[/]")

    result: str
    match output_format:
        case OutputFormat.JSON:
            result = json.dumps(
                compose.model_dump(mode="json", exclude_unset=True, exclude_none=True),
                indent=2,
            )
        case OutputFormat.YAML:
            result = yaml.dump(
                compose.model_dump(mode="json", exclude_unset=True, exclude_none=True),
                width=float("inf"),
            )

    stdout.write(result)
    stdout.flush()
