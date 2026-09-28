# this_file: src/vexy_localizzy/experimental/distillation_store.py
"""Durable pass inputs and decisions; completed SQLite artifacts are immutable."""

import hashlib
import json
import sqlite3
from dataclasses import dataclass

import numpy as np

from vexy_localizzy.experimental.distillation import DistillationEntry
from vexy_localizzy.experimental.embedding_store import validate_vectors

APPLICATION_ID = 0x4C5A4450


@dataclass(frozen=True)
class ClusterEntry:
    cluster_id: int
    entry: DistillationEntry
    vector: np.ndarray


def encoded(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(cluster, data, vector):
    return hashlib.sha256(
        str(cluster).encode() + b"\0" + data.encode() + b"\0" + vector
    ).hexdigest()


def open_pass(path, identity, *, readonly=False):
    db = sqlite3.connect(
        path.as_uri() + ("?mode=ro" if readonly else "?mode=rwc"), uri=True
    )
    try:
        app = db.execute("PRAGMA application_id").fetchone()[0]
        if not app and not db.execute("SELECT 1 FROM sqlite_master").fetchone():
            db.executescript(f"""
                BEGIN IMMEDIATE;
                PRAGMA application_id={APPLICATION_ID}; PRAGMA user_version=1;
                CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE entries(source_id INTEGER PRIMARY KEY,cluster_id INTEGER NOT NULL,data TEXT NOT NULL,vector BLOB NOT NULL,checksum TEXT NOT NULL);
                CREATE INDEX cluster_entries ON entries(cluster_id,source_id);
                CREATE TABLE chunks(id INTEGER PRIMARY KEY,cluster_id INTEGER NOT NULL,ids TEXT NOT NULL,decision TEXT NOT NULL);
                CREATE TABLE results(source_id INTEGER PRIMARY KEY REFERENCES entries,action TEXT NOT NULL CHECK(action IN ('keep','drop')),representative_id INTEGER REFERENCES entries,reason TEXT NOT NULL,chunk_id INTEGER REFERENCES chunks);
                CREATE INDEX representatives ON results(representative_id);
                CREATE INDEX result_chunks ON results(chunk_id);
                CREATE TABLE pending(cluster_id INTEGER PRIMARY KEY,error TEXT NOT NULL);
            """)
            db.execute(
                "INSERT INTO metadata VALUES ('identity',?)", (encoded(identity),)
            )
            db.commit()
        elif (
            app != APPLICATION_ID
            or db.execute("PRAGMA user_version").fetchone()[0] != 1
        ):
            raise ValueError("Unknown distillation pass schema")
        if db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone() != (
            encoded(identity),
        ):
            raise ValueError("Pass identity changed; use a separate output")
        db.execute("PRAGMA foreign_keys=ON")
        return db
    except BaseException:
        db.close()
        raise


def ingest(db, items, count, dimensions):
    """Reconcile every input on resume before any model call; commit bounded batches."""
    digest, previous, total = hashlib.sha256(), (-1, -1), 0
    sealed = (
        db.execute("SELECT 1 FROM metadata WHERE key='input_sha256'").fetchone()
        is not None
    )
    for item in items:
        entry = DistillationEntry.model_validate(item.entry.model_dump())
        key = (item.cluster_id, entry.id)
        if type(item.cluster_id) is not int or item.cluster_id < 0 or key <= previous:
            raise ValueError("Inputs must have strictly ordered cluster/source IDs")
        previous = key
        data = encoded(entry.model_dump())
        vector = validate_vectors(np.asarray(item.vector)[None, :], 1, dimensions)[
            0
        ].tobytes()
        checksum = fingerprint(item.cluster_id, data, vector)
        row = (entry.id, item.cluster_id, data, vector, checksum)
        existing = db.execute(
            "SELECT * FROM entries WHERE source_id=?", (entry.id,)
        ).fetchone()
        if existing is None:
            if sealed:
                raise ValueError(f"Changed pass input ID {entry.id}")
            db.execute("INSERT INTO entries VALUES (?,?,?,?,?)", row)
        elif existing != row:
            raise ValueError(f"Changed pass input for source {entry.id}")
        digest.update(bytes.fromhex(checksum))
        total += 1
        if total % 128 == 0:
            db.commit()
    if (
        total != count
        or db.execute("SELECT COUNT(*) FROM entries").fetchone()[0] != count
    ):
        raise ValueError("Pass input count differs from expected count")
    stored = db.execute(
        "SELECT value FROM metadata WHERE key='input_sha256'"
    ).fetchone()
    if stored is None:
        db.execute(
            "INSERT INTO metadata VALUES ('input_sha256',?)", (digest.hexdigest(),)
        )
    elif stored != (digest.hexdigest(),):
        raise ValueError("Pass input checksum changed")
    db.commit()


def load_item(row):
    source_id, cluster, data, vector, checksum = row
    if fingerprint(cluster, data, vector) != checksum:
        raise ValueError(f"Corrupt pass input for source {source_id}")
    entry = DistillationEntry.model_validate(json.loads(data))
    if entry.id != source_id:
        raise ValueError("Pass input identity mismatch")
    return ClusterEntry(cluster, entry, np.frombuffer(vector, dtype="<f4"))


def save_chunk(db, cluster, items, decision):
    ids = [item.entry.id for item in items]
    if set(decision["kept"]) | {
        item["source_id"] for item in decision["dropped"]
    } != set(ids):
        raise ValueError("Incomplete chunk decision")
    with db:
        chunk = db.execute(
            "INSERT INTO chunks(cluster_id,ids,decision) VALUES (?,?,?)",
            (cluster, encoded(ids), encoded(decision)),
        ).lastrowid
        reasons = {item["source_id"]: item["reason"] for item in decision["overrides"]}
        rows = [
            (key, "keep", None, reasons.get(key, "model_keep"), chunk)
            for key in decision["kept"]
        ]
        rows += [
            (
                item["source_id"],
                "drop",
                item["representative_id"],
                "majority_equivalence",
                chunk,
            )
            for item in decision["dropped"]
        ]
        db.executemany(
            "INSERT INTO results VALUES (?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET action=excluded.action,representative_id=excluded.representative_id,reason=excluded.reason,chunk_id=excluded.chunk_id",
            rows,
        )


def validate_representatives(db):
    """Every removal must point directly to a retained member of the same cluster."""
    invalid = db.execute("""
        SELECT 1 FROM results d
        LEFT JOIN results r ON r.source_id=d.representative_id
        LEFT JOIN entries source ON source.source_id=d.source_id
        LEFT JOIN entries target ON target.source_id=d.representative_id
        WHERE d.action='drop' AND (r.source_id IS NULL OR r.action!='keep'
            OR source.cluster_id!=target.cluster_id OR d.source_id=d.representative_id)
        LIMIT 1
    """).fetchone()
    if invalid:
        raise ValueError("Dropped entry has no valid retained representative")


def report(db, identity):
    counts = dict(db.execute("SELECT action,COUNT(*) FROM results GROUP BY action"))
    processed = sum(counts.values())
    coverage = {"before": {}, "after": {}}
    for data, action in db.execute(
        "SELECT e.data,r.action FROM entries e LEFT JOIN results r USING(source_id)"
    ):
        for locale in json.loads(data)["targets"]:
            coverage["before"][locale] = coverage["before"].get(locale, 0) + 1
            if action == "keep":
                coverage["after"][locale] = coverage["after"].get(locale, 0) + 1
    pending = db.execute("SELECT COUNT(*) FROM pending").fetchone()[0]
    return {
        "complete": processed == identity["expected_count"] and not pending,
        "expected_count": identity["expected_count"],
        "processed": processed,
        "kept": counts.get("keep", 0),
        "dropped": counts.get("drop", 0),
        "pending_clusters": pending,
        "coverage": coverage,
        "pass_number": identity["pass_number"],
        "predecessor_sha256": identity["predecessor_sha256"],
        "input_sha256": db.execute(
            "SELECT value FROM metadata WHERE key='input_sha256'"
        ).fetchone()[0],
    }
