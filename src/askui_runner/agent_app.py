from typing import Annotated

import click
import typer

from askui_runner.config import read_config_dict
from .modules.core.containers import SyncContainer
from .modules.core.models import AgentConfig

app = typer.Typer()


@app.command()
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
        str,
        typer.Argument(click_type=click.Choice(["Down", "Up"], case_sensitive=False)),
    ],
    dry: Annotated[
        bool,
        typer.Option(
            "--dry",
            help="Dry run, List all actions without executing",
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
    container = SyncContainer(config_dict=config_dict)

    if direction == "Down":
        container._agent_file_service.sync("remote", dry, delete)
    elif direction == "Up":
        container._agent_file_service.sync("local", dry, delete)
    else:
        raise typer.BadParameter(
            "Sync direction should be either 'Download' or 'Upload'"
        )


@app.command()
def generate_config(
    output_file_path: str = typer.Option(
        ..., "--output", "-o", help="Path to json output config file"
    ),
):
    AgentConfig.model_validate_strings(
        {
            "credentials": {
                "access_token": "your_access_token",
                "workspace_id": "your_workspace_id",
            }
        }
    ).dump_example_config_to_json_file(output_file_path)
