import enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, BaseSettings, Field, validator

from ..core.models import CoreConfigBase, WorkspaceCredentials


class ContainerResource(BaseModel):
    cpu: str = Field(default="500m")
    memory: str = Field(default="1Gi")


class ContainerResources(BaseModel):
    requests: ContainerResource = Field(default=ContainerResource())
    limits: ContainerResource = Field(default=ContainerResource())


class ContainerConfig(BaseModel):
    image: str
    resources: ContainerResources = Field(default=ContainerResources())

class K8sToleration(BaseModel):
    effect: str | None
    key: str | None
    operator: str
    value: str | None
    toleration_seconds: int | None

class K8sJobRunnerConfig(BaseModel):  # TODO Adjust
    namespace: str = "dev"
    shared_memory: str = Field(default="1Gi")
    tolerations: list[K8sToleration] = Field(default=[])
    node_selector: dict[str, str] | None = Field(default=None)
    runner_container = ContainerConfig(
        image="askuigmbh/askui-runner:latest",
    )
    controller_container = ContainerConfig(
        image="askuigmbh/askui-ui-controller:v0.11.2-chrome-100.0.4896.60-amd64"
    )


class RunnerType(str, enum.Enum):
    K8S_JOB = "K8S_JOB"
    SUBPROCESS = "SUBPROCESS"


class Host(str, enum.Enum):
    ASKUI = "ASKUI"
    SELF = "SELF"


class RunnerConfig(
    CoreConfigBase
):  # TODO parts only relevant for a runner within queue -> move to queue or new model, e.g., registration data
    id: str = Field(
        str(uuid4()), description="ID of the runner"
    )  # only relevant for runner in queue
    exec: str = Field(  # only relevant for runner in queue
        "python -m askui_runner", 
        description="Command to execute the runner",
    )
    tags: list[str] = Field(  # only relevant for runner in queue
        [],
        description="Tags to filter jobs by, i.e., only picks jobs from schedules with matching tags",
    )
    type: RunnerType = Field(  # only relevant for runner in queue
        RunnerType.SUBPROCESS,
        description="Type of runner to use for running jobs",
    )
    host: Host = Field(
        default=Host.SELF, description="Host of the runner"
    )  # only relevant for runner in queue
    workflows_dir: str = Field(
        "workflows",
        description="Absolute path or path relative to {project_dir} of directory where workflows are located or to be downloaded to",
    )
    results_dir: str = Field(
        "results-allure",
        description="Absolute path or path relative to {project_dir} of directory where results are to be put in and to be uploaded from",
    )
    schedule_results_dir: str = Field(
        "results",
        description="Absolute path or path relative to {project_dir} of directory where schedule results are to be put in and to be uploaded from",
    )

class RunnerJobsFilters(BaseModel):
    tags: list[str] = []
    runner_id: str
    runner_host: Host
    workspace_id: Optional[str]


class RunnerJobsQueuePollingConfig(BaseModel):
    filters: RunnerJobsFilters
    job_timeout: int
    keep_alive: bool
    polling_interval: int


class QueueConfig(BaseModel):
    api_url: str = Field(
        "https://app-gateway-api.askui.com/prod/api/v1/workspaces/{workspace_id}/runner-jobs",  # TODO Adjust
        description="URL of the runner jobs queue API",
    )
    keep_alive: bool = Field(
        True,
        description="Whether to keep the runner alive after not being able to lease a job because none is available",
    )
    polling_interval: int = Field(
        30, description="Interval in seconds to poll for jobs from the queue"
    )
    k8s_job_runner: K8sJobRunnerConfig = Field(
        K8sJobRunnerConfig(), description="Configuration of the Kubernetes runner"
    )


class EntryPoint(str, enum.Enum):
    QUEUE = "QUEUE"
    JOB = "JOB"


class RunnerJobData(BaseModel):
    credentials: WorkspaceCredentials
    workflows: list[str]  # TODO Make easier to use by prefixing with our general prefix
    schedule_results_api_url: str | None = Field(None)
    results_api_url: str  # TODO Depending on feature toggle you don't need to provide all of these with job config
    workflows_api_url: str
    inference_api_url: str
    data: dict[str, Any] = Field(default_factory=dict)
    
    def dict(self, **kwargs) -> dict[str, Any]:
        if "exclude" in kwargs and kwargs["exclude"] is not None:
            if "data" not in kwargs["exclude"]:
                if isinstance(kwargs["exclude"], set):
                    kwargs["exclude"] |= {"data"}
                else:
                    kwargs["exclude"] |= {"data": True}
        else:
            kwargs["exclude"] = {"data"}
        return {
            **super().dict(**kwargs),
            "data": self.data,
        }


class LogLevel(str, enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Config(
    BaseSettings
):  # TODO Move into general config or create general config to separate out job entrypoint
    entrypoint: EntryPoint = Field(
        default=EntryPoint.QUEUE, description="Entry point of the runner"
    )
    runner: RunnerConfig = Field(
        default=RunnerConfig(), description="Configuration of the runner"  # type: ignore
    )
    credentials: WorkspaceCredentials | None = Field(
        description="Credentials for accessing the workspace"
    )
    queue: Optional[QueueConfig] = Field(
        default=QueueConfig(), description="Configuration of the queue"  # type: ignore
    )
    job_timeout: int = Field(
        default=3600,
        description="Timeout in seconds for a job to be completed before it is considered failed",
    )
    job: RunnerJobData | None
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Log level")

    @validator("credentials", always=True)
    def validate_credentials_set_when_self_hosted(  # pylint: disable=no-self-argument
        cls,
        v: Optional[WorkspaceCredentials],
        values,
    ) -> Optional[WorkspaceCredentials]:
        if v is None and values["runner"].host == Host.SELF:
            raise ValueError('Credentials must be given when runner is "self"-hosted')
        return v

    @validator("queue", always=True)
    def validate_queue_set_when_set_as_entrypoint(  # pylint: disable=no-self-argument
        cls,
        v: Optional[QueueConfig],
        values,
    ) -> Optional[QueueConfig]:
        if v is None and values["entrypoint"] == EntryPoint.QUEUE:
            raise ValueError(
                'Queue configuration must be given when entrypoint is "queue"'
            )
        if v is not None and values["credentials"] is not None:
            v.api_url = v.api_url.format(
                workspace_id=values["credentials"].workspace_id
            )
        return v

    @validator("job", always=True)
    def validate_job_set_when_set_as_entrypoint(  # pylint: disable=no-self-argument
        cls,
        v: Optional[RunnerJobData],
        values,
    ) -> Optional[RunnerJobData]:
        if v is None and values["entrypoint"] == EntryPoint.JOB:
            raise ValueError('Job data must be given when entrypoint is "job"')
        return v

    @property
    def runner_jobs_queue_polling_domain_service_config(
        self,
    ) -> RunnerJobsQueuePollingConfig:
        return RunnerJobsQueuePollingConfig(
            filters=RunnerJobsFilters(
                tags=self.runner.tags,
                runner_host=self.runner.host,
                runner_id=self.runner.id,
                workspace_id=self.credentials.workspace_id
                if self.credentials
                else None,
            ),
            job_timeout=self.job_timeout,
            keep_alive=self.queue.keep_alive if self.queue else False,
            polling_interval=self.queue.polling_interval if self.queue else 30,
        )

# TODO Does K8s still work?