from typing import Annotated, Literal

import click
import typer

from askui_runner.config import read_config_dict
from .modules.agents.containers import SyncContainer
from .modules.agents.models import AgentsConfig

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
    container = SyncContainer(config=config)

    if direction == "down":
        container._agent_file_service.sync("remote", dry, delete)
        return
    if direction == "up":
        container._agent_file_service.sync("local", dry, delete)
        return


@app.command(help="Show an example configuration for the agent app")
def show_example_configuration():
    example_config = AgentsConfig.model_validate_strings(
        {
            "credentials": {
                "access_token": "your_access_token",
                "workspace_id": "your_workspace_id",
            }
        }
    ).model_dump_json(indent=2)

    print(example_config)
