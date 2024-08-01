import os
from urllib.parse import urlencode, urljoin
from xml.etree import ElementTree

import requests
from pydantic import BaseModel
from requests_toolbelt.streaming_iterator import StreamingIterator
from tenacity import retry, stop_after_attempt, wait_exponential

from .files import FilesDownloadService, FilesUploadService
from .utils import get_mimetype


class ListObjectsResponseContent(BaseModel):
    key: str


class ListObjectsResponse(BaseModel):
    contents: list[ListObjectsResponseContent]
    continuation_token: str | None
    prefix: str | None

REQUEST_TIMEOUT_IN_S=60

class S3RestApiFilesService(FilesUploadService, FilesDownloadService):
    def __init__(self, base_url: str, headers: dict[str, str]):
        self.disabled = base_url == ""
        self.base_url = base_url.rstrip("/") + "/"
        self.headers = headers
    
    def _should_ignore_error(self, response: requests.Response) -> bool:
        """
        Check if the response status code is an ignored error.
        Status code 413 of the AWS API gateway, which is used to expose the S3 Rest API, is ignored because it is a workaround for the 10MB upload limit.
        """
        return response.status_code == 413

    def _build_file_url(self, remote_file_path: str) -> str:
        return urljoin(
            base=self.base_url,
            url=remote_file_path,
        )

    def _build_upload_file_url(self, remote_file_path: str) -> str:
        return self._build_file_url(remote_file_path)

    def _build_download_file_url(self, remote_file_path: str) -> str:
        return self._build_file_url(remote_file_path)

    @retry(
        stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True
    )  # log retry
    def _upload_file(
        self, local_file_path: str, remote_file_path: str
    ) -> None:  # log upload file + failure and retry
        with open(local_file_path, "rb") as f:
            iterator = StreamingIterator(os.path.getsize(local_file_path), f)
            url = self._build_upload_file_url(remote_file_path)
            mimetype = get_mimetype(local_file_path)
            headers = {"Content-Type": mimetype} if mimetype else {}
            response = requests.put(
                url,
                data=iterator,
                headers={
                    **self.headers,
                    **headers,
                },
                timeout=REQUEST_TIMEOUT_IN_S,
            )
            if response.status_code != 200:
                if not self._should_ignore_error(response):
                    response.raise_for_status()

    def _upload_dir(self, local_dir_path: str, remote_dir_path: str) -> None:
        for root, _, files in os.walk(local_dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_file_path = os.path.relpath(file_path, start=local_dir_path)
                remote_file_path = f"{remote_dir_path}/" "/".join(
                    relative_file_path.split(os.sep)
                )
                self._upload_file(file_path, remote_file_path)

    def upload(self, local_path: str, remote_dir_path: str = "") -> None:
        if self.disabled:
            return
        r_dir_path = remote_dir_path.rstrip("/")
        if os.path.isdir(local_path):
            self._upload_dir(local_path, r_dir_path)
        else:
            self._upload_file(local_path, f"{r_dir_path}/{os.path.basename(local_path)}")

    @retry(
        stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True
    )  # log retry
    def _download_file(
        self, remote_file_path: str, local_file_path: str
    ) -> None:  # log download file
        url = self._build_download_file_url(remote_file_path)
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

    def _map_list_objects_response(self, content: bytes) -> ListObjectsResponse:
        list_response_element = ElementTree.fromstring(content)
        return ListObjectsResponse(
            contents=[
                ListObjectsResponseContent(key=key_element.text)
                for key_element in list_response_element.findall(
                    ".//{http://s3.amazonaws.com/doc/2006-03-01/}Key"
                )
                if key_element.text is not None
            ],
            continuation_token=list_response_element.findtext(
                ".//{http://s3.amazonaws.com/doc/2006-03-01/}NextContinuationToken"
            ),
            prefix=list_response_element.findtext(
                ".//{http://s3.amazonaws.com/doc/2006-03-01/}Prefix"
            ),
        )

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True)
    def _list_objects(
        self, prefix: str, continuation_token: str | None = None
    ) -> ListObjectsResponse:
        params = {"list-type": "2", "prefix": prefix}
        if continuation_token is not None:
            params["continuation-token"] = continuation_token
        list_url = f"{self.base_url}?{urlencode(params)}"
        response = requests.get(list_url, headers=self.headers, timeout=REQUEST_TIMEOUT_IN_S)
        if response.status_code != 200:
            response.raise_for_status()
        return self._map_list_objects_response(response.content)

    def download(self, local_dir_path: str, remote_path: str = "") -> None:
        if self.disabled:
            return
        continuation_token = None
        prefix = remote_path.strip("/")
        while True:
            list_objects_response = self._list_objects(prefix, continuation_token)
            for content in list_objects_response.contents:
                relative_remote_path = (
                    content.key.split("/")[-1]
                    if prefix == content.key
                    else content.key[len(prefix) :].lstrip("/")
                )
                local_file_path = os.path.join(
                    local_dir_path, *relative_remote_path.split("/")
                )
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                self._download_file(content.key, local_file_path)
            continuation_token = list_objects_response.continuation_token
            if continuation_token is None:
                break
