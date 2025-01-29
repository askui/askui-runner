import logging
import os
import re
from typing import Dict, Generator, Literal, Optional, Union
from urllib.parse import urlencode, urljoin, quote
from datetime import datetime, timezone

import requests
from pydantic import AwareDatetime, BaseModel, Field, ConfigDict
from tenacity import retry, stop_after_attempt, wait_exponential

from .files import FilesDownloadService, FilesUploadService, FilesSyncService


class FileDto(BaseModel):
    name: str = Field(..., description="Name of the file")
    path: str = Field(..., description="Path of the file")
    last_modified: AwareDatetime = Field(
        ..., alias="lastModified", description="Last modified date of the file"
    )
    url: str = Field(..., description="URL of the file")
    size: int = Field(..., description="Size of the file in bytes")

    model_config = ConfigDict(frozen=True, populate_by_name=True)


class FilesListResponseDto(BaseModel):
    data: list[FileDto] = Field(..., description="List of files")
    next_continuation_token: Optional[str] = Field(
        default=None, description="Token for pagination"
    )

    model_config = ConfigDict(frozen=True)


REQUEST_TIMEOUT_IN_S = 60
UPLOAD_REQUEST_TIMEOUT_IN_S = 3600  # allows for uploading large files


class AskUiFilesService(FilesUploadService, FilesDownloadService, FilesSyncService):
    HIDDEN_FILES_PATTERNS = [
        r"^workspaces/[^/]+/test-cases/\.askui/.+$",
    ]

    def __init__(self, base_url: str, headers: dict[str, str]):
        self._disabled = base_url == ""
        self._base_url = base_url.rstrip("/")
        self._headers = headers

    def download(self, local_dir_path: str, remote_path: str = "") -> None:
        """Download files from S3.

        Args:
            local_dir_path (str): The local directory to download the files to.
            remote_path (str, optional): The remote path to a directory to download the files from or a single file to download. Defaults to "". If you pass a a prefix of a directory or file, the `remote_path` prefix is going to be stripped from the file paths when creating the local paths to the files.
        """
        if self._disabled:
            return
        prefix = remote_path.lstrip("/")
        for content in self._list_remote_objects(prefix):
            if prefix == content.path:  # is a file
                relative_remote_path = content.name
            else:  # is a prefix, e.g., folder
                relative_remote_path = content.path[len(prefix) :].lstrip("/")
            local_file_path = os.path.join(
                local_dir_path, *relative_remote_path.split("/")
            )
            self._download_file(content.url, local_file_path, content.last_modified)

    def upload(self, local_path: str, remote_dir_path: str = "") -> None:
        if self._disabled:
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
        # List remote files
        remote_files: Dict[str, FileDto] = {}

        for file in self._list_remote_objects(remote_dir_path):
            remote_files[file.path[len(remote_dir_path) :].lstrip("/")] = file

        # List local files
        local_files = self._list_local_files(local_dir_path)

        # Create lookup table
        all_paths = set(local_files.keys()) | set(remote_files.keys())

        for relative_path in sorted(all_paths):
            local_file: Union[FileDto | None] = local_files.get(relative_path)
            remote_file: Union[FileDto | None] = remote_files.get(relative_path)
            remote_file_path = f"{remote_dir_path}/{relative_path}".replace("\\", "/")

            # File exists in both locations
            if local_file and remote_file:
                local_mtime = local_file.last_modified
                remote_mtime = remote_file.last_modified

                if source_of_truth == "local" and (
                    local_mtime > remote_mtime or local_file.size != remote_file.size
                ):
                    self._upload_file(local_file.path, remote_file_path, dry)

                elif source_of_truth == "remote" and (
                    remote_mtime > local_mtime or local_file.size != remote_file.size
                ):
                    local_path = os.path.join(local_dir_path, relative_path)
                    self._download_file(
                        remote_file.url, local_path, remote_file.last_modified, dry
                    )
                else:
                    logging.info(f"Skip {relative_path} (no changes)")
                    continue

            # File exists only locally
            elif local_file:
                if source_of_truth == "local":
                    self._upload_file(local_file.path, remote_file_path, dry)
                elif delete:
                    self._delete_local_file(local_file.path, dry)

            # File exists only remotely
            elif remote_file:
                if source_of_truth == "remote":
                    local_path = os.path.join(local_dir_path, relative_path)
                    self._download_file(
                        remote_file.url, local_path, remote_file.last_modified, dry
                    )
                elif delete:
                    self._delete_remote_file(remote_file_path, dry)

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True)
    def _upload_file(
        self, local_file_path: str, remote_file_path: str, dry=False
    ) -> None:
        url = urljoin(
            base=self._base_url + "/",
            url=quote(remote_file_path),
        )

        logging.info(f"Uploading {local_file_path} to {url} ...")
        if dry:
            return

        with open(local_file_path, "rb") as f:
            with requests.put(
                url,
                files={"file": f},
                headers=self._headers,
                timeout=UPLOAD_REQUEST_TIMEOUT_IN_S,
                stream=True,
            ) as response:
                if response.status_code != 200:
                    response.raise_for_status()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True)
    def _delete_remote_file(self, remote_file_path: str, dry=False) -> None:
        logging.info(f"Deleting file {remote_file_path} ...")
        if dry:
            return

        delete_url = urljoin(self._base_url + "/", remote_file_path)
        response = requests.delete(delete_url, headers=self._headers)
        if response.status_code != 204:
            response.raise_for_status()

    def _delete_local_file(self, local_file_path: str, dry=False) -> None:
        logging.info(f"Deleting file {local_file_path} ...")
        if dry:
            return

        os.remove(local_file_path)

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True)
    def _download_file(
        self,
        url: str,
        local_file_path: str,
        last_modified_on_remote: AwareDatetime,
        dry=False,
    ) -> None:
        logging.info(
            f"Downloading file to {local_file_path} from {url}. Last modified on {last_modified_on_remote} ..."
        )
        if dry:
            return

        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        response = requests.get(
            url,
            headers=self._headers,
            timeout=REQUEST_TIMEOUT_IN_S,
            stream=True,
        )
        if response.status_code != 200:
            response.raise_for_status()
        with open(local_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        os.utime(
            path=local_file_path,
            times=(
                last_modified_on_remote.timestamp(),
                last_modified_on_remote.timestamp(),
            ),
        )

    def _list_local_files(self, local_dir_path: str) -> dict[str, FileDto]:
        """List all files in a local directory."""
        local_files = {}
        for root, _, files in os.walk(local_dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(
                    file_path, start=local_dir_path
                ).replace(os.sep, "/")
                file_stats = os.stat(file_path)
                local_files[relative_path] = FileDto(
                    name=os.path.basename(file_path),
                    path=file_path,
                    last_modified=datetime.fromtimestamp(
                        file_stats.st_mtime, tz=timezone.utc
                    ),
                    url=f"file://{file_path}",
                    size=file_stats.st_size,
                )  # type: ignore[call-arg]
        return local_files

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True)
    def _list_remote_objects(self, prefix: str) -> Generator[FileDto, None, None]:
        continuation_token = None
        while True:
            params = {"prefix": prefix, "limit": 100, "expand": "url"}
            if continuation_token:
                params["continuation_token"] = continuation_token

            list_url = f"{self._base_url}?{urlencode(params)}"
            response = requests.get(
                list_url, headers=self._headers, timeout=REQUEST_TIMEOUT_IN_S
            )

            response.raise_for_status()

            file_list_response = FilesListResponseDto(**response.json())

            for file in file_list_response.data:
                if any(
                    re.match(pattern, file.path)
                    for pattern in self.HIDDEN_FILES_PATTERNS
                ):
                    continue

                yield file

            continuation_token = file_list_response.next_continuation_token
            if not continuation_token:
                break

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
