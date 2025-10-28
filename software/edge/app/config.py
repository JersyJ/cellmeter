# File with environment variables and general configuration logic.
# Env variables are combined in nested groups like "Security" etc.
# So environment variable (case-insensitive) for "webhook_secret" will be "security__webhook_secret"
#
# Pydantic priority ordering:
#
# 1. (Most important, will overwrite everything) - environment variables
# 2. `.env` file in root folder of project
# 3. Default values
#
#
# See https://pydantic-docs.helpmanual.io/usage/settings/
# Note, complex types like lists are read as json-encoded strings.

import logging.config
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).parent.parent


class Teltonika(BaseModel):
    """Settings related to Teltonika API."""

    ip: str
    user: str = "admin"
    ssh_user: str = "root"
    password: SecretStr


class Database(BaseModel):
    """Settings related to database connections."""

    url: str
    token: SecretStr
    org: str = "cellmeter-org"
    bucket: str = "metrics"


class SessionDB(BaseModel):
    """Settings related to the session database."""

    path: str = "/tmp/cellmeter_session.db"


class Benchmarking(BaseModel):
    """Settings related to benchmarking tests."""

    ping_address: str = "158.196.195.32"
    ping_count: int = 10
    iperf3_server_ip: str = "158.196.195.32"
    interval__in_seconds: int = 60
    speedtest_url: str = "http://rychlost.poda.cz:8080/speedtest/upload.php"


class Settings(BaseSettings):
    teltonika: Teltonika = Field(default_factory=Teltonika)  # type: ignore
    database: Database = Field(default_factory=Database)  # type: ignore
    session_db: SessionDB = Field(default_factory=SessionDB)
    benchmarking: Benchmarking = Field(default_factory=Benchmarking)
    log_level: str = "INFO"
    debug_mode: bool = True

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=f"{PROJECT_DIR}/.env",
        case_sensitive=False,
        env_nested_delimiter="__",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore


def logging_config(log_level: str) -> None:
    conf = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{asctime} [{levelname}] {name}: {message}",
                "style": "{",
            },
        },
        "handlers": {
            "stream": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "level": "DEBUG",
            },
        },
        "loggers": {
            "": {
                "level": log_level,
                "handlers": ["stream"],
                "propagate": True,
            },
        },
    }
    logging.config.dictConfig(conf)


logging_config(log_level=get_settings().log_level)
