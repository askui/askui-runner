from typing import Protocol

from ...models import Config as RunnerConfig
from ...models import RunnerJobData


class RunnerConfigFactory(Protocol):
    def __call__(self, runner_job_data: RunnerJobData) -> RunnerConfig: ...
