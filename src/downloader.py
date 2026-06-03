"""Download dashcam files safely."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from posixpath import normpath
from urllib.parse import urljoin

import requests

from .constants import DOWNLOAD_CHUNK_SIZE, RECORD_PATH_PREFIX, TEMP_FILE_SUFFIX
from .index_parser import DashcamEntry

logger = logging.getLogger(__name__)


class UnsafeDashcamPathError(ValueError):
    """Raised when an index path cannot be safely mapped to local storage."""


class DashcamFileDownloader:
    """Download completed dashcam files to local storage."""

    def __init__(
        self,
        base_url: str,
        download_dir: Path,
        timeout: int,
        retries: int,
        retry_delay: int,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.download_dir = download_dir
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self._session = requests.Session()

    def destination_path_for(self, dashcam_path: str) -> Path:
        """Map a dashcam path to a safe local destination path."""
        normalized = normpath(dashcam_path)
        if (
            normalized != dashcam_path
            or not normalized.startswith(RECORD_PATH_PREFIX)
            or normalized.endswith("/")
            or "\\" in normalized
        ):
            raise UnsafeDashcamPathError(f"Unsafe dashcam path: {dashcam_path}")

        relative_path = normalized.lstrip("/")
        return self.download_dir / relative_path

    def url_for(self, dashcam_path: str) -> str:
        """Build the absolute download URL for a dashcam path."""
        return urljoin(self.base_url, dashcam_path.lstrip("/"))

    def is_downloaded(self, dashcam_path: str) -> bool:
        """Return whether the final local file already exists."""
        return self.destination_path_for(dashcam_path).is_file()

    def download(self, entry: DashcamEntry) -> bool:
        """Download one dashcam entry.

        Returns True when the file exists locally after this call, otherwise False.
        """
        destination = self.destination_path_for(entry.path)
        if destination.is_file():
            logger.debug("Skipping existing file: %s", destination)
            return True

        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_path = destination.with_name(destination.name + TEMP_FILE_SUFFIX)
        attempts = self.retries + 1

        for attempt in range(1, attempts + 1):
            try:
                self._download_once(entry.path, temp_path)
                os.replace(temp_path, destination)
                logger.info("Downloaded %s to %s", entry.path, destination)
                return True
            except Exception as exc:
                logger.warning(
                    "Download attempt %d/%d failed for %s: %s",
                    attempt,
                    attempts,
                    entry.path,
                    exc,
                )
                if attempt < attempts and self.retry_delay > 0:
                    self._sleep_before_retry()

        return False

    def _download_once(self, dashcam_path: str, temp_path: Path) -> None:
        url = self.url_for(dashcam_path)
        bytes_written = 0
        expected_length: int | None = None

        with self._session.get(url, stream=True, timeout=self.timeout) as response:
            response.raise_for_status()
            content_length = response.headers.get("Content-Length")
            if content_length and content_length.isdigit():
                expected_length = int(content_length)

            with temp_path.open("wb") as file_obj:
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if not chunk:
                        continue
                    file_obj.write(chunk)
                    bytes_written += len(chunk)

        if expected_length is not None and bytes_written != expected_length:
            raise IOError(
                f"Downloaded {bytes_written} bytes, expected {expected_length} bytes"
            )

    def _sleep_before_retry(self) -> None:
        import time

        time.sleep(self.retry_delay)

