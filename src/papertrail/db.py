from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    file_hash TEXT NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    mtime REAL NOT NULL DEFAULT 0,
    indexed_at TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'unknown'
);

CREATE INDEX IF NOT EXISTS idx_documents_path ON documents(path);
CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
"""


@dataclass
class Document:
    id: int | None
    path: str
    file_hash: str
    text: str
    size_bytes: int
    mtime: float
    indexed_at: str
    language: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Document":
        return cls(
            id=row["id"],
            path=row["path"],
            file_hash=row["file_hash"],
            text=row["text"],
            size_bytes=row["size_bytes"],
            mtime=row["mtime"],
            indexed_at=row["indexed_at"],
            language=row["language"],
        )


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: str | Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def upsert_document(
    conn: sqlite3.Connection,
    path: str,
    file_hash: str,
    text: str,
    size_bytes: int,
    mtime: float,
    language: str = "unknown",
) -> int:
    indexed_at = datetime.utcnow().isoformat(timespec="seconds")
    cur = conn.execute(
        """
        INSERT INTO documents (path, file_hash, text, size_bytes, mtime, indexed_at, language)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            file_hash = excluded.file_hash,
            text = excluded.text,
            size_bytes = excluded.size_bytes,
            mtime = excluded.mtime,
            indexed_at = excluded.indexed_at,
            language = excluded.language
        """,
        (path, file_hash, text, size_bytes, mtime, indexed_at, language),
    )
    conn.commit()
    if cur.lastrowid:
        return cur.lastrowid
    row = conn.execute("SELECT id FROM documents WHERE path = ?", (path,)).fetchone()
    return int(row["id"])


def search_documents(conn: sqlite3.Connection, query: str, limit: int = 100) -> list[Document]:
    pattern = f"%{query}%"
    rows = conn.execute(
        """
        SELECT * FROM documents
        WHERE text LIKE ? OR path LIKE ?
        ORDER BY indexed_at DESC
        LIMIT ?
        """,
        (pattern, pattern, limit),
    ).fetchall()
    return [Document.from_row(r) for r in rows]


def get_all_documents(conn: sqlite3.Connection, limit: int = 1000) -> list[Document]:
    rows = conn.execute(
        "SELECT * FROM documents ORDER BY indexed_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [Document.from_row(r) for r in rows]


def get_document_by_id(conn: sqlite3.Connection, doc_id: int) -> Document | None:
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    return Document.from_row(row) if row else None


def count_documents(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM documents").fetchone()
    return int(row["c"])


def delete_document(conn: sqlite3.Connection, doc_id: int) -> None:
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
