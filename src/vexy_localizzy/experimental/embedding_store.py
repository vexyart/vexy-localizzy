# this_file: src/vexy_localizzy/experimental/embedding_store.py
"""SQLite boundary and checksums for normalized float32 source embeddings."""

import hashlib
import json
import sqlite3

import numpy as np

APPLICATION_ID = 0x4C5A454D


def identity(engine) -> str:
    """Include uubed's model/revision/prompt/backend and output settings."""
    if not isinstance(engine.space, str) or not engine.space:
        raise ValueError("Missing embedding space identity")
    if not isinstance(engine.cache_identity, str) or not engine.cache_identity:
        raise ValueError("Missing embedding output identity")
    if type(engine.dimensions) is not int or engine.dimensions < 1:
        raise ValueError("Invalid embedding dimensions")
    return json.dumps(
        {
            "space": engine.space,
            "cache_identity": engine.cache_identity,
            "dimensions": engine.dimensions,
            "encoding": "float32-le",
            "normalization": "l2",
        },
        sort_keys=True,
    )


def open_store(path, metadata: str):
    db = sqlite3.connect(path, timeout=30)
    try:
        db.execute("BEGIN IMMEDIATE")
        app_id = db.execute("PRAGMA application_id").fetchone()[0]
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        if app_id == 0 and not tables:
            db.execute("CREATE TABLE metadata(identity TEXT NOT NULL)")
            db.execute("INSERT INTO metadata VALUES (?)", (metadata,))
            db.execute(
                "CREATE TABLE embeddings(source_id INTEGER PRIMARY KEY, text TEXT NOT NULL, vector BLOB NOT NULL, checksum TEXT NOT NULL)"
            )
            db.execute(f"PRAGMA application_id={APPLICATION_ID}")
            db.execute("PRAGMA user_version=1")
        elif (
            app_id != APPLICATION_ID
            or db.execute("PRAGMA user_version").fetchone()[0] != 1
        ):
            raise ValueError("Unknown embedding cache schema")
        if db.execute("SELECT identity FROM metadata").fetchall() != [(metadata,)]:
            raise ValueError("Embedding identity differs; use a separate cache")
        db.commit()
        return db
    except BaseException:
        db.close()
        raise


def validate_vectors(values, count: int, dimensions: int) -> np.ndarray:
    vectors = np.asarray(values, dtype="<f4")
    if vectors.shape != (count, dimensions) or not np.isfinite(vectors).all():
        raise ValueError("Invalid embedding vector shape or values")
    if not np.allclose(
        np.linalg.norm(vectors.astype(np.float64), axis=1), 1, atol=1e-5
    ):
        raise ValueError("Embedding vectors must be L2 normalized")
    return vectors


def checksum(source_id: int, text: str, vector: bytes) -> str:
    return hashlib.sha256(
        str(source_id).encode() + b"\0" + text.encode() + b"\0" + vector
    ).hexdigest()


def decode(row, dimensions: int) -> np.ndarray:
    source_id, text, vector, saved = row
    if checksum(source_id, text, vector) != saved:
        raise ValueError(f"Embedding checksum mismatch for source {source_id}")
    values = np.frombuffer(vector, dtype="<f4")
    return validate_vectors(values[None, :], 1, dimensions)[0]
