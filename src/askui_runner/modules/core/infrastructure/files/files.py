from abc import ABC, abstractmethod
from typing import Literal


class FilesUploadService(ABC):
    @abstractmethod
    def upload(self, local_path: str, remote_dir_path: str) -> None:
        raise NotImplementedError()


class FilesDownloadService(ABC):
    @abstractmethod
    def download(self, local_dir_path: str, remote_path: str) -> None:
        raise NotImplementedError()


class FilesSyncService(ABC):
    @abstractmethod
    def sync(
        self,
        local_dir_path: str,
        remote_dir_path: str,
        source_of_truth: Literal["local", "remote"],
        dry: bool = False,
        delete: bool = True,
    ) -> None:
        raise NotImplementedError()
