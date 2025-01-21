import json
import os
import subprocess
import tempfile
from typing import Optional

from ...queue import Runner, RunnerJob
from .shared import RunnerConfigFactory


def stop(process: subprocess.Popen[bytes], timeout: int = 30) -> None:
    try:
        process.terminate()
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()


class SubprocessRunner(Runner):
    def __init__(
        self,
        runner_exec: str,
        runner_config_factory: RunnerConfigFactory,
    ):
        self.runner_exec = runner_exec
        self.runner_config_factory = runner_config_factory
        self.process: Optional[subprocess.Popen[bytes]] = None

    def _create_config_file(self, runner_job: RunnerJob) -> str:
        """Creates a temporary config file for the runner and returns its path."""
        runner_config = self.runner_config_factory(runner_job_data=runner_job.data)
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".json"
        ) as config_file:
            json.dump(runner_config.model_dump(), config_file)
            return config_file.name

    def _delete_config_file(self, config_file_name: str) -> None:
        os.remove(config_file_name)

    def start(self, runner_job: RunnerJob) -> None:
        config_file_name = self._create_config_file(runner_job)
        command = [*self.runner_exec.split(" "), "--config", config_file_name]
        self.process = subprocess.Popen(command)

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def has_passed(self) -> bool:
        return self.process is not None and self.process.poll() == 0

    def has_failed(self) -> bool:
        if self.process is None:
            return False
        return_code = self.process.poll()
        return return_code is not None and return_code > 0

    def stop(self) -> None:
        if self.process is None:
            return
        stop(process=self.process)
