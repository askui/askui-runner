from typing import Optional

import requests

import runner.modules.queue.models

from ...domain import services
from ...domain.services import RunnerJob, RunnerJobsQueuePingResult


class AskUiRunnerJobsQueueService(services.RunnerJobsQueue):
    def __init__(self, url: str, headers: dict[str, str]):
        self.url = url
        self.headers = headers

    def lease(
        self, filters: runner.modules.queue.models.RunnerJobsFilters
    ) -> Optional[RunnerJob]:
        response = requests.post(
            f"{self.url}/lease",
            headers=self.headers,
            timeout=5,
            params=filters.dict(),
        )
        if response.status_code != 200:
            response.raise_for_status()
        if response.json() is None:
            return
        return RunnerJob(**response.json())

    def ping(self, runner_job: RunnerJob) -> RunnerJobsQueuePingResult:
        response = requests.post(
            f"{self.url}/ping",
            params={"ack": runner_job.ack},
            headers=self.headers,
            timeout=5,
        )
        if response.status_code != 200:
            response.raise_for_status()
        return RunnerJobsQueuePingResult(**response.json())

    def fail(self, runner_job: RunnerJob) -> None:
        runner_job.fail()
        self.complete(runner_job)

    def cancel(self, runner_job: RunnerJob) -> None:
        runner_job.cancel()
        self.complete(runner_job)

    def pass_(self, runner_job: RunnerJob) -> None:
        runner_job.pass_()
        self.complete(runner_job)

    def complete(self, runner_job: RunnerJob) -> None:
        requests.post(
            f"{self.url}/complete",
            params={"ack": runner_job.ack},
            headers=self.headers,
            json={"status": runner_job.status.value},
            timeout=5,
        )
