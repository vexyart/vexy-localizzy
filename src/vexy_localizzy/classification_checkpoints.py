# this_file: src/vexy_localizzy/classification_checkpoints.py
"""Bind each committed classification batch to its payload and exact decisions."""

import hashlib
import json
import sqlite3
import time

from vexy_localizzy.classification import Entry, consensus, request_text
from vexy_localizzy.classification_cache import ClassificationBatch
from vexy_localizzy.classification_evidence import (
    RunIdentity,
    check_decision,
    checked_models,
)
from vexy_localizzy.classification_models import model_chains
from vexy_localizzy.classification_results import ROWS


def batch_key(batch: list[Entry]) -> str:
    return hashlib.sha256(
        json.dumps([entry.id for entry in batch]).encode()
    ).hexdigest()


def payload_digest(batch: list[Entry], coverage: dict[str, int]) -> str:
    return hashlib.sha256(request_text(batch, coverage).encode()).hexdigest()


def check_dispatch(
    db: sqlite3.Connection, batch: list[Entry], coverage: dict[str, int]
) -> None:
    """Do not dispatch or commit data that differs from the verified preflight."""
    row = db.execute(
        "SELECT input_sha256 FROM dispatch_inputs WHERE key=?", (batch_key(batch),)
    ).fetchone()
    if row is None or row[0] != payload_digest(batch, coverage):
        raise ValueError("Classification input changed after preflight")


def rows_for(db: sqlite3.Connection, batch: list[Entry]) -> list[sqlite3.Row]:
    marks = ",".join("?" for _ in batch)
    sql = ROWS.replace(
        "ORDER BY d.entry_id", f"WHERE d.entry_id IN ({marks}) ORDER BY d.entry_id"
    )
    return db.execute(sql, [entry.id for entry in batch]).fetchall()


def rows_digest(rows: list[sqlite3.Row]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            json.dumps(list(row), ensure_ascii=False, separators=(",", ":")).encode()
            + b"\n"
        )
    return digest.hexdigest()


def check_saved(
    db: sqlite3.Connection,
    batch: list[Entry],
    coverage: dict[str, int],
    identity: RunIdentity,
    rare: set[str],
) -> bool:
    checkpoint = db.execute(
        "SELECT * FROM completed_batches WHERE key=?", (batch_key(batch),)
    ).fetchone()
    rows = rows_for(db, batch)
    if checkpoint is None:
        if rows:
            raise ValueError("Unsealed existing classification decisions")
        return False
    if (
        checkpoint["entries"] != len(batch)
        or len(rows) != len(batch)
        or checkpoint["input_sha256"] != payload_digest(batch, coverage)
        or checkpoint["decision_sha256"] != rows_digest(rows)
    ):
        raise ValueError("Classification batch checkpoint changed")
    chains = model_chains(identity.models, identity.fallbacks)
    for entry, row in zip(batch, rows, strict=True):
        if entry.id != row["entry_id"]:
            raise ValueError("Checkpoint entry IDs differ")
        check_decision(row, entry, rare)
        checked_models(row, identity, chains)
    return True


def save_batch(
    db: sqlite3.Connection,
    batch: list[Entry],
    result: ClassificationBatch,
    coverage: dict[str, int],
    rare: set[str],
) -> None:
    check_dispatch(db, batch, coverage)
    key = batch_key(batch)
    with db:
        for entry in batch:
            votes = result.votes[entry.id]
            decision = consensus(votes, entry.locales, rare)
            db.execute(
                "INSERT INTO decisions VALUES (?,?,?,?,?)",
                (
                    entry.id,
                    decision["class"],
                    json.dumps(votes),
                    decision["reason"],
                    decision["disagreement"],
                ),
            )
            db.execute(
                "INSERT INTO decision_models VALUES (?,?,?,?,?)",
                (
                    entry.id,
                    json.dumps(result.models),
                    json.dumps(result.requested_models),
                    json.dumps(result.reported_models),
                    result.identity_verified,
                ),
            )
        db.execute(
            "INSERT INTO completed_batches VALUES (?,?,?,?)",
            (
                key,
                payload_digest(batch, coverage),
                rows_digest(rows_for(db, batch)),
                len(batch),
            ),
        )
        db.execute("DELETE FROM pending_batches WHERE key=?", (key,))


def save_pending(db: sqlite3.Connection, batch: list[Entry], error: Exception) -> None:
    with db:
        db.execute(
            "INSERT OR REPLACE INTO pending_batches VALUES (?,?,?,?)",
            (
                batch_key(batch),
                json.dumps([e.id for e in batch]),
                str(error),
                time.time(),
            ),
        )
