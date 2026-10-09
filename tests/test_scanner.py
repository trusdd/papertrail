from pathlib import Path

import pytest

from papertrail.db import connect, count_documents, get_all_documents, init_db
from papertrail.scanner import (
    file_hash,
    find_documents,
    is_changed,
    is_supported,
    scan_and_index,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    init_db(path)
    return path


@pytest.fixture
def docs_dir(tmp_path: Path) -> Path:
    d = tmp_path / "docs"
    d.mkdir()
    (d / "a.pdf").write_bytes(b"%PDF-1.4 fake pdf content")
    (d / "b.jpg").write_bytes(b"\xff\xd8\xff fake jpeg content")
    (d / "c.txt").write_text("not supported")
    sub = d / "sub"
    sub.mkdir()
    (sub / "d.png").write_bytes(b"\x89PNG fake png")
    return d


def test_is_supported() -> None:
    assert is_supported(Path("doc.pdf"))
    assert is_supported(Path("doc.PDF"))
    assert is_supported(Path("photo.JPG"))
    assert not is_supported(Path("notes.txt"))
    assert not is_supported(Path("archive.zip"))


def test_find_documents(docs_dir: Path) -> None:
    found = find_documents(docs_dir)
    names = sorted(p.name for p in found)
    assert names == ["a.pdf", "b.jpg", "d.png"]


def test_find_documents_missing_dir(tmp_path: Path) -> None:
    assert find_documents(tmp_path / "nope") == []


def test_file_hash_deterministic(tmp_path: Path) -> None:
    f = tmp_path / "x.bin"
    f.write_bytes(b"hello world")
    assert file_hash(f) == file_hash(f)


def test_file_hash_differs(tmp_path: Path) -> None:
    f1 = tmp_path / "x.bin"
    f1.write_bytes(b"hello")
    f2 = tmp_path / "y.bin"
    f2.write_bytes(b"world")
    assert file_hash(f1) != file_hash(f2)


def test_scan_and_index_adds_new(db_path: Path, docs_dir: Path) -> None:
    conn = connect(db_path)
    stats = scan_and_index(conn, docs_dir)
    assert stats.scanned == 3
    assert stats.added == 3
    assert stats.updated == 0
    assert stats.skipped == 0
    assert count_documents(conn) == 3


def test_scan_and_index_skips_unchanged(db_path: Path, docs_dir: Path) -> None:
    conn = connect(db_path)
    scan_and_index(conn, docs_dir)
    stats = scan_and_index(conn, docs_dir)
    assert stats.scanned == 3
    assert stats.added == 0
    assert stats.updated == 0
    assert stats.skipped == 3
    assert count_documents(conn) == 3


def test_scan_and_index_updates_changed(db_path: Path, docs_dir: Path) -> None:
    conn = connect(db_path)
    scan_and_index(conn, docs_dir)
    (docs_dir / "a.pdf").write_bytes(b"%PDF-1.4 MODIFIED content")
    stats = scan_and_index(conn, docs_dir)
    assert stats.scanned == 3
    assert stats.added == 0
    assert stats.updated == 1
    assert stats.skipped == 2


def test_is_changed_new_file(db_path: Path, docs_dir: Path) -> None:
    conn = connect(db_path)
    target = docs_dir / "a.pdf"
    assert is_changed(conn, target, file_hash(target)) is True


def test_is_changed_unchanged_after_scan(db_path: Path, docs_dir: Path) -> None:
    conn = connect(db_path)
    scan_and_index(conn, docs_dir)
    target = docs_dir / "a.pdf"
    assert is_changed(conn, target, file_hash(target)) is False


def test_scan_and_index_records_metadata(db_path: Path, docs_dir: Path) -> None:
    conn = connect(db_path)
    scan_and_index(conn, docs_dir)
    docs = get_all_documents(conn)
    assert all(d.size_bytes > 0 for d in docs)
    assert all(d.mtime > 0 for d in docs)
    assert all(d.text == "" for d in docs)
