import logging
import sys
from typing import Annotated

import typer

from .config import Config, read_config
from .modules.core.containers import Container as CoreContainer
from .modules.core.models import CoreConfig, ControllerConfig
from .modules.core.models import ResultsConfig, WorkflowsConfig
from .modules.queue.containers import Container as QueueContainer
from .modules.queue.models import EntryPoint


def run_jobs_from_queue(config: Config) -> None:
    container = QueueContainer()
    container.config.from_pydantic(config)
    container.runner_jobs_queue_polling_application_service().poll()


def run_job(config: Config) -> None:
    runner_core_config = build_runner_core_config(config)
    container = CoreContainer()
    container.config.from_pydantic(runner_core_config)
    exit_code = container.runner_application_service().run()
    sys.exit(exit_code)


def build_runner_core_config(config: Config):
    runner_job_data = config.job
    if runner_job_data is None:
        raise ValueError(
            'Expected job to be defined in config because entrypoint is set to "job" but found no defnition'
        )
    return CoreConfig(
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
    )


def take_entrypoint(config: Config) -> None:
    logging.basicConfig(level=config.log_level.value, format='%(asctime)s - %(levelname)s - %(message)s')
    match config.entrypoint:
        case EntryPoint.QUEUE:
            run_jobs_from_queue(config)
        case EntryPoint.JOB:
            run_job(config)


def main(
    config_json_or_config_file_path: Annotated[
        str,
        typer.Option(
            "--config", "-c", help="Path to config file (.json, .yaml, .yml supported) or config provided as json"
        ),
    ],
) -> None:
    config = read_config(config_json_or_config_file_path)
    take_entrypoint(config)


if __name__ == "__main__":
    typer.run(main)
