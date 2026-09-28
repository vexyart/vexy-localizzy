# this_file: src/vexy_localizzy/classification_results.py
"""Bounded reconciliation of completed decisions against their frozen input."""

import hashlib
import json
import sqlite3
from collections import Counter
from contextlib import closing, contextmanager
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path

from vexy_localizzy.classification_evidence import (
    Complete,
    InputEntry,
    InputMetadata,
    RunIdentity,
    check_decision,
    checked_models,
    policy,
)

ROWS = """SELECT d.entry_id,d.class,d.votes,d.reason,d.disagreement,
 m.models,m.requested_models,m.reported_models,m.identity_verified
 FROM decisions d JOIN decision_models m USING(entry_id) ORDER BY d.entry_id"""


def decision_digest(db: sqlite3.Connection) -> str:
    """Hash ordered decisions/model evidence for a producer's completion marker.

    The producer must hold one read transaction while counting and hashing its
    completed run. This fingerprint alone does not prove completion or correctness.
    """
    digest = hashlib.sha256()
    with closing(db.execute(ROWS)) as rows:
        for row in rows:
            digest.update(
                json.dumps(
                    list(row), ensure_ascii=False, separators=(",", ":")
                ).encode()
                + b"\n"
            )
    return digest.hexdigest()


@dataclass(frozen=True)
class ClassificationResults:
    """A checked read snapshot; consume its IDs inside validated_results' context."""

    _db: sqlite3.Connection
    metadata: InputMetadata
    report: dict

    def selected_ids(self):
        """Stream exactly the A/B source IDs in stable numeric order."""
        with closing(
            self._db.execute(
                "SELECT entry_id FROM decisions WHERE class IN ('A','B') ORDER BY entry_id"
            )
        ) as rows:
            for (key,) in rows:
                yield key


def _reconcile(db, inputs, identity, complete, run_id):
    digest, evidence_digest = hashlib.sha256(), hashlib.sha256()
    classes, coverage = Counter(), Counter()
    previous, fully_reported = 0, 0
    with inputs.open("rb") as stream:
        header = stream.readline()
        digest.update(header)
        metadata = InputMetadata.model_validate_json(header)
        if metadata.source_snapshot != identity.source_snapshot:
            raise ValueError("Classification source snapshot does not match its input")
        chains, rare = policy(identity, metadata)
        with closing(db.execute(ROWS)) as rows:
            for line, row in zip_longest(stream, rows):
                if line is None or row is None:
                    raise ValueError(
                        "Classification decisions do not cover every input ID"
                    )
                digest.update(line)
                entry = InputEntry.model_validate_json(line)
                if entry.id <= previous or entry.id != row["entry_id"]:
                    raise ValueError("Classification input IDs and decisions differ")
                if entry.locales != sorted(set(entry.locales)) or not entry.locales:
                    raise ValueError(
                        "Input locales must be nonempty, unique and sorted"
                    )
                previous = entry.id
                check_decision(row, entry, rare)
                fully_reported += checked_models(row, identity, chains)
                classes[row["class"]] += 1
                coverage.update(entry.locales)
                evidence_digest.update(
                    json.dumps(
                        list(row), ensure_ascii=False, separators=(",", ":")
                    ).encode()
                    + b"\n"
                )
    if evidence_digest.hexdigest() != complete.decision_sha256:
        raise ValueError("Classification decision digest changed since completion")
    if digest.hexdigest() != identity.input_sha256:
        raise ValueError("Classification input hash changed")
    count = sum(classes.values())
    if (
        count != metadata.entries
        or count != complete.entries
        or count != complete.expected_entries
    ):
        raise ValueError("Classification entry counts disagree")
    if (
        dict(coverage) != metadata.coverage
        or dict(classes) != complete.classes
        or sorted(rare) != complete.rare_locales
    ):
        raise ValueError("Classification coverage, classes or rarity report disagrees")
    for table in ("decisions", "decision_models"):
        if db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != count:
            raise ValueError("Classification contains missing or extra evidence rows")
    report = {
        "version": 1,
        "run_id": run_id,
        "input_sha256": digest.hexdigest(),
        "decision_sha256": evidence_digest.hexdigest(),
        "source_snapshot": metadata.source_snapshot,
        "entry_map_sha256": metadata.entry_map_sha256,
        "entries": count,
        "classes": dict(classes),
        "rare_locales": sorted(rare),
        "selected_entries": classes["A"] + classes["B"],
        "fully_reported_entries": fully_reported,
    }
    return ClassificationResults(db, metadata, report)


@contextmanager
def validated_results(directory: str | Path, inputs: str | Path):
    """Require a completion marker and replay all saved evidence before exposing IDs.

    Reads remain in one SQLite transaction through export. Missing votes, unknown
    model identities, changed inputs and inconsistent summaries fail before yielding.
    """
    directory, inputs = Path(directory).resolve(), Path(inputs).resolve()
    try:
        marker = (directory / "complete.json").read_bytes()
    except FileNotFoundError as error:
        raise ValueError(
            "Classification is incomplete: no completion marker"
        ) from error
    complete = Complete.model_validate_json(marker)
    if not complete.complete:
        raise ValueError("Classification is incomplete")
    raw_identity = (directory / "identity.json").read_bytes()
    identity = RunIdentity.model_validate_json(raw_identity)
    run_id = hashlib.sha256(
        json.dumps(json.loads(raw_identity), sort_keys=True).encode()
    ).hexdigest()
    if run_id != complete.run_id:
        raise ValueError(
            "Classification run identity does not match its completion marker"
        )
    with closing(
        sqlite3.connect(
            (directory / "decisions.sqlite").as_uri() + "?mode=ro", uri=True
        )
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN")
        try:
            if db.execute("SELECT 1 FROM pending_batches LIMIT 1").fetchone():
                raise ValueError("Classification still contains pending batches")
            yield _reconcile(db, inputs, identity, complete, run_id)
        finally:
            db.rollback()
