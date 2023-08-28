import enum
import tempfile
from abc import ABC, abstractmethod
from typing import Any

from ..models import Config, FeatureToggles


class WorkflowsDownload(ABC):
    @abstractmethod
    def download(self) -> None:
        raise NotImplementedError()


class ResultsUpload(ABC):
    @abstractmethod
    def upload(self) -> None:
        raise NotImplementedError()


class RunWorkflowsResult(int, enum.Enum):
    SUCCESS = 0
    FAILURE = 1


class Runner:
    def __init__(
        self,
        config: dict[str, Any],
        workflows_download_service: WorkflowsDownload,
        results_upload_service: ResultsUpload,
    ) -> None:
        self.config = Config.parse_obj(config)
        self.workflows_download_service = workflows_download_service
        self.results_upload_service = results_upload_service

    @property
    def enable(self) -> FeatureToggles:
        return self.config.enable

    def run(self) -> RunWorkflowsResult:
        result = RunWorkflowsResult.SUCCESS
        with tempfile.TemporaryDirectory(
            suffix="askui-runner-"
        ) as dir_path:  # TODO: Make configurable and move into the infrastructure layer
            if self.enable.setup:
                self.setup(dir_path=dir_path)
            if self.enable.download_workflows:
                self.download_workflows()
            if self.enable.run_workflows:
                result = self.run_workflows()
            if self.enable.upload_results:
                self.upload_results()
            if self.enable.teardown:
                self.teardown()
        return result

    def setup(self, dir_path: str) -> None:
        pass

    def download_workflows(self) -> None:
        self.workflows_download_service.download()

    def run_workflows(self) -> RunWorkflowsResult:
        return RunWorkflowsResult.SUCCESS

    def upload_results(self) -> None:
        self.results_upload_service.upload()

    def teardown(self) -> None:
        pass
