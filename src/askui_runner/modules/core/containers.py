from dependency_injector import containers, providers

from .application import services as application_services
from .infrastructure.askui import AskUiAccessToken
from .infrastructure.files.askui import AskUiFilesService
from .infrastructure.results_upload.askui import AskUiResultsUploadService
from .infrastructure.runner.askui import AskUiJestRunnerService
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
    runner_domain_service = providers.Singleton(
        AskUiJestRunnerService,
        config=config,
        workflows_download_service=workflows_download_service,
        results_upload_service=results_upload_service,
    )
    runner_application_service = providers.Singleton(
        application_services.Runner,
        runner=runner_domain_service,
    )
