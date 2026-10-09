from pathlib import Path

import pytest

from papertrail import indexer as indexer_module
from papertrail.db import connect, count_documents, get_all_documents, init_db
from papertrail.indexer import index_file, index_folder


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    init_db(path)
    return path


@pytest.fixture
def docs_dir(tmp_path: Path) -> Path:
    d = tmp_path / "docs"
    d.mkdir()
    (d / "insurance.pdf").write_bytes(b"%PDF fake insurance")
    (d / "receipt.jpg").write_bytes(b"\xff\xd8\xff fake receipt")
    return d


def _fake_extract(text_by_name: dict[str, str]):
    def _extract(path: Path, lang: str = "rus+eng") -> str:
        return text_by_name.get(path.name, "")
    return _extract


def test_index_file_new(db_path: Path, docs_dir: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        indexer_module,
        "extract_text",
        _fake_extract({"insurance.pdf": "ОСАГО договор страхования"}),
    )
    conn = connect(db_path)
    changed = index_file(conn, docs_dir / "insurance.pdf")
    assert changed is True
    docs = get_all_documents(conn)
    assert len(docs) == 1
    assert "страхован" in docs[0].text
    assert docs[0].language == "rus"


def test_index_file_unchanged_is_skipped(db_path: Path, docs_dir: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        indexer_module,
        "extract_text",
        _fake_extract({"insurance.pdf": "text"}),
    )
    conn = connect(db_path)
    assert index_file(conn, docs_dir / "insurance.pdf") is True
    assert index_file(conn, docs_dir / "insurance.pdf") is False


def test_index_file_changed_is_reindexed(db_path: Path, docs_dir: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        indexer_module,
        "extract_text",
        _fake_extract({"insurance.pdf": "old text"}),
    )
    conn = connect(db_path)
    index_file(conn, docs_dir / "insurance.pdf")

    (docs_dir / "insurance.pdf").write_bytes(b"%PDF NEW CONTENT")
    monkeypatch.setattr(
        indexer_module,
        "extract_text",
        _fake_extract({"insurance.pdf": "new text"}),
    )
    assert index_file(conn, docs_dir / "insurance.pdf") is True
    docs = get_all_documents(conn)
    assert len(docs) == 1
    assert docs[0].text == "new text"


def test_index_folder_all_new(db_path: Path, docs_dir: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        indexer_module,
        "extract_text",
        _fake_extract({
            "insurance.pdf": "ОСАГО",
            "receipt.jpg": "квитанция",
        }),
    )
    conn = connect(db_path)
    stats = index_folder(conn, docs_dir)
    assert stats.total == 2
    assert stats.indexed == 2
    assert stats.skipped == 0
    assert count_documents(conn) == 2


def test_index_folder_second_run_skips_all(db_path: Path, docs_dir: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        indexer_module,
        "extract_text",
        _fake_extract({"insurance.pdf": "x", "receipt.jpg": "y"}),
    )
    conn = connect(db_path)
    index_folder(conn, docs_dir)
    stats = index_folder(conn, docs_dir)
    assert stats.indexed == 0
    assert stats.skipped == 2


def test_index_folder_records_errors(db_path: Path, docs_dir: Path, monkeypatch) -> None:
    def _boom(path: Path, lang: str = "rus+eng") -> str:
        raise RuntimeError("tesseract crashed")

    monkeypatch.setattr(indexer_module, "extract_text", _boom)
    conn = connect(db_path)
    stats = index_folder(conn, docs_dir)
    assert stats.indexed == 0
    assert len(stats.errors) == 2
