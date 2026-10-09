from pathlib import Path

import pytest

from papertrail.db import (
    count_documents,
    delete_document,
    get_all_documents,
    get_document_by_id,
    init_db,
    connect,
    search_documents,
    upsert_document,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    init_db(path)
    return path


def test_init_db_creates_file(db_path: Path) -> None:
    assert db_path.exists()


def test_upsert_and_count(db_path: Path) -> None:
    conn = connect(db_path)
    upsert_document(conn, "/a/doc.pdf", "hash1", "hello world", 100, 1.0)
    upsert_document(conn, "/a/doc2.pdf", "hash2", "goodbye world", 200, 2.0)
    assert count_documents(conn) == 2


def test_upsert_updates_existing(db_path: Path) -> None:
    conn = connect(db_path)
    upsert_document(conn, "/a/doc.pdf", "hash1", "old text", 100, 1.0)
    upsert_document(conn, "/a/doc.pdf", "hash1", "new text", 100, 1.0)
    assert count_documents(conn) == 1
    docs = get_all_documents(conn)
    assert docs[0].text == "new text"


def test_search_by_text(db_path: Path) -> None:
    conn = connect(db_path)
    upsert_document(conn, "/a/insurance.pdf", "h1", "ОСАГО договор страхования", 100, 1.0)
    upsert_document(conn, "/a/receipt.pdf", "h2", "квитанция за свет", 200, 2.0)
    results = search_documents(conn, "страхован")
    assert len(results) == 1
    assert "insurance" in results[0].path


def test_search_by_path(db_path: Path) -> None:
    conn = connect(db_path)
    upsert_document(conn, "/docs/паспорт.pdf", "h1", "текст", 100, 1.0)
    upsert_document(conn, "/docs/снилс.pdf", "h2", "текст", 200, 2.0)
    results = search_documents(conn, "паспорт")
    assert len(results) == 1


def test_get_document_by_id(db_path: Path) -> None:
    conn = connect(db_path)
    doc_id = upsert_document(conn, "/a/doc.pdf", "h1", "text", 100, 1.0)
    doc = get_document_by_id(conn, doc_id)
    assert doc is not None
    assert doc.path == "/a/doc.pdf"


def test_delete_document(db_path: Path) -> None:
    conn = connect(db_path)
    doc_id = upsert_document(conn, "/a/doc.pdf", "h1", "text", 100, 1.0)
    delete_document(conn, doc_id)
    assert count_documents(conn) == 0


def test_language_field_stored(db_path: Path) -> None:
    conn = connect(db_path)
    upsert_document(conn, "/a/doc.pdf", "h1", "text", 100, 1.0, language="rus")
    doc = get_all_documents(conn)[0]
    assert doc.language == "rus"
