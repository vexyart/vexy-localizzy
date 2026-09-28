# this_file: src/vexy_localizzy/experimental/classification_run_completion.py
"""Seal a producer-owned complete snapshot only after replaying all evidence."""

import sqlite3
from pathlib import Path

from vexy_localizzy.experimental.classification_evidence import (
    Complete,
    InputMetadata,
    RunIdentity,
)
from vexy_localizzy.experimental.classification_results import (
    _reconcile,
    decision_digest,
)
from vexy_localizzy.experimental.classification_run_store import atomic_json


def finish_run(
    db: sqlite3.Connection,
    directory: Path,
    inputs: Path,
    metadata: InputMetadata,
    identity: RunIdentity,
    run_id: str,
    rare: set[str],
) -> dict:
    db.execute("BEGIN")
    try:
        count = db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        pending = db.execute("SELECT COUNT(*) FROM pending_batches").fetchone()[0]
        if count > metadata.entries:
            raise ValueError("Classification contains extra decisions")
        report = {
            "run_id": run_id,
            "entries": count,
            "expected_entries": metadata.entries,
            "pending_entries": metadata.entries - count,
            "complete": count == metadata.entries and pending == 0,
            "classes": dict(
                db.execute("SELECT class,COUNT(*) FROM decisions GROUP BY class")
            ),
            "rare_locales": sorted(rare),
        }
        if report["complete"]:
            report["decision_sha256"] = decision_digest(db)
            _reconcile(db, inputs, identity, Complete.model_validate(report), run_id)
        atomic_json(
            directory / ("complete.json" if report["complete"] else "pending.json"),
            report,
        )
    finally:
        db.rollback()
    if report["complete"]:
        (directory / "pending.json").unlink(missing_ok=True)
    return report
