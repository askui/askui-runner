import os
import re
from typing import Optional
from urllib.parse import urlencode, urljoin

import requests
from pydantic import BaseModel, Field, ConfigDict
from tenacity import retry, stop_after_attempt, wait_exponential

from .files import FilesDownloadService, FilesUploadService


class FileDto(BaseModel):
    name: str = Field(..., description="Name of the file")
    path: str = Field(..., description="Path of the file")
    url: str = Field(..., description="URL of the file")

    model_config = ConfigDict(frozen=True)


class FilesListResponseDto(BaseModel):
    data: list[FileDto] = Field(..., description="List of files")
    next_continuation_token: Optional[str] = Field(
        default=None, description="Token for pagination"
    )

    model_config = ConfigDict(frozen=True)


REQUEST_TIMEOUT_IN_S = 60
UPLOAD_REQUEST_TIMEOUT_IN_S = 3600  # allows for uploading large files


class AskUiFilesService(FilesUploadService, FilesDownloadService):
    HIDDEN_FILES_PATTERNS = [
        r"^workspaces/[^/]+/test-cases/\.askui/.+$",
    ]

    def __init__(self, base_url: str, headers: dict[str, str]):
        self.disabled = base_url == ""
        self.base_url = base_url.rstrip("/")
        self.headers = headers

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True)
    def _upload_file(self, local_file_path: str, remote_file_path: str) -> None:
        with open(local_file_path, "rb") as f:
            url = urljoin(
                base=self.base_url + "/",
                url=remote_file_path,
            )
            with requests.put(
                url,
                files={"file": f},
                headers=self.headers,
                timeout=UPLOAD_REQUEST_TIMEOUT_IN_S,
                stream=True,
            ) as response:
                if response.status_code != 200:
                    response.raise_for_status()

    def _upload_dir(self, local_dir_path: str, remote_dir_path: str) -> None:
        for root, _, files in os.walk(local_dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_file_path = os.path.relpath(
                    file_path,
                    start=local_dir_path,
                )
                remote_file_path = (
                    remote_dir_path
                    + ("/" if remote_dir_path != "" else "")
                    + ("/".join(relative_file_path.split(os.sep)))
                )
                self._upload_file(file_path, remote_file_path)

    def upload(self, local_path: str, remote_dir_path: str = "") -> None:
        if self.disabled:
            return
        r_dir_path = remote_dir_path.rstrip("/")
        if os.path.isdir(local_path):
            self._upload_dir(local_path, r_dir_path)
        else:
            self._upload_file(
                local_path, f"{r_dir_path}/{os.path.basename(local_path)}"
            )

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True)
    def _download_file(self, url: str, local_file_path: str) -> None:
        response = requests.get(
            url,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_IN_S,
            stream=True,
        )
        if response.status_code != 200:
            response.raise_for_status()
        with open(local_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True)
    def _list_objects(
        self, prefix: str, continuation_token: str | None = None
    ) -> FilesListResponseDto:
        params = {"prefix": prefix, "limit": 100, "expand": "url"}
        if continuation_token is not None:
            params["continuation_token"] = continuation_token
        list_url = f"{self.base_url}?{urlencode(params)}"
        response = requests.get(
            list_url, headers=self.headers, timeout=REQUEST_TIMEOUT_IN_S
        )
        if response.status_code != 200:
            response.raise_for_status()
        return FilesListResponseDto(**response.json())

    def download(self, local_dir_path: str, remote_path: str = "") -> None:
        """Download files from S3.

        Args:
            local_dir_path (str): The local directory to download the files to.
            remote_path (str, optional): The remote path to a directory to download the files from or a single file to download. Defaults to "". If you pass a a prefix of a directory or file, the `remote_path` prefix is going to be stripped from the file paths when creating the local paths to the files.
        """
        if self.disabled:
            return
        continuation_token = None
        prefix = remote_path.lstrip("/")
        while True:
            list_objects_response = self._list_objects(prefix, continuation_token)
            for content in list_objects_response.data:
                if any(
                    re.match(pattern, content.path) is not None
                    for pattern in self.HIDDEN_FILES_PATTERNS
                ):
                    continue

                if prefix == content.path:  # is a file
                    relative_remote_path = content.name
                else:  # is a prefix, e.g., folder
                    relative_remote_path = content.path[len(prefix) :].lstrip("/")
                local_file_path = os.path.join(
                    local_dir_path, *relative_remote_path.split("/")
                )
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                self._download_file(content.url, local_file_path)
            continuation_token = list_objects_response.next_continuation_token
            if continuation_token is None:
                break
