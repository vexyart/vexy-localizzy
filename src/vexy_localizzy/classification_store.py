# this_file: src/vexy_localizzy/classification_store.py
"""Classification cache schema, including durable fallback choices and cooldowns."""

import sqlite3

APPLICATION_ID = 0x4C5A434C


def open_cache(path):
    db = sqlite3.connect(path, timeout=30)
    try:
        db.execute("BEGIN IMMEDIATE")
        app_id = db.execute("PRAGMA application_id").fetchone()[0]
        version = db.execute("PRAGMA user_version").fetchone()[0]
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        if app_id == 0 and not tables:
            db.execute(
                "CREATE TABLE responses(key TEXT PRIMARY KEY, model TEXT, endpoint TEXT, prompt TEXT, input TEXT, response TEXT)"
            )
            db.execute(
                "CREATE TABLE attempts(id INTEGER PRIMARY KEY, key TEXT, model TEXT, response TEXT, error TEXT)"
            )
            db.execute(f"PRAGMA application_id={APPLICATION_ID}")
            version = 2
        elif app_id != APPLICATION_ID or version not in (2, 3, 4, 5):
            raise ValueError("Unknown classification cache schema")
        if version == 2:
            db.execute(
                "CREATE TABLE cooldowns(endpoint TEXT, model TEXT, until REAL NOT NULL, reason TEXT NOT NULL, PRIMARY KEY(endpoint,model))"
            )
            db.execute(
                "CREATE TABLE selections(key TEXT PRIMARY KEY, models TEXT NOT NULL)"
            )
            db.execute("PRAGMA user_version=3")
            version = 3
        if version == 3:
            db.execute(
                "CREATE TABLE IF NOT EXISTS response_models(key TEXT PRIMARY KEY REFERENCES responses(key),model TEXT NOT NULL)"
            )
            db.execute("PRAGMA user_version=4")
            version = 4
        if version == 4:
            db.execute(
                "CREATE TABLE IF NOT EXISTS model_health(endpoint TEXT, model TEXT, state TEXT NOT NULL, last_success REAL, last_failure REAL, probe_after REAL, PRIMARY KEY(endpoint,model))"
            )
            db.execute("PRAGMA user_version=5")
        db.commit()
        return db
    except BaseException:
        db.close()
        raise
