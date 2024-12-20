import json
from typing import Any

import yaml
from pydantic_settings import SettingsConfigDict

from .modules.queue import config as queue_config


class Config(queue_config.Config):
    model_config = SettingsConfigDict(env_prefix="askui_runner_")


def read_config_dict(config_json_or_config_file_path: str) -> dict[str, Any]:
    if config_json_or_config_file_path.lstrip().startswith("{"):
        return json.loads(config_json_or_config_file_path)
    with open(config_json_or_config_file_path, "r", encoding="utf-8") as read_stream:
        file_extension = config_json_or_config_file_path.split(".")[-1]
        match file_extension:
            case "yaml" | "yml":
                return yaml.safe_load(read_stream)
            case "json":
                return json.load(read_stream)
        raise ValueError(f"Unsupported config file extension: {file_extension}")


def read_config(config_json_or_config_file_path: str) -> Config:
    return Config.model_validate(read_config_dict(config_json_or_config_file_path))
