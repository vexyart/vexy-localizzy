# this_file: src/vexy_localizzy/translate/store.py
"""Atomic SQLite schema and portable identities for translation response caches."""

import hashlib
import json
import sqlite3

APPLICATION_ID = 0x4C5A5452
SCHEMA = (
    "CREATE TABLE responses(key TEXT PRIMARY KEY,model TEXT NOT NULL,request_sha256 TEXT NOT NULL,result TEXT NOT NULL,checksum TEXT NOT NULL)",
    "CREATE TABLE selections(key TEXT PRIMARY KEY,response_key TEXT NOT NULL REFERENCES responses(key))",
    "CREATE TABLE cooldowns(endpoint TEXT NOT NULL,model TEXT NOT NULL,until REAL NOT NULL,reason TEXT NOT NULL,PRIMARY KEY(endpoint,model))",
    "CREATE TABLE attempts(response_key TEXT NOT NULL,model TEXT NOT NULL,error TEXT NOT NULL)",
)


def encoded(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value) -> str:
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def open_store(path):
    db = sqlite3.connect(path, timeout=30)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        app_id = db.execute("PRAGMA application_id").fetchone()[0]
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        if app_id == 0 and not tables:
            for statement in SCHEMA:
                db.execute(statement)
            db.execute(f"PRAGMA application_id={APPLICATION_ID}")
            db.execute("PRAGMA user_version=1")
        elif (
            app_id != APPLICATION_ID
            or db.execute("PRAGMA user_version").fetchone()[0] != 1
        ):
            raise ValueError("Unknown translation cache schema")
        db.commit()
        return db
    except BaseException:
        db.close()
        raise
