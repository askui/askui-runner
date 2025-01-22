import logging
import os
import re
from typing import Callable, Dict, Literal, Optional, Union
from urllib.parse import urlencode, urljoin, quote
from datetime import datetime, timezone

import requests
from pydantic import BaseModel, Field, ConfigDict
from tenacity import retry, stop_after_attempt, wait_exponential

from .files import FilesDownloadService, FilesUploadService, FilesSyncService


# region Models
class FileDto(BaseModel):
    name: str = Field(..., description="Name of the file")
    path: str = Field(..., description="Path of the file")
    last_modified: str = Field(
        ..., alias="lastModified", description="Last modified date of the file"
    )
    url: str = Field(..., description="URL of the file")
    size: int = Field(..., description="Size of the file")

    model_config = ConfigDict(frozen=True)


class LocalFileDto(BaseModel):
    path: str = Field(..., description="Path of the local file")
    size: int = Field(..., description="Size of the file")
    last_modified: float = Field(..., description="Last modified time of the file")

    model_config = ConfigDict(frozen=True)


class FilesListResponseDto(BaseModel):
    data: list[FileDto] = Field(..., description="List of files")
    next_continuation_token: Optional[str] = Field(
        default=None, description="Token for pagination"
    )

    model_config = ConfigDict(frozen=True)


REQUEST_TIMEOUT_IN_S = 60
UPLOAD_REQUEST_TIMEOUT_IN_S = 3600  # allows for uploading large files


# region Services
class AskUiFilesService(FilesUploadService, FilesDownloadService, FilesSyncService):
    HIDDEN_FILES_PATTERNS = [
        r"^workspaces/[^/]+/test-cases/\.askui/.+$",
    ]

    def __init__(self, base_url: str, headers: dict[str, str]):
        self.disabled = base_url == ""
        self.base_url = base_url.rstrip("/")
        self.headers = headers

    # region Public Functions
    def download(self, local_dir_path: str, remote_path: str = "") -> None:
        """Download files from S3.

        Args:
            local_dir_path (str): The local directory to download the files to.
            remote_path (str, optional): The remote path to a directory to download the files from or a single file to download. Defaults to "". If you pass a a prefix of a directory or file, the `remote_path` prefix is going to be stripped from the file paths when creating the local paths to the files.
        """
        if self.disabled:
            return
        prefix = remote_path.lstrip("/")
        list_objects_response = self._list_object_recursive(prefix)
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
            self._download_file(content.url, local_file_path, content.last_modified)

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

    def sync(
        self,
        local_dir_path: str,
        remote_dir_path: str,
        source_of_truth: Literal["local", "remote"],
        dry: bool = False,
        delete: bool = True,
    ) -> None:
        if source_of_truth not in {"local", "remote"}:
            raise ValueError("source_of_truth must be 'local' or 'remote'")

        # List remote files
        remote_files: Dict[str, FileDto] = {}
        list_objects_response = self._list_object_recursive(remote_dir_path)
        for content in list_objects_response.data:
            if any(
                re.match(pattern, content.path)
                for pattern in self.HIDDEN_FILES_PATTERNS
            ):
                continue
            remote_files[content.path[len(remote_dir_path) :].lstrip("/")] = content

        # List local files
        local_files = self._list_local_files(local_dir_path)

        # Create lookup table
        all_paths = set(local_files.keys()) | set(remote_files.keys())

        # Action mapper
        action_mapper: Dict[str, Callable[..., None]] = {
            "upload": lambda local_file_path, remote_file_path: (
                logging.info(f"Dry: Upload {local_file_path} to cloud")
                if dry
                else self._upload_file(local_file_path, remote_file_path)
            ),
            "download": lambda remote_file_url, remote_file_last_modified, local_path: (
                logging.info(f"Dry: Download file to {local_path}")
                if dry
                else self._download_file(
                    remote_file_url, local_path, remote_file_last_modified
                )
            ),
            "delete_local": lambda local_file_path: (
                logging.info(f"Dry: Delete local file {local_file_path}")
                if dry
                else os.remove(local_file_path)
            ),
            "delete_remote": lambda remote_file_path: (
                logging.info(f"Dry: Delete remote file {remote_file_path}")
                if dry
                else self._delete_file(remote_file_path)
            ),
            "skip": lambda relative_path: logging.info(
                f"Skip {relative_path} (no changes)"
            ),
        }

        for relative_path in sorted(all_paths):
            local_file: Union[LocalFileDto | None] = local_files.get(relative_path)
            remote_file: Union[FileDto | None] = remote_files.get(relative_path)
            remote_file_path = f"{remote_dir_path}/{relative_path}".replace("\\", "/")

            # File exists in both locations
            if local_file and remote_file:
                local_mtime = local_file.last_modified
                remote_mtime = (
                    datetime.strptime(remote_file.last_modified, "%Y-%m-%dT%H:%M:%SZ")
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                )

                if source_of_truth == "local" and (
                    local_mtime > remote_mtime or local_file.size != remote_file.size
                ):
                    action_mapper["upload"](local_file.path, remote_file_path)

                elif source_of_truth == "remote" and (
                    remote_mtime > local_mtime or local_file.size != remote_file.size
                ):
                    local_path = os.path.join(local_dir_path, relative_path)
                    action_mapper["download"](
                        remote_file.url, remote_file.last_modified, local_path
                    )
                else:
                    action_mapper["skip"](relative_path)
                    continue

            # File exists only locally
            elif local_file:
                if source_of_truth == "local":
                    action_mapper["upload"](local_file.path, remote_file_path)
                elif delete:
                    action_mapper["delete_local"](local_file.path)

            # File exists only remotely
            elif remote_file:
                if source_of_truth == "remote":
                    local_path = os.path.join(local_dir_path, relative_path)
                    action_mapper["download"](
                        remote_file.url, remote_file.last_modified, local_path
                    )
                elif delete:
                    action_mapper["delete_remote"](remote_file_path)

    # region Private Functions
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True)
    def _upload_file(self, local_file_path: str, remote_file_path: str) -> None:
        with open(local_file_path, "rb") as f:
            url = urljoin(
                base=self.base_url + "/",
                url=remote_file_path,
            )
            url = quote(url, safe=":/")
            with requests.put(
                url,
                files={"file": f},
                headers=self.headers,
                timeout=UPLOAD_REQUEST_TIMEOUT_IN_S,
                stream=True,
            ) as response:
                if response.status_code != 200:
                    response.raise_for_status()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True)
    def _delete_file(self, remote_file_path: str) -> None:
        delete_url = urljoin(self.base_url + "/", remote_file_path)
        response = requests.delete(delete_url, headers=self.headers)
        if response.status_code != 204:
            response.raise_for_status()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True)
    def _download_file(
        self, url: str, local_file_path: str, last_modified: str
    ) -> None:
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
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

        cloud_timestamp = (
            datetime.strptime(last_modified, "%Y-%m-%dT%H:%M:%SZ")
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )
        os.utime(path=local_file_path, times=(cloud_timestamp, cloud_timestamp))

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

    def _list_local_files(self, local_dir_path: str) -> dict[str, LocalFileDto]:
        """List all files in a local directory."""
        local_files = {}
        for root, _, files in os.walk(local_dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, start=local_dir_path)
                file_stats = os.stat(file_path)
                local_files[relative_path] = LocalFileDto(
                    path=file_path,
                    size=file_stats.st_size,
                    last_modified=datetime.fromtimestamp(
                        file_stats.st_mtime, tz=timezone.utc
                    ).timestamp(),
                )
        return local_files

    def _list_object_recursive(self, prefix: str) -> FilesListResponseDto:
        all_files = []
        continuation_token = None
        while True:
            list_objects_response = self._list_objects(prefix, continuation_token)
            all_files.extend(list_objects_response.data)
            continuation_token = list_objects_response.next_continuation_token
            if continuation_token is None:
                break
        return FilesListResponseDto(data=all_files, next_continuation_token=None)

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
