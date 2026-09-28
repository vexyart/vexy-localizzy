# this_file: src/vexy_localizzy/embedding_search.py
"""Exact bounded multi-query ranking over an optional source-ID selection."""

import heapq
import itertools
import sqlite3
from contextlib import closing, contextmanager

import numpy as np

from vexy_localizzy.embedding_store import decode


@contextmanager
def selection(db, source_ids):
    """Stage IDs before inference and restore the caller's transaction on exit."""
    db.execute("SAVEPOINT embedding_search")
    try:
        query = "SELECT e.* FROM embeddings e"
        if source_ids is not None:
            db.execute("CREATE TEMP TABLE embedding_search_ids(id INTEGER PRIMARY KEY)")
            for key in source_ids:
                if type(key) is not int or not 0 < key < 2**63:
                    raise ValueError(
                        "Selected source IDs must be positive SQLite integers"
                    )
                try:
                    db.execute("INSERT INTO embedding_search_ids VALUES (?)", (key,))
                except sqlite3.IntegrityError as error:
                    raise ValueError(f"Duplicate selected source ID {key}") from error
            missing = db.execute(
                "SELECT id FROM embedding_search_ids s WHERE NOT EXISTS "
                "(SELECT 1 FROM embeddings e WHERE e.source_id=s.id) LIMIT 1"
            ).fetchone()
            if missing:
                raise ValueError(f"Selected source {missing[0]} has no embedding")
            query += " JOIN embedding_search_ids s ON s.id=e.source_id"
        yield query + " ORDER BY e.source_id"
    finally:
        db.execute("ROLLBACK TO embedding_search")
        db.execute("RELEASE embedding_search")


def rank(cache, query_sql, queries, limit, batch_size):
    """Decode each vector once per query block; retain only bounded top-k heaps."""
    best = [[] for _ in queries]
    with closing(cache.db.execute(query_sql)) as cursor:
        while rows := cursor.fetchmany(batch_size):
            ids = np.array([row[0] for row in rows], dtype=np.int64)
            vectors = np.stack([decode(row, cache.dimensions) for row in rows]).astype(
                np.float64
            )
            for query, heap in zip(queries, best, strict=True):
                # Identical row-wise reductions preserve ties across batch shapes.
                scores = np.sum(vectors * query, axis=1)
                for index in np.lexsort((ids, -scores))[:limit]:
                    item = (float(scores[index]), -int(ids[index]))
                    if len(heap) < limit:
                        heapq.heappush(heap, item)
                    elif item > heap[0]:
                        heapq.heapreplace(heap, item)
    return [
        [(-key, score) for score, key in sorted(heap, reverse=True)] for heap in best
    ]


def search_many(cache, texts, *, source_ids, limit, batch_size, query_batch_size):
    """Share validated document scans across bounded batches of same-space queries."""
    for bound in (limit, batch_size, query_batch_size):
        if type(bound) is not int or bound < 1:
            raise ValueError("Batch sizes and result limits must be positive integers")
    if isinstance(texts, str):
        raise ValueError("Provide an iterable of query strings")
    cache._check_identity()
    stream, results = iter(texts), []
    with selection(cache.db, source_ids) as query_sql:
        with closing(cache.db.execute(query_sql)) as cursor:
            empty = cursor.fetchone() is None
        while batch := list(itertools.islice(stream, query_batch_size)):
            if any(not isinstance(text, str) or not text.strip() for text in batch):
                raise ValueError("Queries require nonempty text")
            queries = None if empty else cache._infer(batch).astype(np.float64)
            results.extend(
                [[] for _ in batch]
                if empty
                else rank(cache, query_sql, queries, limit, batch_size)
            )
    cache._check_identity()
    return results
