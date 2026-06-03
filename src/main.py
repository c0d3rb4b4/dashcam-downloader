"""Main entry point for dashcam-downloader."""

from __future__ import annotations

import json
import logging
from queue import Empty, Full, Queue
import signal
import sys
import threading
from typing import NoReturn
from urllib.parse import urljoin

import requests

from .config import get_settings
from .constants import APP_NAME, APP_VERSION
from .downloader import DashcamFileDownloader, UnsafeDashcamPathError
from .index_parser import DashcamEntry, complete_entries, parse_index


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured service logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": APP_NAME,
            "version": APP_VERSION,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def setup_logging(level: str) -> None:
    """Configure JSON structured logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.root.handlers = [handler]
    logging.root.setLevel(log_level)
    handler.setLevel(log_level)


logger = logging.getLogger(__name__)


class DashcamDownloaderService:
    """Poll the dashcam index and download complete files in a worker thread."""

    def __init__(self) -> None:
        self.settings = get_settings()
        setup_logging(self.settings.log_level)

        self.index_url = urljoin(
            self.settings.dashcam_base_url.rstrip("/") + "/",
            self.settings.dashcam_index_path.lstrip("/"),
        )
        self.downloader = DashcamFileDownloader(
            base_url=self.settings.dashcam_base_url,
            download_dir=self.settings.download_dir,
            timeout=self.settings.request_timeout_seconds,
            retries=self.settings.download_retries,
            retry_delay=self.settings.retry_delay_seconds,
        )
        self._session = requests.Session()
        self._queue: Queue[DashcamEntry] = Queue(maxsize=self.settings.queue_max_size)
        self._queued_paths: set[str] = set()
        self._queued_paths_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

        logger.info("Initializing %s v%s", APP_NAME, APP_VERSION)
        logger.info("Dashcam index URL: %s", self.index_url)
        logger.info("Download directory: %s", self.settings.download_dir)
        logger.info("Complete file size marker: %d", self.settings.complete_file_size)

    def run(self) -> None:
        """Run the downloader service."""
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        self._worker_thread = threading.Thread(target=self._download_worker, daemon=True)
        self._worker_thread.start()

        logger.info("Starting poll loop: interval=%ds", self.settings.poll_interval_seconds)
        while not self._stop_event.is_set():
            self._poll_once()
            self._stop_event.wait(self.settings.poll_interval_seconds)

        logger.info("Stopping downloader service")
        if self._worker_thread:
            self._worker_thread.join(timeout=5)

    def _poll_once(self) -> None:
        try:
            body = self._fetch_index()
            entries = parse_index(body)
            completed = complete_entries(entries, self.settings.complete_file_size)
            incomplete_count = len(entries) - len(completed)
            queued_count = 0
            existing_count = 0
            invalid_count = 0

            for entry in completed:
                try:
                    if self.downloader.is_downloaded(entry.path):
                        existing_count += 1
                        continue
                    if self._enqueue(entry):
                        queued_count += 1
                except UnsafeDashcamPathError:
                    invalid_count += 1
                    logger.warning("Ignoring unsafe dashcam index path: %s", entry.path)

            logger.info(
                "Polled index: total=%d complete=%d incomplete=%d queued=%d existing=%d invalid=%d",
                len(entries),
                len(completed),
                incomplete_count,
                queued_count,
                existing_count,
                invalid_count,
            )
        except requests.RequestException as exc:
            logger.error("Failed to fetch dashcam index: %s", exc)
        except Exception as exc:
            logger.error("Unexpected polling error: %s", exc, exc_info=True)

    def _fetch_index(self) -> str:
        response = self._session.get(self.index_url, timeout=self.settings.request_timeout_seconds)
        response.raise_for_status()
        return response.text

    def _enqueue(self, entry: DashcamEntry) -> bool:
        with self._queued_paths_lock:
            if entry.path in self._queued_paths:
                return False
            self._queued_paths.add(entry.path)

        try:
            self._queue.put_nowait(entry)
            return True
        except Full:
            with self._queued_paths_lock:
                self._queued_paths.discard(entry.path)
            logger.warning("Download queue is full; skipping for now: %s", entry.path)
            return False

    def _download_worker(self) -> None:
        while not self._stop_event.is_set():
            try:
                entry = self._queue.get(timeout=1)
            except Empty:
                continue

            try:
                self.downloader.download(entry)
            except UnsafeDashcamPathError:
                logger.warning("Skipping unsafe queued path: %s", entry.path)
            except Exception as exc:
                logger.error("Unexpected download error for %s: %s", entry.path, exc, exc_info=True)
            finally:
                with self._queued_paths_lock:
                    self._queued_paths.discard(entry.path)
                self._queue.task_done()

    def _handle_signal(self, signum: int, frame: object) -> None:
        logger.info("Received signal %s, shutting down", signum)
        self._stop_event.set()


def main() -> NoReturn:
    """Main entry point."""
    service = DashcamDownloaderService()
    service.run()
    sys.exit(0)


if __name__ == "__main__":
    main()

