# this_file: src/vexy_localizzy/experimental/classification_run_store.py
"""Atomic producer identity and files; never adopt an unbound legacy database."""

import json
import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

APPLICATION_ID = 0x4C5A4352
SCHEMA = (
    "CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)",
    "CREATE TABLE decisions(entry_id INTEGER PRIMARY KEY,class TEXT NOT NULL,votes TEXT NOT NULL,reason TEXT NOT NULL,disagreement INTEGER NOT NULL)",
    "CREATE TABLE decision_models(entry_id INTEGER PRIMARY KEY,models TEXT NOT NULL,requested_models TEXT NOT NULL,reported_models TEXT NOT NULL,identity_verified INTEGER NOT NULL)",
    "CREATE TABLE pending_batches(key TEXT PRIMARY KEY,ids TEXT NOT NULL,error TEXT NOT NULL,updated REAL NOT NULL)",
    "CREATE TABLE completed_batches(key TEXT PRIMARY KEY,input_sha256 TEXT NOT NULL,decision_sha256 TEXT NOT NULL,entries INTEGER NOT NULL)",
)


def atomic_json(path: Path, value: dict) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, mode="w", encoding="utf-8", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@contextmanager
def open_run(directory: Path, identity: dict) -> Iterator[sqlite3.Connection]:
    """Require the native schema and immutable identity before any decision writes."""
    encoded = json.dumps(identity, sort_keys=True)
    path = directory / "identity.json"
    if path.exists() and json.loads(path.read_text()) != identity:
        raise ValueError("Classification run identity changed; use a new run directory")
    with closing(sqlite3.connect(directory / "decisions.sqlite", timeout=30)) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN IMMEDIATE")
        try:
            app_id = db.execute("PRAGMA application_id").fetchone()[0]
            tables = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if app_id == 0 and not tables:
                for sql in SCHEMA:
                    db.execute(sql)
                db.execute(f"PRAGMA application_id={APPLICATION_ID}")
                db.execute("PRAGMA user_version=1")
                db.execute("INSERT INTO metadata VALUES (?,?)", ("identity", encoded))
            elif (
                app_id != APPLICATION_ID
                or db.execute("PRAGMA user_version").fetchone()[0] != 1
            ):
                raise ValueError("Unknown or unbound classification run database")
            saved = db.execute(
                "SELECT value FROM metadata WHERE key='identity'"
            ).fetchone()
            if saved is None or saved[0] != encoded:
                raise ValueError("Classification database belongs to another run")
            db.commit()
        except BaseException:
            db.rollback()
            raise
        if not path.exists():
            atomic_json(path, identity)
        yield db
