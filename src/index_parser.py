"""BlackVue VOD index parsing."""

from __future__ import annotations

from dataclasses import dataclass
import re


_ENTRY_RE = re.compile(r"n:(?P<path>[^,\s\r\n]+)(?:,s:(?P<size>[^\s\r\n]+))?")


@dataclass(frozen=True)
class DashcamEntry:
    """A single file entry from the dashcam index."""

    path: str
    size: int | None

    def is_complete(self, complete_file_size: int) -> bool:
        """Return whether the dashcam reports this entry as fully written."""
        return self.size == complete_file_size


def parse_index(body: str) -> list[DashcamEntry]:
    """Parse a BlackVue VOD index response.

    The camera can return entries either one-per-line or inline, for example:
    ``v:1.00 n:/Record/a.mp4,s:1000000 n:/Record/b.mp4,s:123``.
    """
    entries: list[DashcamEntry] = []
    for match in _ENTRY_RE.finditer(body):
        raw_size = match.group("size")
        size = int(raw_size) if raw_size and raw_size.isdigit() else None
        entries.append(DashcamEntry(path=match.group("path"), size=size))
    return entries


def complete_entries(entries: list[DashcamEntry], complete_file_size: int) -> list[DashcamEntry]:
    """Return only entries whose size matches the complete-file marker."""
    return [entry for entry in entries if entry.is_complete(complete_file_size)]
