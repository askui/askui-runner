import json
from typing import Any

import yaml

from .modules.queue import config as queue_config


class Config(queue_config.Config):
    class Config:
        env_prefix = "askui_runner_"


def read_config_dict(config_file_path: str) -> dict[str, Any]:
    with open(config_file_path, "r", encoding="utf-8") as read_stream:
        file_extension = config_file_path.split(".")[-1]
        match file_extension:
            case "yaml" | "yml":
                return yaml.safe_load(read_stream)
            case "json":
                return json.load(read_stream)
        raise ValueError(f"Unsupported config file extension: {file_extension}")


def read_config(config_file_path: str) -> Config:
    return Config.parse_obj(read_config_dict(config_file_path))
