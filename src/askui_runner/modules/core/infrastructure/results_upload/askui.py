import os

from ...domain import services
from ..files.files import FilesUploadService


class AskUiResultsUploadService(services.ResultsUpload):
    def __init__(
        self,
        files_upload_service: FilesUploadService,
        results_dir: str,
    ) -> None:
        self.files_upload_service = files_upload_service
        self.results_dir = results_dir

    def upload(self) -> None:
        if os.path.exists(self.results_dir):
            self.files_upload_service.upload(
                local_path=self.results_dir,
                remote_dir_path="",
            )
