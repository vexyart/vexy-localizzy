# this_file: src/vexy_localizzy/distillation_run.py
"""Resumable immutable distillation passes over ordered, provenance-linked inputs.

One caller owns a pass at a time. Inputs are fully reconciled before model work;
only complete artifacts are published, using a no-overwrite same-filesystem link.
"""

import hashlib
import json
import math
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from vexy_localizzy.distillation_chunks import process_cluster
from vexy_localizzy.distillation_store import (
    APPLICATION_ID,
    ClusterEntry,
    encoded,
    ingest,
    load_item,
    open_pass,
    report,
    validate_representatives,
)
from vexy_localizzy.distillation_validation import validate_evidence, validate_inputs
from vexy_localizzy.locales import canonical_locale

__all__ = ["ClusterEntry", "retained_items", "run_pass"]


def _read_complete(path):
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        if (
            db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
            or db.execute("PRAGMA user_version").fetchone()[0] != 1
        ):
            raise ValueError("Unknown predecessor pass schema")
        row = db.execute("SELECT value FROM metadata WHERE key='report'").fetchone()
        if row is None or not json.loads(row[0])["complete"]:
            raise ValueError("Predecessor pass is incomplete")
        identity = json.loads(
            db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()[0]
        )
        validate_inputs(db, identity)
        validate_representatives(db)
        validate_evidence(db, identity)
        if json.loads(row[0]) != report(db, identity):
            raise ValueError("Predecessor pass accounting changed")
        return db
    except BaseException:
        db.close()
        raise


def retained_items(path):
    """Stream unchanged retained entries/vectors for a required subsequent pass."""
    with closing(_read_complete(Path(path).resolve())) as db:
        for row in db.execute(
            "SELECT e.* FROM entries e JOIN results r USING(source_id) WHERE r.action='keep' ORDER BY e.cluster_id,e.source_id"
        ):
            yield load_item(row)


def _predecessor(path, source_identity, embedding_identity):
    if path is None:
        return None, 1
    with closing(_read_complete(path)) as db:
        prior = json.loads(
            db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()[0]
        )
        if (
            prior["source_identity"] != source_identity
            or prior["embedding_identity"] != embedding_identity
        ):
            raise ValueError("Predecessor source/embedding identity differs")
        number = prior["pass_number"] + 1
        if number > 3:
            raise ValueError("At most three distillation passes are supported")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest(), number


def _reconcile_predecessor(db, predecessor):
    if predecessor is None:
        return
    db.execute("ATTACH DATABASE ? AS predecessor", (predecessor.as_uri() + "?mode=ro",))
    try:
        current = "SELECT source_id,data,vector FROM main.entries"
        prior = "SELECT e.source_id,e.data,e.vector FROM predecessor.entries e JOIN predecessor.results r USING(source_id) WHERE r.action='keep'"
        for first, second in ((current, prior), (prior, current)):
            if db.execute(
                f"SELECT 1 FROM ({first} EXCEPT {second}) LIMIT 1"
            ).fetchone():
                raise ValueError("Inputs differ from predecessor retained entries")
    finally:
        db.execute("DETACH DATABASE predecessor")


def run_pass(
    items,
    selector,
    output,
    *,
    expected_count,
    source_identity,
    embedding_identity,
    rare_locales,
    predecessor=None,
    threshold=0.90,
    max_entries=100,
    chunk_max_entries=None,
    carry=8,
):
    """Resume pending chunks or validate/reuse a completed pass without model calls.

    items must be ordered by (cluster_id, source_id), with each source exactly once.
    source_identity must identify the immutable corpus/provenance snapshot. A later
    pass must contain exactly its predecessor's retained source text/targets/vectors.
    """
    if type(expected_count) is not int or expected_count < 1:
        raise ValueError("Expected count must be positive")
    if (
        type(max_entries) is not int
        or not 1 <= max_entries <= 100
        or type(carry) is not int
        or not 0 <= carry < max_entries
    ):
        raise ValueError("Invalid chunk/carry limits")
    if chunk_max_entries is None:
        chunk_max_entries = max_entries
    if (
        type(chunk_max_entries) is not int
        or not 1 <= chunk_max_entries <= max_entries
        or chunk_max_entries <= carry
    ):
        raise ValueError("Invalid processing chunk limit")
    if (
        not math.isfinite(threshold)
        or not 0 <= threshold <= 1
        or any(canonical_locale(locale) != locale for locale in rare_locales)
    ):
        raise ValueError("Invalid similarity/locale policy")
    if (
        not isinstance(source_identity, dict)
        or not source_identity
        or not isinstance(embedding_identity, dict)
    ):
        raise ValueError("Source and embedding identities are required")
    dimensions = embedding_identity.get("dimensions")
    if type(dimensions) is not int or dimensions < 1:
        raise ValueError("Embedding identity requires positive dimensions")
    output = Path(output).resolve()
    predecessor = Path(predecessor).resolve() if predecessor is not None else None
    if output == predecessor:
        raise ValueError("Output cannot replace its predecessor")
    prior_hash, pass_number = _predecessor(
        predecessor, source_identity, embedding_identity
    )
    panel = selector.panel
    identity = json.loads(
        encoded(
            {
                "format": "localizzy-distillation-pass-1",
                "expected_count": expected_count,
                "source_identity": source_identity,
                "embedding_identity": embedding_identity,
                "predecessor_sha256": prior_hash,
                "pass_number": pass_number,
                "rare_locales": sorted(rare_locales),
                "threshold": threshold,
                "max_entries": max_entries,
                "carry": carry,
                "models": panel.models,
                "chains": panel.chains,
                "model_identities": panel.model_identities,
                "prompt": panel.prompt,
                "endpoint": panel.endpoint_identity,
                "max_request_bytes": panel.max_request_bytes,
            }
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    completed = output.exists()
    pending = output.with_name("." + output.name + ".pending")
    path = output if completed else pending
    with closing(open_pass(path, identity, readonly=completed)) as db:
        ingest(db, items, expected_count, dimensions)
        _reconcile_predecessor(db, predecessor)
        validate_representatives(db)
        validate_evidence(db, identity)
        if completed:
            saved = db.execute(
                "SELECT value FROM metadata WHERE key='report'"
            ).fetchone()
            if (
                saved is None
                or json.loads(saved[0]) != report(db, identity)
                or not json.loads(saved[0])["complete"]
            ):
                raise ValueError("Invalid completed pass accounting")
            if pending.exists() and os.path.samefile(output, pending):
                pending.unlink()
            return json.loads(saved[0])
        cursor = db.execute(
            """SELECT DISTINCT e.cluster_id FROM entries e
            LEFT JOIN results r USING(source_id)
            WHERE r.source_id IS NULL ORDER BY e.cluster_id"""
        )
        for (cluster,) in cursor:
            process_cluster(
                db,
                cluster,
                selector,
                rare_locales=rare_locales,
                threshold=threshold,
                max_entries=chunk_max_entries,
                carry=carry,
                shrink_on_pending=chunk_max_entries < max_entries,
            )
        result = report(db, identity)
        if result["complete"]:
            validate_representatives(db)
            validate_evidence(db, identity)
            with db:
                db.execute(
                    "INSERT OR REPLACE INTO metadata VALUES ('report',?)",
                    (encoded(result),),
                )
    if result["complete"]:
        os.link(pending, output)
        pending.unlink()
    return result
