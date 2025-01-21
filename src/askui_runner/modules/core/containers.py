from functools import cached_property
from typing import Dict, List, Optional


from .infrastructure.askui import AskUiAccessToken
from .infrastructure.files.askui import AskUiFilesService
from .infrastructure.results_upload.askui import (
    AskUiResultsUploadService,
    ChainedResultsUploadService,
)
from .infrastructure.runner.askui import (
    AskUIJestRunner,
    AskUIVisionAgentExperimentsRunner,
)
from .infrastructure.workflows_download.askui import AskUiWorkflowsDownloadService
from .models import CoreConfig
from .runner import ResultsUpload


class CoreContainer:
    def __init__(self, config: CoreConfig):
        self._config = config

    @cached_property
    def _access_token(self) -> AskUiAccessToken:
        return AskUiAccessToken(access_token=self._config.credentials.access_token)

    @cached_property
    def _base_http_headers(self) -> Dict[str, str]:
        return {"Authorization": self._access_token.to_auth_header()}

    @cached_property
    def _workflows_download_service(self) -> AskUiWorkflowsDownloadService:
        files_download_service = AskUiFilesService(
            base_url=self._config.workflows.api_url,
            headers=self._base_http_headers,
        )
        return AskUiWorkflowsDownloadService(
            files_download_service=files_download_service,
            workflows_dir=self._config.workflows.dir,
            remote_workflows_paths=self._config.workflows.prefixes,
        )

    @cached_property
    def _results_upload_service(self) -> AskUiResultsUploadService:
        files_upload_service = AskUiFilesService(
            base_url=self._config.results.api_url,
            headers=self._base_http_headers,
        )
        return AskUiResultsUploadService(
            files_upload_service=files_upload_service,
            results_dir=self._config.results.dir,
        )

    @cached_property
    def _schedule_results_upload_service(self) -> Optional[AskUiResultsUploadService]:
        if self._config.schedule_results is None:
            return None

        files_upload_service = AskUiFilesService(
            base_url=self._config.schedule_results.api_url,
            headers=self._base_http_headers,
        )
        return AskUiResultsUploadService(
            files_upload_service=files_upload_service,
            results_dir=self._config.schedule_results.dir,
        )

    @cached_property
    def _chained_results_upload_service(self) -> ChainedResultsUploadService:
        services: List[ResultsUpload] = [self._results_upload_service]
        if self._schedule_results_upload_service is not None:
            services.append(self._schedule_results_upload_service)
        return ChainedResultsUploadService(
            services=services,
        )

    @cached_property
    def runner(self):
        if self._config.runner_type == "askui_jest_runner":
            return AskUIJestRunner(
                config=self._config,
                workflows_download_service=self._workflows_download_service,
                results_upload_service=self._chained_results_upload_service,
            )
        elif self._config.runner_type == "askui_vision_agent_experiments_runner":
            return AskUIVisionAgentExperimentsRunner(
                config=self._config,
            )
        else:
            raise ValueError(f"Unknown runner type: {self._config.runner_type}")
