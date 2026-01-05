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

from composable.app_config import load_app_config
from composable.app_state import AppState
from composable.libs.functions.load_compose import load_compose
from composable.libs.functions.load_data import load_data

app = typer.Typer(
    no_args_is_help=True,
)
console = Console(stderr=True)


@app.callback()
def main(
    ctx: typer.Context,
    config_paths: list[Path] = typer.Option(
        [
            Path("./composable.yaml"),
            Path("./composable.yml"),
            Path("./cpose.yaml"),
            Path("./cpose.yml"),
        ],
        "--config",
        "-c",
        help="Path to the application configuration file.",
    ),
):
    ctx.obj = AppState(
        app_config=load_app_config(tuple(config_paths)),
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
        src=app_state.app_config.src,
        versions_spec=app_state.app_config.versions,
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
        src=app_state.app_config.src,
        versions_spec=app_state.app_config.versions,
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
