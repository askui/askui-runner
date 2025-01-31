import json
from typing import Annotated, Literal

import click
import typer

from askui_runner.config import read_config_dict
from .modules.agents.containers import AgentsContainer
from .modules.agents.config import AgentsConfig

app = typer.Typer()


@app.command(
    help="Sync files between local and remote storage",
)
def sync(
    config_json_or_config_file_path: Annotated[
        str,
        typer.Option(
            "--config",
            "-c",
            help="Path to config file (.json, .yaml, .yml supported) or config provided as json",
        ),
    ],
    direction: Annotated[
        Literal["down", "up"],
        typer.Argument(click_type=click.Choice(["down", "up"], case_sensitive=False)),
    ],
    dry: Annotated[
        bool,
        typer.Option(
            "--dry",
            help="Displays the operations that would be performed using the specified command without actually running them",
        ),
    ] = False,
    delete: Annotated[
        bool,
        typer.Option(
            "--delete",
            help="Delete files that are not in source of truth",
        ),
    ] = False,
):
    config_dict = read_config_dict(config_json_or_config_file_path)
    config = AgentsConfig.model_validate(config_dict)
    container = AgentsContainer(config=config)

    if direction == "down":
        container.file_service.sync("remote", dry, delete)
        return
    if direction == "up":
        container.file_service.sync("local", dry, delete)
        return


@app.command(help="Prints the schema of the config file")
def print_config_schema():
    example_config = AgentsConfig.model_json_schema()

    print(json.dumps(example_config, indent=2))
