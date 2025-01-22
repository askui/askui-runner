import os
from typing import Literal
from ..files.files import FilesSyncService


class AskUIAgentFileManager:
    def __init__(
        self,
        files_sync_service: FilesSyncService,
        local_storage_dir: str,
        remote_workflow_path: str,
    ) -> None:
        self.files_sync_service = files_sync_service
        self.remote_workflows_path = remote_workflow_path
        self.local_storage_dir = local_storage_dir

    def build_local_dir_path_to_prevent_overriding(self, remote_path: str) -> str:
        # /workspaces/<WorkspaceID>/Agents/<Agents>
        split_remote_paths = remote_path.strip("/").split("/")
        workspace_id = split_remote_paths[1]
        workflows_paths = split_remote_paths[3:]

        return os.path.join(
            self.local_storage_dir,
            workspace_id,
            *workflows_paths,
        )

    def sync(
        self, source_of_truth: Literal["local", "remote"], dry: bool, delete: bool
    ) -> None:
        self.files_sync_service.sync(
            local_dir_path=self.build_local_dir_path_to_prevent_overriding(
                self.remote_workflows_path
            ),
            source_of_truth=source_of_truth,
            remote_dir_path=self.remote_workflows_path,
            dry=dry,
            delete=delete,
        )
