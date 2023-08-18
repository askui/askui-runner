from abc import ABC, abstractmethod


class FilesUploadService(ABC):
    @abstractmethod
    def upload(self, local_path: str, remote_dir_path: str) -> None:
        raise NotImplementedError()

class FilesDownloadService(ABC):
    @abstractmethod
    def download(self, local_dir_path: str, remote_path: str) -> None:
        raise NotImplementedError()
