import os


def create_and_open(filename, mode):
    dirname = os.path.dirname(filename)
    if dirname != "":
        os.makedirs(dirname, exist_ok=True)
    return open(filename, mode)
