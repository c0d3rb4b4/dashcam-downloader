from pathlib import Path

import pytest

from src.downloader import DashcamFileDownloader, UnsafeDashcamPathError


def make_downloader(tmp_path: Path) -> DashcamFileDownloader:
    return DashcamFileDownloader(
        base_url="http://192.168.68.17",
        download_dir=tmp_path,
        timeout=30,
        retries=3,
        retry_delay=0,
    )


def test_destination_preserves_record_path(tmp_path: Path) -> None:
    downloader = make_downloader(tmp_path)

    destination = downloader.destination_path_for("/Record/20260602_074033_PF.mp4")

    assert destination == tmp_path / "Record" / "20260602_074033_PF.mp4"


@pytest.mark.parametrize(
    "dashcam_path",
    [
        "../Record/evil.mp4",
        "/Other/20260602_074033_PF.mp4",
        "Record/20260602_074033_PF.mp4",
        "/Record/../evil.mp4",
        "/Record/subdir/../evil.mp4",
        "/Record/evil.mp4/",
        "/Record\\evil.mp4",
    ],
)
def test_destination_rejects_unsafe_paths(tmp_path: Path, dashcam_path: str) -> None:
    downloader = make_downloader(tmp_path)

    with pytest.raises(UnsafeDashcamPathError):
        downloader.destination_path_for(dashcam_path)


def test_url_for_dashcam_path() -> None:
    downloader = DashcamFileDownloader(
        base_url="http://192.168.68.17/",
        download_dir=Path("/downloads"),
        timeout=30,
        retries=3,
        retry_delay=0,
    )

    assert (
        downloader.url_for("/Record/20260602_074033_PF.mp4")
        == "http://192.168.68.17/Record/20260602_074033_PF.mp4"
    )

