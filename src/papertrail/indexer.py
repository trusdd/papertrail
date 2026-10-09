from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from papertrail.db import upsert_document
from papertrail.ocr import detect_language, extract_text
from papertrail.scanner import file_hash, find_documents, get_stored_hash


@dataclass
class IndexStats:
    total: int = 0
    indexed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def index_file(conn: sqlite3.Connection, path: Path) -> bool:
    current_hash = file_hash(path)
    stored_hash = get_stored_hash(conn, str(path))
    if stored_hash == current_hash:
        return False

    text = extract_text(path)
    language = detect_language(text)
    stat = path.stat()

    upsert_document(
        conn=conn,
        path=str(path),
        file_hash=current_hash,
        text=text,
        size_bytes=stat.st_size,
        mtime=stat.st_mtime,
        language=language,
    )
    return True


def index_folder(conn: sqlite3.Connection, root: Path) -> IndexStats:
    stats = IndexStats()
    for file_path in find_documents(root):
        stats.total += 1
        try:
            changed = index_file(conn, file_path)
        except Exception as e:
            stats.errors.append(f"{file_path}: {e}")
            continue
        if changed:
            stats.indexed += 1
        else:
            stats.skipped += 1
    return stats
