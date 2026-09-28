# this_file: src/vexy_localizzy/clustering.py
"""Bounded MiniBatchKMeans over a consistent snapshot of source embeddings."""

import hashlib
import json
import math
import os
import sqlite3
import tempfile
from contextlib import closing
from importlib.metadata import version
from pathlib import Path

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.utils.random import sample_without_replacement
from threadpoolctl import threadpool_limits

from vexy_localizzy.embedding_store import decode, identity

APPLICATION_ID = 0x4C5A434D


def _sample(cache, count: int, size: int, batch_size: int, seed: int):
    positions = set(
        sample_without_replacement(
            count, size, random_state=seed, method="reservoir_sampling"
        )
    )
    sample, digest, offset = [], hashlib.sha256(), 0
    with closing(
        cache.db.execute("SELECT * FROM embeddings ORDER BY source_id")
    ) as cursor:
        while rows := cursor.fetchmany(batch_size):
            for row in rows:
                vector = decode(row, cache.dimensions)
                digest.update(bytes.fromhex(row[3]))
                if offset in positions:
                    sample.append(vector)
                offset += 1
    if offset != count or len(sample) != size:
        raise ValueError("Embedding count changed during sampling")
    return np.stack(sample), digest.hexdigest()


def _fit(cache, sample, n_clusters: int, batch_size: int, epochs: int, seed: int):
    model = MiniBatchKMeans(
        n_clusters=n_clusters,
        batch_size=batch_size,
        random_state=seed,
        n_init=1,
        reassignment_ratio=0,
        compute_labels=False,
    )
    model.partial_fit(sample)
    for _ in range(epochs):
        for _, vectors in cache.vectors(batch_size=batch_size):
            model.partial_fit(vectors)
    return model


def _write(cache, output: Path, model, metadata: dict) -> dict:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output.parent, prefix=".clusters-", delete=False
        ) as file:
            temporary = Path(file.name)
        with closing(sqlite3.connect(temporary)) as db:
            db.execute(f"PRAGMA application_id={APPLICATION_ID}")
            db.execute("PRAGMA user_version=1")
            db.execute("CREATE TABLE metadata(value TEXT NOT NULL)")
            db.execute(
                "CREATE TABLE centers(cluster_id INTEGER PRIMARY KEY, vector BLOB NOT NULL)"
            )
            db.execute(
                "CREATE TABLE members(source_id INTEGER PRIMARY KEY, cluster_id INTEGER NOT NULL REFERENCES centers(cluster_id), distance REAL NOT NULL)"
            )
            centers = np.asarray(model.cluster_centers_, dtype="<f4")
            db.executemany(
                "INSERT INTO centers VALUES (?,?)",
                [(i, vector.tobytes()) for i, vector in enumerate(centers)],
            )
            count = 0
            for source_ids, vectors in cache.vectors(batch_size=metadata["batch_size"]):
                labels = model.predict(vectors)
                distances = np.linalg.norm(
                    vectors.astype(np.float64) - centers[labels].astype(np.float64),
                    axis=1,
                )
                db.executemany(
                    "INSERT INTO members VALUES (?,?,?)",
                    [
                        (source_id, int(label), float(distance))
                        for source_id, label, distance in zip(
                            source_ids, labels, distances, strict=True
                        )
                    ],
                )
                count += len(source_ids)
            if count != metadata["entries"]:
                raise ValueError(
                    "Cluster output does not match expected embedding count"
                )
            metadata["populated_clusters"] = db.execute(
                "SELECT COUNT(DISTINCT cluster_id) FROM members"
            ).fetchone()[0]
            db.execute(
                "CREATE INDEX members_cluster ON members(cluster_id, distance, source_id)"
            )
            db.execute(
                "INSERT INTO metadata VALUES (?)",
                (json.dumps(metadata, sort_keys=True),),
            )
            db.commit()
        # Same-filesystem publication refuses to overwrite an existing run.
        os.link(temporary, output)
        return metadata
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def cluster_embeddings(
    cache,
    output: str | Path,
    *,
    expected_count: int,
    n_clusters: int | None = None,
    batch_size: int = 1024,
    epochs: int = 2,
    seed: int = 0,
) -> dict:
    """Publish a reproducible cluster database; never allocate an all-pairs matrix.

    Memory is bounded by at most three batches for initialization, one training
    batch, and at most batch_size centers. Stable reproduction requires the same
    inputs, configuration and dependency versions, recorded in the output.
    expected_count describes the supplied cache, not completeness of a corpus.
    """
    if any(type(n) is not int or n < 1 for n in (expected_count, batch_size, epochs)):
        raise ValueError("Counts, batch size and epochs must be positive integers")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("Seed must be an unsigned 32-bit integer")
    n_clusters = (
        min(batch_size, math.ceil(math.sqrt(expected_count)))
        if n_clusters is None
        else n_clusters
    )
    if type(n_clusters) is not int or not 1 <= n_clusters <= min(
        expected_count, batch_size
    ):
        raise ValueError("Cluster count must fit the input and batch size")
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    if cache.db.in_transaction:
        raise ValueError("Finish the current embedding transaction before clustering")
    if identity(cache.engine) != cache.identity:
        raise ValueError("Embedding identity changed")
    cache.db.execute("BEGIN")
    try:
        count = cache.db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        if count != expected_count:
            raise ValueError("Embedding count does not match expected count")
        size = min(count, max(batch_size, 3 * n_clusters))
        sample, digest = _sample(cache, count, size, batch_size, seed)
        metadata = {
            "format": "localizzy-clusters-1",
            "entries": count,
            "input_sha256": digest,
            "embedding_identity": json.loads(cache.identity),
            "n_clusters": n_clusters,
            "batch_size": batch_size,
            "initial_sample_size": size,
            "epochs": epochs,
            "seed": seed,
            "metric": "euclidean",
            "center_encoding": "float32-le",
            "packages": {
                name: version(name)
                for name in ("numpy", "scikit-learn", "threadpoolctl")
            },
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with threadpool_limits(limits=1):
            model = _fit(cache, sample, n_clusters, batch_size, epochs, seed)
            if identity(cache.engine) != cache.identity:
                raise ValueError("Embedding identity changed during clustering")
            return _write(cache, output, model, metadata)
    finally:
        cache.db.rollback()
