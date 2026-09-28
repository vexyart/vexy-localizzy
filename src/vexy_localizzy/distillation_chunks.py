# this_file: src/vexy_localizzy/distillation_chunks.py
"""Bounded cluster chunks with durable representative protection."""

import numpy as np

from vexy_localizzy.distillation_cache import DistillationPending
from vexy_localizzy.distillation_store import load_item, save_chunk


def _fits(selector, items, rare_locales):
    return (
        selector.request_size([item.entry for item in items], rare_locales=rare_locales)
        <= selector.panel.max_request_bytes
    )


def _retained(item, reason):
    return {
        "kept": [item.entry.id],
        "dropped": [],
        "overrides": [{"source_id": item.entry.id, "reason": reason}],
        "votes": {},
    }


def _protect(db, decision, items):
    protected = {
        item.entry.id
        for item in items
        if db.execute(
            "SELECT 1 FROM results WHERE representative_id=? LIMIT 1", (item.entry.id,)
        ).fetchone()
    }
    overrides = [
        {"source_id": row["source_id"], "reason": "protected_representative"}
        for row in decision["dropped"]
        if row["source_id"] in protected
    ]
    dropped = [row for row in decision["dropped"] if row["source_id"] not in protected]
    removed = {row["source_id"] for row in dropped}
    result = {
        **decision,
        "dropped": dropped,
        "kept": [item.entry.id for item in items if item.entry.id not in removed],
        "overrides": decision["overrides"] + overrides,
    }
    if "coverage_after" in result:
        coverage = {}
        for item in items:
            if item.entry.id not in removed:
                for locale in item.entry.targets:
                    coverage[locale] = coverage.get(locale, 0) + 1
        result["coverage_after"] = coverage
    return result


def process_cluster(
    db,
    cluster,
    selector,
    *,
    rare_locales,
    threshold,
    max_entries,
    carry,
    shrink_on_pending=False,
):
    """Stop a pending cluster, leaving other clusters available to the caller."""
    while rows := db.execute(
        "SELECT e.* FROM entries e LEFT JOIN results r USING(source_id) WHERE e.cluster_id=? AND r.source_id IS NULL ORDER BY e.source_id LIMIT ?",
        (cluster, max_entries),
    ).fetchall():
        fresh = [load_item(row) for row in rows]
        if not _fits(selector, fresh[:1], rare_locales):
            save_chunk(db, cluster, fresh[:1], _retained(fresh[0], "oversized_entry"))
            continue
        carried = [
            load_item(row)
            for row in db.execute(
                "SELECT e.* FROM entries e JOIN results r USING(source_id) WHERE e.cluster_id=? AND r.action='keep' ORDER BY e.source_id LIMIT ?",
                (cluster, carry),
            )
        ]
        batch = fresh[:1]
        for item in carried:
            if len(batch) < max_entries and _fits(
                selector, [item, *batch], rare_locales
            ):
                batch.insert(len(batch) - 1, item)
        for item in fresh[1:]:
            if len(batch) >= max_entries or not _fits(
                selector, [*batch, item], rare_locales
            ):
                break
            batch.append(item)
        if len(batch) == 1:
            save_chunk(db, cluster, batch, _retained(batch[0], "singleton_chunk"))
            continue
        try:
            decision = selector.select(
                [item.entry for item in batch],
                np.stack([item.vector for item in batch]),
                rare_locales=rare_locales,
                threshold=threshold,
            )
        except DistillationPending:
            if shrink_on_pending and len(batch) > 1:
                # A provider can accept the request size yet fail to produce a
                # parseable panel for a particular mixture of entries. Split
                # only this cluster and retry; completed clusters stay intact.
                max_entries = max(1, len(batch) // 2)
                continue
            with db:
                db.execute(
                    "INSERT INTO pending VALUES (?,?) ON CONFLICT(cluster_id) DO UPDATE SET error=excluded.error",
                    (cluster, "model_selections_pending"),
                )
            return
        save_chunk(db, cluster, batch, _protect(db, decision, batch))
    with db:
        db.execute("DELETE FROM pending WHERE cluster_id=?", (cluster,))
