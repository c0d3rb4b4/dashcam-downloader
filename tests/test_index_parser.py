from src.index_parser import complete_entries, parse_index


def test_parse_newline_delimited_index() -> None:
    body = (
        "v:1.00\r\n"
        "n:/Record/20260602_074033_PF.mp4,s:1000000\r\n"
        "n:/Record/20260602_074130_PF.mp4,s:42\r\n"
    )

    entries = parse_index(body)

    assert [(entry.path, entry.size) for entry in entries] == [
        ("/Record/20260602_074033_PF.mp4", 1000000),
        ("/Record/20260602_074130_PF.mp4", 42),
    ]


def test_parse_inline_index() -> None:
    body = (
        "v:1.00 n:/Record/20260602_073630_PF.mp4,s:1000000 "
        "n:/Record/20260602_073741_PF.mp4,s:1000000 "
        "n:/Record/20260602_073837_PF.mp4"
    )

    entries = parse_index(body)

    assert [(entry.path, entry.size) for entry in entries] == [
        ("/Record/20260602_073630_PF.mp4", 1000000),
        ("/Record/20260602_073741_PF.mp4", 1000000),
        ("/Record/20260602_073837_PF.mp4", None),
    ]


def test_complete_entries_require_exact_size_marker() -> None:
    body = (
        "v:1.00 "
        "n:/Record/missing.mp4 "
        "n:/Record/malformed.mp4,s:not-ready "
        "n:/Record/incomplete.mp4,s:999999 "
        "n:/Record/complete.mp4,s:1000000"
    )

    entries = parse_index(body)
    completed = complete_entries(entries, complete_file_size=1000000)

    assert [entry.path for entry in completed] == ["/Record/complete.mp4"]

