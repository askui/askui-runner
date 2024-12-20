from typing import Any

from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import (
    Callable,
    Configuration,
    Dict,
    Factory,
    Selector,
    Singleton,
)

from ..core.infrastructure.askui import AskUiAccessToken
from .application import services as application_services
from .domain import services as domain_services
from .infrastructure.clock.time import TimeClock
from .infrastructure.runner.k8s_job import K8sJobRunner
from .infrastructure.runner.subprocess import SubprocessRunner
from .infrastructure.runner_jobs_queue.askui import AskUiRunnerJobsQueueService
from .infrastructure.system.sys import SysSystem
from .models import (
    Config,
    EntryPoint,
    K8sJobRunnerConfig,
    RunnerJobData,
    RunnerType,
)


def build_runner_config(
    config_dict: dict[str, Any], runner_job_data: RunnerJobData
) -> Config:
    return Config.model_validate({
        **config_dict,
        "queue": None,
        "runner": {
            **config_dict.get("runner", {}),
            "type": RunnerType.SUBPROCESS,
        },
        "entrypoint": EntryPoint.JOB,
        "job": runner_job_data,
    })


class Container(DeclarativeContainer):
    config = Configuration()
    access_token = Factory(
        AskUiAccessToken,
        access_token=config.queue.credentials.access_token,
    )
    runner_jobs_queue_service = Singleton(
        AskUiRunnerJobsQueueService,
        url=config.queue.api_url,
        headers=Dict(
            Authorization=access_token.provided.to_auth_header.call(),
        ),
    )
    runner_config_factory = Callable(
        build_runner_config,
        config_dict=config,
    )
    runner_service = Selector(
        config.runner.type,
        SUBPROCESS=Singleton(
            SubprocessRunner,
            runner_exec=config.runner.exec,
            runner_config_factory=runner_config_factory.provider,
        ),
        K8S_JOB=Singleton(
            K8sJobRunner,
            config=Factory(
                K8sJobRunnerConfig.model_validate,
                config.queue.k8s_job_runner,
            ),
            runner_config_factory=runner_config_factory.provider,
        ),
    )
    clock_service = Singleton(
        TimeClock,
    )
    system_service = Singleton(
        SysSystem,
    )
    runner_jobs_queue_polling_domain_service = Singleton(
        domain_services.RunnerJobsQueuePolling,
        config=config,
        queue=runner_jobs_queue_service,
        runner=runner_service,
        clock=clock_service,
        system=system_service,
    )
    runner_jobs_queue_polling_application_service = Singleton(
        application_services.RunnerJobsQueuePolling,
        runner_jobs_queue_polling_service=runner_jobs_queue_polling_domain_service,
    )
