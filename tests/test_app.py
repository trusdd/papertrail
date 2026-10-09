from pathlib import Path

from papertrail.app import format_size, format_document_row
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
    assert row == ("insurance.pdf", "RUS", "2.0 KB", "2026-01-01T00:00:00+00:00")


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
