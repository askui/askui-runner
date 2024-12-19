from dependency_injector import containers, providers

from .infrastructure.askui import AskUiAccessToken
from .infrastructure.files.askui import AskUiFilesService
from .infrastructure.results_upload.askui import AskUiResultsUploadService, ChainedResultsUploadService
from .infrastructure.runner.askui import AskUIJestRunner, AskUIVisionAgentExperimentsRunner
from .infrastructure.workflows_download.askui import AskUiWorkflowsDownloadService


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)
    access_token = providers.Factory(
        AskUiAccessToken,
        access_token=config.credentials.access_token,
    )
    base_http_headers = providers.Dict(
        Authorization=access_token.provided.to_auth_header.call(),
    )
    workflows_download_service = providers.Singleton(
        AskUiWorkflowsDownloadService,
        files_download_service=providers.Singleton(
            AskUiFilesService,
            base_url=config.workflows.api_url,
            headers=base_http_headers,
        ),
        workflows_dir=config.workflows.dir,
        remote_workflows_paths=config.workflows.prefixes,
    )
    results_upload_service = providers.Singleton(
        AskUiResultsUploadService,
        files_upload_service=providers.Singleton(
            AskUiFilesService,
            base_url=config.results.api_url,
            headers=base_http_headers,
        ),
        results_dir=config.results.dir,
    )
    schedule_results_upload_service = providers.Singleton(
        AskUiResultsUploadService,
        files_upload_service=providers.Singleton(
            AskUiFilesService,
            base_url=config.schedule_results.api_url,
            headers=base_http_headers,
        ),
        results_dir=config.schedule_results.dir,
    )
    chained_results_upload_service = providers.Singleton(
        ChainedResultsUploadService,
        services=providers.List(
            results_upload_service,
            schedule_results_upload_service,
        ),
    )
    runner = providers.Selector(
        config.runner_type,
        askui_jest_runner=providers.Singleton(
            AskUIJestRunner,
            config=config,
            workflows_download_service=workflows_download_service,
            results_upload_service=chained_results_upload_service,
        ),
        askui_vision_agent_experiments_runner=providers.Singleton(
            AskUIVisionAgentExperimentsRunner,
            config=config,
        ),
    )
