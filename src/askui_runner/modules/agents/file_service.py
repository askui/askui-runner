import os
from pathlib import Path
from typing import Literal
from ..core.infrastructure.files.files import FilesSyncService


class FileService:
    def __init__(
        self,
        files_sync_service: FilesSyncService,
        local_storage_base_dir: Path,
        workspace_id: str,
    ) -> None:
        self._files_sync_service = files_sync_service
        self._local_storage_dir = os.path.join(
            local_storage_base_dir, "Workspaces", workspace_id, "Agents"
        )
        self._remote_agents_path = f"workspaces/{workspace_id}/agents"

    def _build_local_dir_path_to_prevent_overriding(self, remote_path: str) -> str:
        # /workspaces/<WorkspaceID>/agents/<AgentName>
        split_remote_paths = remote_path.strip("/").split("/")
        agent_file_paths = split_remote_paths[3:]

        return os.path.join(
            self._local_storage_dir,
            *agent_file_paths,
        )

    def sync(
        self, source_of_truth: Literal["local", "remote"], dry: bool, delete: bool
    ) -> None:
        self._files_sync_service.sync(
            local_dir_path=self._build_local_dir_path_to_prevent_overriding(
                self._remote_agents_path
            ),
            source_of_truth=source_of_truth,
            remote_dir_path=self._remote_agents_path,
            dry=dry,
            delete=delete,
        )
