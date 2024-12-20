import os

from ...runner import ResultsUpload
from ..files.files import FilesUploadService


class AskUiResultsUploadService(ResultsUpload):
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


class ChainedResultsUploadService(ResultsUpload):
    def __init__(self, services: list[ResultsUpload]) -> None:
        self.services = services

    def upload(self) -> None:
        for service in self.services:
            service.upload()
