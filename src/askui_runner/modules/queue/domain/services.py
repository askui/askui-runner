from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel

from runner.modules.queue.models import Config, RunnerJobData, RunnerJobsFilters


class System(ABC):
    @abstractmethod
    def exit(self) -> None:
        raise NotImplementedError()


class Clock(ABC):
    @abstractmethod
    def now(self) -> int:
        raise NotImplementedError()

    @abstractmethod
    def sleep(self, seconds: int) -> None:
        raise NotImplementedError()


class RunnerJobsQueuePingResult(BaseModel):  # TODO Make names similar to our queue
    visible: int
    cancel_job: bool


class RunnerJobStatus(str, Enum):  # TODO Check how well I can differentiate
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"


class RunnerJob(BaseModel):  # TODO use datetime instead of int
    id: str
    ack: str
    status: RunnerJobStatus
    visible: int
    runner_id: str
    tries: int
    data: RunnerJobData

    def should_ping(self, now: int, ping_threshold: int) -> bool:
        return self.visible - now < ping_threshold

    def fail(self) -> None:
        self.status = RunnerJobStatus.FAILED
        self._complete()

    def cancel(self) -> None:
        self.status = RunnerJobStatus.CANCELED
        self._complete()

    def pass_(self) -> None:
        self.status = RunnerJobStatus.PASSED
        self._complete()

    def _complete(self) -> None:
        pass


class RunnerJobsQueue(ABC):
    @abstractmethod
    def lease(self, filters: RunnerJobsFilters) -> Optional[RunnerJob]:
        raise NotImplementedError()

    @abstractmethod
    def ping(self, runner_job: RunnerJob) -> RunnerJobsQueuePingResult:
        raise NotImplementedError()

    @abstractmethod
    def fail(self, runner_job: RunnerJob) -> None:
        raise NotImplementedError()

    @abstractmethod
    def cancel(self, runner_job: RunnerJob) -> None:
        raise NotImplementedError()

    @abstractmethod
    def pass_(self, runner_job: RunnerJob) -> None:
        raise NotImplementedError()


class Runner(ABC):
    @abstractmethod
    def start(self, runner_job: RunnerJob) -> None:
        raise NotImplementedError()

    @abstractmethod
    def is_running(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def has_passed(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def has_failed(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError()


class LeaseExpiredError(Exception):
    def __init__(self, job: RunnerJob):
        self.job = job
        super().__init__(f"Lease of job {job.id} with ack {job.ack} has expired.")


class RunnerJobsQueuePolling:
    def __init__(
        self,
        config: dict[str, Any],
        queue: RunnerJobsQueue,
        runner: Runner,
        clock: Clock,
        system: System,
    ):
        self.config = Config.parse_obj(
            config
        ).runner_jobs_queue_polling_domain_service_config
        self.queue = queue
        self.runner = runner
        self.clock = clock
        self.system = system
        self.leased_at = 0

    def poll(self) -> None:
        while True:
            job: RunnerJob | None = self.queue.lease(filters=self.config.filters)
            if job is None:
                self._sleep_until_next_poll_or_exit()
                continue
            self.leased_at = self.clock.now()
            self._run(job)

    def _run(self, job: RunnerJob) -> None:
        self.runner.start(runner_job=job)
        while self.runner.is_running():
            if job.should_ping(
                now=self.clock.now(), ping_threshold=60
            ):  # TODO Make ping threshold configurable
                self._ping(job)
            self.clock.sleep(
                10
            )  # TODO Put sleep time into constant and make sleep time configurable, should be lesser than the ping threshold, should be lesser than timeout
            if self.has_job_timed_out():
                self._fail_run(job)
                return
        return self._complete_run(job)

    def _fail_run(self, job: RunnerJob) -> None:
        self.runner.stop() # TODO Not stopped
        self.queue.fail(job)

    def _cancel_run(self, job: RunnerJob) -> None:
        self.runner.stop()
        self.queue.cancel(job)

    def _complete_run(self, job: RunnerJob):
        if self.runner.has_passed():
            self.queue.pass_(job)
            return
        self.queue.fail(job)

    def _ping(self, job: RunnerJob) -> None:
        try:
            return self._try_ping(job) # TODO Error seem to have killed it
        except LeaseExpiredError:
            self._fail_run(job)

    def _try_ping(self, job: RunnerJob):
        ping_result = self.queue.ping(job)
        if ping_result.cancel_job:
            self._cancel_run(job)
            return
        job.visible = ping_result.visible

    def _sleep_until_next_poll_or_exit(self) -> None:
        if not self.config.keep_alive:
            self.system.exit()
        self.clock.sleep(self.config.polling_interval)

    def get_job_timeout_timestamp(self) -> int:
        return self.leased_at + self.config.job_timeout

    def has_job_timed_out(self) -> bool:
        return self.get_job_timeout_timestamp() - self.clock.now() <= 0
