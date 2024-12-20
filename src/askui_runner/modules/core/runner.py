import enum
import tempfile
from abc import ABC, abstractmethod
from typing import Any

from .models import CoreConfig, FeatureToggles


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
    ) -> None:
        self.config = CoreConfig.model_validate(config)

    @property
    def enable(self) -> FeatureToggles:
        return self.config.enable

    def run(self) -> RunWorkflowsResult:
        result = RunWorkflowsResult.SUCCESS
        with tempfile.TemporaryDirectory(
            prefix="askui-runner-",
        ) as dir_path:
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
        pass

    def run_workflows(self) -> RunWorkflowsResult:
        return RunWorkflowsResult.SUCCESS

    def upload_results(self) -> None:
        pass

    def teardown(self) -> None:
        pass
