from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Configuration, Dict, Factory, List, Selector, Singleton

from .infrastructure.askui import AskUiAccessToken
from .infrastructure.files.askui import AskUiFilesService
from .infrastructure.results_upload.askui import AskUiResultsUploadService, ChainedResultsUploadService
from .infrastructure.runner.askui import AskUIJestRunner, AskUIVisionAgentExperimentsRunner
from .infrastructure.workflows_download.askui import AskUiWorkflowsDownloadService


class Container(DeclarativeContainer):
    config = Configuration(strict=True)
    access_token = Factory(
        AskUiAccessToken,
        access_token=config.credentials.access_token,
    )
    base_http_headers = Dict(
        Authorization=access_token.provided.to_auth_header.call(),
    )
    workflows_download_service = Singleton(
        AskUiWorkflowsDownloadService,
        files_download_service=Singleton(
            AskUiFilesService,
            base_url=config.workflows.api_url,
            headers=base_http_headers,
        ),
        workflows_dir=config.workflows.dir,
        remote_workflows_paths=config.workflows.prefixes,
    )
    results_upload_service = Singleton(
        AskUiResultsUploadService,
        files_upload_service=Singleton(
            AskUiFilesService,
            base_url=config.results.api_url,
            headers=base_http_headers,
        ),
        results_dir=config.results.dir,
    )
    schedule_results_upload_service = Singleton(
        AskUiResultsUploadService,
        files_upload_service=Singleton(
            AskUiFilesService,
            base_url=config.schedule_results.api_url,
            headers=base_http_headers,
        ),
        results_dir=config.schedule_results.dir,
    )
    chained_results_upload_service = Singleton(
        ChainedResultsUploadService,
        services=List(
            results_upload_service,
            schedule_results_upload_service,
        ),
    )
    runner = Selector(
        config.runner_type,
        askui_jest_runner=Singleton(
            AskUIJestRunner,
            config=config,
            workflows_download_service=workflows_download_service,
            results_upload_service=chained_results_upload_service,
        ),
        askui_vision_agent_experiments_runner=Singleton(
            AskUIVisionAgentExperimentsRunner,
            config=config,
        ),
    )
