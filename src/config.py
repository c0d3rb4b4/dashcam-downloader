"""Configuration management for dashcam-downloader."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

from .constants import (
    DEFAULT_COMPLETE_FILE_SIZE,
    DEFAULT_DASHCAM_BASE_URL,
    DEFAULT_DASHCAM_INDEX_PATH,
    DEFAULT_DOWNLOAD_DIR,
    DEFAULT_DOWNLOAD_RETRIES,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_QUEUE_MAX_SIZE,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_RETRY_DELAY_SECONDS,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    dashcam_base_url: str = DEFAULT_DASHCAM_BASE_URL
    dashcam_index_path: str = DEFAULT_DASHCAM_INDEX_PATH
    download_dir: Path = Path(DEFAULT_DOWNLOAD_DIR)
    poll_interval_seconds: int = Field(default=DEFAULT_POLL_INTERVAL_SECONDS, ge=1)
    complete_file_size: int = Field(default=DEFAULT_COMPLETE_FILE_SIZE, ge=1)
    request_timeout_seconds: int = Field(default=DEFAULT_REQUEST_TIMEOUT_SECONDS, ge=1)
    download_retries: int = Field(default=DEFAULT_DOWNLOAD_RETRIES, ge=0)
    retry_delay_seconds: int = Field(default=DEFAULT_RETRY_DELAY_SECONDS, ge=0)
    queue_max_size: int = Field(default=DEFAULT_QUEUE_MAX_SIZE, ge=1)
    log_level: str = "INFO"

    model_config = {
        "env_file": "config/app.env",
        "env_file_encoding": "utf-8",
        "env_prefix": "",
        "extra": "ignore",
    }


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
