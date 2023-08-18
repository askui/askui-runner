import os
import mimetypes


def create_and_open(filename, mode):
    dirname = os.path.dirname(filename)
    if dirname != "":
        os.makedirs(dirname, exist_ok=True)
    return open(filename, mode)


def get_mimetype(file_path: str) -> str | None:
    mimetype, _ = mimetypes.guess_type(file_path)
    return mimetype
