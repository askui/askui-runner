from functools import cached_property
from typing import Dict

from .file_service import FileService
from ..core.infrastructure.askui import AskUiAccessToken
from ..core.infrastructure.files.askui import AskUiFilesService


from .config import AgentsConfig


class AgentsContainer:
    def __init__(self, config: AgentsConfig):
        self._config: AgentsConfig = config

    @cached_property
    def _access_token(self) -> AskUiAccessToken:
        return AskUiAccessToken(access_token=self._config.credentials.access_token)

    @cached_property
    def _base_http_headers(self) -> Dict[str, str]:
        return {"Authorization": self._access_token.to_auth_header()}

    @cached_property
    def file_service(self) -> FileService:
        files_sync_service = AskUiFilesService(
            base_url=str(self._config.sync.base_url),
            headers=self._base_http_headers,
        )
        return FileService(
            files_sync_service=files_sync_service,
            local_storage_base_dir=self._config.sync.local_storage_base_dir,
            workspace_id=self._config.credentials.workspace_id,
        )
