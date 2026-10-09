from __future__ import annotations

import queue
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, StringVar, Tk, filedialog, messagebox
from tkinter import ttk

from papertrail.db import Document, connect, get_all_documents, init_db, search_documents
from papertrail.indexer import index_folder


DB_FILENAME = "papertrail.db"


def default_db_path() -> Path:
    return Path.home() / DB_FILENAME


def format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_document_row(doc: Document) -> tuple[str, str, str, str]:
    name = Path(doc.path).name
    lang = doc.language.upper() if doc.language != "unknown" else "—"
    return (name, lang, format_size(doc.size_bytes), doc.indexed_at)


def open_in_system(path: str) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif sys.platform.startswith("win"):
        subprocess.Popen(["start", path], shell=True)
    else:
        subprocess.Popen(["xdg-open", path])


class PapertrailApp:
    def __init__(self, root: Tk, db_path: Path | None = None) -> None:
        self.root = root
        self.db_path = db_path or default_db_path()
        init_db(self.db_path)
        self.conn: sqlite3.Connection = connect(self.db_path)

        self.root.title("papertrail")
        self.root.geometry("900x560")
        self.root.minsize(700, 400)

        self.search_var = StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_results())

        self._result_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._build_widgets()
        self.refresh_results()

        self.root.after(100, self._poll_queue)

    def _build_widgets(self) -> None:
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=X)

        self.index_button = ttk.Button(
            top, text="Выбрать папку и проиндексировать", command=self.on_index_click
        )
        self.index_button.pack(side=LEFT)

        self.status_label = ttk.Label(top, text="Готов")
        self.status_label.pack(side=RIGHT)

        search_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        search_frame.pack(fill=X)

        ttk.Label(search_frame, text="Поиск:").pack(side=LEFT)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=LEFT, fill=X, expand=True, padx=(8, 0))

        columns = ("name", "lang", "size", "indexed_at")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings")
        self.tree.heading("name", text="Файл")
        self.tree.heading("lang", text="Язык")
        self.tree.heading("size", text="Размер")
        self.tree.heading("indexed_at", text="Проиндексирован")
        self.tree.column("name", width=420)
        self.tree.column("lang", width=80, anchor="center")
        self.tree.column("size", width=100, anchor="e")
        self.tree.column("indexed_at", width=180)

        self.tree.bind("<Double-1>", self.on_row_double_click)

        scroll = ttk.Scrollbar(self.root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True, padx=(10, 0), pady=(0, 10))
        scroll.pack(side=RIGHT, fill=Y, pady=(0, 10))

        self._doc_paths: dict[str, str] = {}

    def refresh_results(self) -> None:
        query = self.search_var.get().strip()
        if query:
            docs = search_documents(self.conn, query)
        else:
            docs = get_all_documents(self.conn)

        for row in self.tree.get_children():
            self.tree.delete(row)

        self._doc_paths.clear()
        for doc in docs:
            values = format_document_row(doc)
            item_id = self.tree.insert("", END, values=values)
            self._doc_paths[item_id] = doc.path

        self.status_label.config(text=f"Найдено: {len(docs)}")

    def on_index_click(self) -> None:
        folder = filedialog.askdirectory(title="Выберите папку с документами")
        if not folder:
            return
        self.index_button.config(state="disabled")
        self.status_label.config(text="Индексация...")
        thread = threading.Thread(target=self._run_index, args=(Path(folder),), daemon=True)
        thread.start()

    def _run_index(self, folder: Path) -> None:
        try:
            stats = index_folder(self.conn, folder)
            self._result_queue.put(("ok", stats))
        except Exception as e:
            self._result_queue.put(("error", str(e)))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self._result_queue.get_nowait()
                if kind == "ok":
                    stats = payload
                    msg = (
                        f"Всего: {stats.total}, "
                        f"новых: {stats.indexed}, "
                        f"пропущено: {stats.skipped}, "
                        f"ошибок: {len(stats.errors)}"
                    )
                    self.status_label.config(text=msg)
                    self.index_button.config(state="normal")
                    self.refresh_results()
                    if stats.errors:
                        messagebox.showwarning(
                            "papertrail",
                            "Некоторые файлы не удалось обработать:\n\n"
                            + "\n".join(stats.errors[:5]),
                        )
                elif kind == "error":
                    self.status_label.config(text="Ошибка")
                    self.index_button.config(state="normal")
                    messagebox.showerror("papertrail", f"Ошибка индексации:\n{payload}")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_queue)

    def on_row_double_click(self, _event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        path = self._doc_paths.get(selection[0])
        if not path:
            return
        try:
            open_in_system(path)
        except Exception as e:
            messagebox.showerror("papertrail", f"Не удалось открыть файл:\n{e}")


def run() -> None:
    root = Tk()
    PapertrailApp(root)
    root.mainloop()
