import subprocess  # noqa: S404
from pathlib import Path
from sys import stdout
from tempfile import NamedTemporaryFile
from typing import Any, cast

import typer
import yaml
from omegaconf import OmegaConf
from rich.console import Console

from py_docker_compose.app_settings import get_app_settings
from py_docker_compose.app_state import AppState
from py_docker_compose.libs.functions.load_compose import load_compose

app = typer.Typer(
    no_args_is_help=True,
)
app_settings = get_app_settings()
console = Console(stderr=True)


@app.callback()
def main(
    ctx: typer.Context,
    src_dir: Path = typer.Option(
        default=app_settings.default_src_dir,
        help="Source directory to find source docker-compose files.",
    ),
    src_patterns: list[str] = typer.Option(
        default=app_settings.default_src_patterns,
        help="Source pattern(s) to find source docker-compose files.",
    ),
):
    ctx.obj = AppState(src_dir=src_dir, src_patterns=src_patterns)


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
):
    app_state: AppState = ctx.obj

    resolved_data = cast(
        dict[str, Any],
        OmegaConf.to_container(
            OmegaConf.merge(app_settings.default_data, OmegaConf.from_dotlist(data)),
            resolve=True,
        ),
    )
    compose = load_compose(
        src_dir=app_state.src_dir,
        src_patterns=app_state.src_patterns,
        data=resolved_data,
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

        subprocess.run(args, check=True)  # noqa: S603


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
):
    app_state: AppState = ctx.obj

    resolved_data = cast(
        dict[str, Any],
        OmegaConf.to_container(
            OmegaConf.merge(app_settings.default_data, OmegaConf.from_dotlist(data)),
            resolve=True,
        ),
    )
    compose = load_compose(
        src_dir=app_state.src_dir,
        src_patterns=app_state.src_patterns,
        data=resolved_data,
    )

    console.print("[bold green]Generated Docker Compose YAML:[/]")

    stdout.write(
        yaml.dump(
            compose.model_dump(mode="json", exclude_unset=True, exclude_none=True),
            width=float("inf"),
        )
    )
    stdout.flush()
