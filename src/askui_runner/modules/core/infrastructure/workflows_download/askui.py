import os

from ...runner import WorkflowsDownload
from ..files.files import FilesDownloadService


class AskUiWorkflowsDownloadService(WorkflowsDownload):
    def __init__(
        self,
        files_download_service: FilesDownloadService,
        workflows_dir: str,
        remote_workflows_paths: list[str] | None,
    ) -> None:
        self.files_download_service = files_download_service
        self.workflows_dir = workflows_dir
        self.remote_workflows_paths = remote_workflows_paths or []

    def build_local_dir_path_to_prevent_overriding(self, remote_path: str) -> str:
        """Returns a local_dir_path that is the concatenation of local_workflows_folder and the part of remote_path (the "workflows_path") that identifies the workflow inside the workspace.

        Assumes that remote_path is of the form "\\/?workspaces/(?<workspace_id>.*?)\\/test-cases\\/?(?<workflows_path>.*(\\/.+\\.ts)?)" (regex).
        """
        split_remote_paths = remote_path.strip("/").split("/")
        workflows_paths = split_remote_paths[3:]
        if len(workflows_paths) > 0 and workflows_paths[-1].endswith(".ts"):
            workflows_paths = workflows_paths[:-1]
        return os.path.join(
            self.workflows_dir,
            *workflows_paths,
        )

    def download(self) -> None:
        for remote_workflows_path in self.remote_workflows_paths:
            self.files_download_service.download(
                local_dir_path=self.build_local_dir_path_to_prevent_overriding(
                    remote_workflows_path
                ),
                remote_path=remote_workflows_path,
            )
