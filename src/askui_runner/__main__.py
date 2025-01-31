import logging
import sys
from typing import Annotated

import typer

from .config import Config, read_config
from .modules.core.containers import CoreContainer
from .modules.core.models import CoreConfig, ControllerConfig, ScheduleResultsConfig
from .modules.core.models import ResultsConfig, WorkflowsConfig
from .modules.queue.containers import QueueContainer
from .modules.queue.models import EntryPoint
from .agent_app import app as agent_app

app = typer.Typer(add_completion=False)


def run_jobs_from_queue(config: Config) -> None:
    container = QueueContainer(config=config)
    container.runner_jobs_queue_polling.poll()


def run_job(config: Config) -> None:
    runner_core_config = build_runner_core_config(config)
    container = CoreContainer(config=runner_core_config)
    exit_code = container.runner.run()
    sys.exit(exit_code)


def build_runner_core_config(config: Config):
    runner_job_data = config.job
    if runner_job_data is None:
        raise ValueError(
            'Expected job to be defined in config because entrypoint is set to "job" but found no defnition'
        )
    return CoreConfig(
        command=config.runner.command,
        runner_type=runner_job_data.data.get("runner_type", "askui_jest_runner"),
        controller=ControllerConfig(
            host=config.runner.controller.host,
            port=config.runner.controller.port,
        ),
        credentials=runner_job_data.credentials,
        enable=config.runner.enable,
        inference_api_url=runner_job_data.inference_api_url,
        project_dir=config.runner.project_dir,
        workflows=WorkflowsConfig(
            api_url=runner_job_data.workflows_api_url,
            dir=config.runner.workflows_dir,
            prefixes=runner_job_data.workflows,
        ),
        results=ResultsConfig(
            api_url=runner_job_data.results_api_url,
            dir=config.runner.results_dir,
        ),
        schedule_results=ScheduleResultsConfig(
            api_url=runner_job_data.schedule_results_api_url or "",
            dir=config.runner.schedule_results_dir,
        ),
        data=runner_job_data.data,
    )


def take_entrypoint(config: Config) -> None:
    logging.basicConfig(
        level=config.log_level.value, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    match config.entrypoint:
        case EntryPoint.QUEUE:
            run_jobs_from_queue(config)
        case EntryPoint.JOB:
            run_job(config)


@app.command(name="start")
def main(
    config_json_or_config_file_path: Annotated[
        str,
        typer.Option(
            "--config",
            "-c",
            help="Path to config file (.json, .yaml, .yml supported) or config provided as json",
        ),
    ],
) -> None:
    config = read_config(config_json_or_config_file_path)
    take_entrypoint(config)


app.add_typer(agent_app, name="agent")

if __name__ == "__main__":
    logging.basicConfig(
        level="INFO", format="%(asctime)s - %(levelname)s - %(message)s"
    )
    app()
