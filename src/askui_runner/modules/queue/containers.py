from typing import Any

from dependency_injector import containers, providers

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
    Host,
    K8sJobRunnerConfig,
    RunnerJobData,
    RunnerType,
)


def build_runner_config(
    config_dict: dict[str, Any], runner_job_data: RunnerJobData
) -> Config:
    config = Config.parse_obj(config_dict)
    config.queue = None
    config.runner.type = RunnerType.SUBPROCESS
    config.entrypoint = EntryPoint.JOB
    config.credentials = runner_job_data.credentials
    config.job = runner_job_data
    return config


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    access_token = providers.Selector(
        config.runner.host,
        **{
            Host.SELF: providers.Factory(
                AskUiAccessToken,
                access_token=config.credentials.access_token,
            ),
            Host.ASKUI: providers.Factory(
                AskUiAccessToken,
            ),
        },
    )
    runner_jobs_queue_service = providers.Singleton(
        AskUiRunnerJobsQueueService,
        url=config.queue.api_url,
        headers=providers.Dict(
            Authorization=access_token.provided.to_auth_header.call(),
        ),
    )
    runner_config_factory = providers.Callable(
        build_runner_config,
        config_dict=config,
    )
    runner_service = providers.Selector(
        config.runner.type,
        **{
            RunnerType.SUBPROCESS: providers.Singleton(
                SubprocessRunner,
                runner_exec=config.runner.exec,
                runner_config_factory=runner_config_factory.provider,
            ),
            RunnerType.K8S_JOB: providers.Singleton(
                K8sJobRunner,
                config=providers.Factory(
                    K8sJobRunnerConfig.parse_obj,
                    config.queue.k8s_job_runner,
                ),
                runner_config_factory=runner_config_factory.provider,
            ),
        },
    )
    clock_service = providers.Singleton(
        TimeClock,
    )
    system_service = providers.Singleton(
        SysSystem,
    )
    runner_jobs_queue_polling_domain_service = providers.Singleton(
        domain_services.RunnerJobsQueuePolling,
        config=config,
        queue=runner_jobs_queue_service,
        runner=runner_service,
        clock=clock_service,
        system=system_service,
    )
    runner_jobs_queue_polling_application_service = providers.Singleton(
        application_services.RunnerJobsQueuePolling,
        runner_jobs_queue_polling_service=runner_jobs_queue_polling_domain_service,
    )
