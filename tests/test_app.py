from pathlib import Path

from papertrail.app import format_size, format_document_row, format_indexed_at
from papertrail.db import Document


def test_format_size_bytes() -> None:
    assert format_size(512) == "512.0 B"


def test_format_size_kb() -> None:
    assert format_size(2048) == "2.0 KB"


def test_format_size_mb() -> None:
    assert format_size(5 * 1024 * 1024) == "5.0 MB"


def test_format_size_gb() -> None:
    assert format_size(3 * 1024 * 1024 * 1024) == "3.0 GB"


def test_format_document_row() -> None:
    doc = Document(
        id=1,
        path="/docs/insurance.pdf",
        file_hash="h",
        text="text",
        size_bytes=2048,
        mtime=1.0,
        indexed_at="2026-01-01T00:00:00+00:00",
        language="rus",
    )
    row = format_document_row(doc)
    assert row == ("insurance.pdf", "RUS", "2.0 KB", "01.01.2026 00:00")


def test_format_document_row_unknown_language() -> None:
    doc = Document(
        id=1,
        path="/docs/x.pdf",
        file_hash="h",
        text="",
        size_bytes=100,
        mtime=1.0,
        indexed_at="2026-01-01T00:00:00+00:00",
        language="unknown",
    )
    row = format_document_row(doc)
    assert row[1] == "—"


def test_format_indexed_at_iso() -> None:
    assert format_indexed_at("2026-10-09T23:41:00+00:00") == "09.10.2026 23:41"


def test_format_indexed_at_invalid() -> None:
    assert format_indexed_at("garbage") == "garbage"
