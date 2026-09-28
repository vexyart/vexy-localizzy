# this_file: src/vexy_localizzy/source_store.py
"""Persist source revisions and their explicitly configured voting identities."""

import sqlite3
from pathlib import Path

from vexy_localizzy.source_policy import SourcePolicy


def family_id(db: sqlite3.Connection, name: str, weight: int) -> int:
    db.execute(
        "INSERT OR IGNORE INTO families(name,weight) VALUES (?,?)", (name, weight)
    )
    row = db.execute("SELECT id,weight FROM families WHERE name=?", (name,)).fetchone()
    if row["weight"] != weight:
        raise ValueError("Existing family has a different weight")
    return row["id"]


def origin_id(db: sqlite3.Connection, path: str, digest: str, archived: str) -> int:
    db.execute(
        "INSERT OR IGNORE INTO origins(path,sha256,snapshot) VALUES (?,?,?)",
        (path, digest, archived),
    )
    return db.execute(
        "SELECT id FROM origins WHERE path=? AND sha256=?", (path, digest)
    ).fetchone()[0]


def prepare(
    db: sqlite3.Connection,
    path: Path,
    digest: str,
    archived: Path,
    policy: SourcePolicy,
) -> tuple[sqlite3.Row, int]:
    existing = db.execute(
        "SELECT policy FROM sources WHERE sha256=? AND path<>? AND active=1 AND status='complete' AND policy<>? LIMIT 1",
        (digest, str(path), policy.identity),
    ).fetchone()
    if existing:
        raise ValueError(
            "Identical source bytes already have a different family policy"
        )
    with db:
        family = family_id(db, policy.family, policy.weight)
        db.execute(
            "INSERT OR IGNORE INTO sources(path,sha256,snapshot,family_id,policy,status) VALUES (?,?,?,?,?,'importing')",
            (str(path), digest, str(archived), family, policy.identity),
        )
        origin = origin_id(db, str(path), digest, str(archived))
    source = db.execute(
        "SELECT * FROM sources WHERE path=? AND sha256=? AND policy=?",
        (str(path), digest, policy.identity),
    ).fetchone()
    return source, origin
