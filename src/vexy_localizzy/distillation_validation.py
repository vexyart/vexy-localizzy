# this_file: src/vexy_localizzy/distillation_validation.py
"""Bounded verification of every pass input and its retained decision evidence."""

import hashlib
import json

import numpy as np

from vexy_localizzy.distillation import decide
from vexy_localizzy.distillation_store import encoded, load_item
from vexy_localizzy.embedding_store import validate_vectors


def validate_inputs(db, identity):
    digest, count = hashlib.sha256(), 0
    for row in db.execute("SELECT * FROM entries ORDER BY cluster_id,source_id"):
        item = load_item(row)
        validate_vectors(
            item.vector[None, :], 1, identity["embedding_identity"]["dimensions"]
        )
        digest.update(bytes.fromhex(row[4]))
        count += 1
    if count != identity["expected_count"] or db.execute(
        "SELECT value FROM metadata WHERE key='input_sha256'"
    ).fetchone() != (digest.hexdigest(),):
        raise ValueError("Corrupt pass input digest/count")


def _validate_decision(db, chunk, items, decision, identity):
    ids = [item.entry.id for item in items]
    listed = decision["kept"] + [row["source_id"] for row in decision["dropped"]]
    if len(listed) != len(set(listed)) or set(listed) != set(ids):
        raise ValueError("Incomplete chunk evidence")
    if not decision["votes"]:
        if (
            len(ids) != 1
            or decision["kept"] != ids
            or decision["dropped"]
            or decision["overrides"]
            not in (
                [{"source_id": ids[0], "reason": "oversized_entry"}],
                [{"source_id": ids[0], "reason": "singleton_chunk"}],
            )
        ):
            raise ValueError("Missing model evidence")
        return
    actual = decision["resolved_models"]
    if (
        len(actual) != 3
        or len(set(actual)) != 3
        or set(actual) != set(decision["votes"])
    ):
        raise ValueError("Incomplete model identity evidence")
    expected = decide(
        [item.entry for item in items],
        np.stack([item.vector for item in items]),
        {model: encoded(vote) for model, vote in decision["votes"].items()},
        rare_locales=set(identity["rare_locales"]),
        threshold=identity["threshold"],
    )
    protected = {
        row["source_id"]
        for row in decision["overrides"]
        if row["reason"] == "protected_representative"
    }
    for key in protected:
        if not db.execute(
            "SELECT 1 FROM results WHERE representative_id=? AND chunk_id<? LIMIT 1",
            (key, chunk),
        ).fetchone():
            raise ValueError("Unsupported representative evidence")
    drops = [row for row in expected["dropped"] if row["source_id"] not in protected]
    kept = [key for key in ids if key not in {row["source_id"] for row in drops}]
    overrides = expected["overrides"] + [
        {"source_id": row["source_id"], "reason": "protected_representative"}
        for row in expected["dropped"]
        if row["source_id"] in protected
    ]
    if (
        drops != decision["dropped"]
        or kept != decision["kept"]
        or overrides != decision["overrides"]
    ):
        raise ValueError("Stored decisions disagree with model evidence")


def validate_evidence(db, identity):
    """Recompute bounded chunk policy and bind each final result to its latest vote."""
    if db.execute("PRAGMA foreign_key_check").fetchone():
        raise ValueError("Broken pass evidence references")
    try:
        for chunk, cluster, raw_ids, raw_decision in db.execute(
            "SELECT * FROM chunks ORDER BY id"
        ):
            ids, decision = json.loads(raw_ids), json.loads(raw_decision)
            if (
                not ids
                or len(ids) > identity["max_entries"]
                or len(set(ids)) != len(ids)
            ):
                raise ValueError("Invalid chunk evidence IDs")
            items = [
                load_item(
                    db.execute(
                        "SELECT * FROM entries WHERE source_id=?", (key,)
                    ).fetchone()
                )
                for key in ids
            ]
            if any(item.cluster_id != cluster for item in items):
                raise ValueError("Mixed cluster evidence")
            _validate_decision(db, chunk, items, decision, identity)
            reasons = {row["source_id"]: row["reason"] for row in decision["overrides"]}
            expected = {
                key: ("keep", None, reasons.get(key, "model_keep"))
                for key in decision["kept"]
            }
            expected.update(
                {
                    row["source_id"]: (
                        "drop",
                        row["representative_id"],
                        "majority_equivalence",
                    )
                    for row in decision["dropped"]
                }
            )
            for key in ids:
                row = db.execute(
                    "SELECT action,representative_id,reason,chunk_id FROM results WHERE source_id=?",
                    (key,),
                ).fetchone()
                if (
                    row is None
                    or row[3] < chunk
                    or (row[3] == chunk and row[:3] != expected[key])
                ):
                    raise ValueError("Final results disagree with chunk evidence")
            for (key,) in db.execute(
                "SELECT source_id FROM results WHERE chunk_id=?", (chunk,)
            ):
                if key not in expected:
                    raise ValueError("Result points to unrelated chunk evidence")
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid chunk evidence") from error
