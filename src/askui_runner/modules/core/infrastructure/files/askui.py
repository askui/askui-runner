from .s3 import ListObjectsResponse, ListObjectsResponseContent, S3RestApiFilesService


class AskUiFilesService(S3RestApiFilesService):
    HIDDEN_FOLDER_NAME = ".askui"

    def build_download_file_url(self, remote_file_path: str) -> str:
        return self.build_file_url(self.remove_workspace_prefix(remote_file_path))

    def remove_workspace_prefix(self, remote_path: str) -> str:
        prefix_end = remote_path.find("/", len("workspaces/"))
        return remote_path[prefix_end + 1 :]

    def map_list_objects_response(self, content: bytes) -> ListObjectsResponse:
        response = super().map_list_objects_response(content)
        return ListObjectsResponse(
            continuation_token=response.continuation_token,
            prefix=response.prefix,
            contents=[
                ListObjectsResponseContent(key=content.key)
                for content in response.contents
                if not content.key[len(response.prefix or "") :]
                .lstrip("/")
                .startswith(self.HIDDEN_FOLDER_NAME)
            ],
        )
