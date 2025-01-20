from functools import cached_property


from ..core.infrastructure.askui import AskUiAccessToken
from .infrastructure.clock.time import TimeClock
from .infrastructure.runner_jobs_queue.askui import AskUiRunnerJobsQueueService
from .infrastructure.runner.k8s_job import K8sJobRunner
from .infrastructure.runner.shared import RunnerConfigFactory
from .infrastructure.runner.subprocess import SubprocessRunner
from .infrastructure.system.sys import SysSystem
from .models import (
    Config,
    EntryPoint,
    K8sJobRunnerConfig,
    RunnerJobData,
    RunnerType,
)
from .queue import RunnerJobsQueuePolling


def build_runner_config(config: Config, runner_job_data: RunnerJobData) -> Config:
    return Config.model_validate(
        {
            **config.model_dump(),
            "queue": None,
            "runner": {
                **config.runner.model_dump(),
                "type": RunnerType.SUBPROCESS,
            },
            "entrypoint": EntryPoint.JOB,
            "job": runner_job_data,
        }
    )


class QueueContainer:
    def __init__(self, config: Config):
        self._config = config
        self._runner_config_factory: RunnerConfigFactory = (
            lambda runner_job_data: build_runner_config(config, runner_job_data)
        )

    @cached_property
    def _access_token(self) -> AskUiAccessToken:
        if self._config.queue is None:
            raise ValueError("Queue config is required")
        return AskUiAccessToken(
            access_token=self._config.queue.credentials.access_token
        )

    @cached_property
    def _runner_jobs_queue_service(self) -> AskUiRunnerJobsQueueService:
        if self._config.queue is None:
            raise ValueError("Queue config is required")
        return AskUiRunnerJobsQueueService(
            url=self._config.queue.api_url,
            headers={"Authorization": self._access_token.to_auth_header()},
        )

    @cached_property
    def _runner_service(self):
        if self._config.runner.type == RunnerType.SUBPROCESS:
            return SubprocessRunner(
                runner_exec=self._config.runner.exec,
                runner_config_factory=self._runner_config_factory,
            )
        elif self._config.runner.type == RunnerType.K8S_JOB:
            return K8sJobRunner(
                config=K8sJobRunnerConfig.model_validate(
                    self._config.queue.k8s_job_runner
                ),
                runner_config_factory=self._runner_config_factory,
            )
        else:
            raise ValueError(f"Unknown runner type: {self._config.runner.type}")

    @cached_property
    def _clock_service(self) -> TimeClock:
        return TimeClock()

    @cached_property
    def _system_service(self) -> SysSystem:
        return SysSystem()

    @cached_property
    def runner_jobs_queue_polling(self) -> RunnerJobsQueuePolling:
        return RunnerJobsQueuePolling(
            config=self._config.runner_jobs_queue_polling_config,
            queue=self._runner_jobs_queue_service,
            runner=self._runner_service,
            clock=self._clock_service,
            system=self._system_service,
        )
