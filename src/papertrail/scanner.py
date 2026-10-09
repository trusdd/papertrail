from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from papertrail.db import upsert_document


SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".bmp",
})

CHUNK_SIZE = 1024 * 1024


@dataclass
class ScanStats:
    scanned: int = 0
    added: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def find_documents(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if not root.is_dir():
        return []
    found: list[Path] = []
    for entry in root.rglob("*"):
        if entry.is_file() and is_supported(entry):
            found.append(entry)
    return found


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def get_stored_hash(conn: sqlite3.Connection, path: str) -> str | None:
    row = conn.execute(
        "SELECT file_hash FROM documents WHERE path = ?", (path,)
    ).fetchone()
    return row["file_hash"] if row else None


def is_changed(conn: sqlite3.Connection, path: Path, current_hash: str) -> bool:
    stored = get_stored_hash(conn, str(path))
    return stored != current_hash


def scan_and_index(conn: sqlite3.Connection, root: Path) -> ScanStats:
    stats = ScanStats()
    for file_path in find_documents(root):
        stats.scanned += 1
        try:
            current_hash = file_hash(file_path)
        except OSError as e:
            stats.errors.append(f"{file_path}: {e}")
            continue

        stored_hash = get_stored_hash(conn, str(file_path))
        if stored_hash == current_hash:
            stats.skipped += 1
            continue

        stat = file_path.stat()
        upsert_document(
            conn=conn,
            path=str(file_path),
            file_hash=current_hash,
            text="",
            size_bytes=stat.st_size,
            mtime=stat.st_mtime,
        )

        if stored_hash is None:
            stats.added += 1
        else:
            stats.updated += 1

    return stats
