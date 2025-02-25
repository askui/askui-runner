import enum
import logging


from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggingConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="askui_runner__log__")

    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(levelname)s - %(message)s"


def configure_logging(config: LoggingConfig | None = None) -> None:
    config = config or LoggingConfig()
    logging.basicConfig(level=config.level.value, format=config.format)
