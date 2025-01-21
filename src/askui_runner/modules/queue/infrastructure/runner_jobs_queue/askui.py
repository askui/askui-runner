import logging
from typing import Optional

import requests

from ...queue import RunnerJob, RunnerJobsQueue, RunnerJobsQueuePingResult
from ...models import RunnerJobsFilters

REQUEST_TIMEOUT_IN_S = 60


class AskUiRunnerJobsQueueService(RunnerJobsQueue):
    def __init__(self, url: str, headers: dict[str, str]):
        self.url = url
        self.headers = headers

    def lease(self, filters: RunnerJobsFilters) -> Optional[RunnerJob]:
        try:
            response = requests.post(
                f"{self.url}/lease",
                headers=self.headers,
                timeout=REQUEST_TIMEOUT_IN_S,
                params=filters.model_dump(),
            )
            if response.status_code != 200:
                response.raise_for_status()
            json = response.json()
            if json:
                return RunnerJob(**json)
        except Exception as error:
            logging.error(error)
        return None

    def ping(self, runner_job: RunnerJob) -> RunnerJobsQueuePingResult:
        response = requests.post(
            f"{self.url}/ping",
            params={"ack": runner_job.ack},
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_IN_S,
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
        try:
            requests.post(
                f"{self.url}/complete",
                params={"ack": runner_job.ack},
                headers=self.headers,
                json={"status": runner_job.status.value},
                timeout=REQUEST_TIMEOUT_IN_S,
            )
        except Exception as error:
            logging.error(error)
