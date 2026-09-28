# this_file: src/vexy_localizzy/embeddings.py
"""Bounded, resumable source embeddings through a published uubed Embedder.

The caller owns the model and closes it. A cache represents one immutable source
identity space; changed text or engine settings require a new cache. Completed
batches are reusable after interruption. No complete-corpus claim is stored here;
the caller must reconcile expected IDs before exporting downstream artifacts.
"""

import itertools
from collections.abc import Iterable, Iterator
from pathlib import Path

import numpy as np

from vexy_localizzy.embedding_search import search_many
from vexy_localizzy.embedding_store import (
    checksum,
    decode,
    identity,
    open_store,
    validate_vectors,
)


def _positive(value: int) -> None:
    if type(value) is not int or value < 1:
        raise ValueError("Batch sizes and result limits must be positive integers")


class EmbeddingCache:
    """One connection/caller; iterators must be consumed before closing the cache."""

    def __init__(self, path: str | Path, engine):
        self.engine, self.identity = engine, identity(engine)
        self.dimensions = engine.dimensions
        self.db = open_store(path, self.identity)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.db.close()

    def _check_identity(self) -> None:
        if identity(self.engine) != self.identity:
            raise ValueError("Embedding identity changed during this run")

    def _infer(self, texts: list[str]) -> np.ndarray:
        self._check_identity()
        values = self.engine.embed(texts)
        self._check_identity()
        return validate_vectors(values, len(texts), self.dimensions)

    def _batch(self, entries: list[tuple[int, str]]) -> int:
        unique = {}
        for source_id, text in entries:
            if (
                type(source_id) is not int
                or source_id < 1
                or not isinstance(text, str)
                or not text.strip()
            ):
                raise ValueError(
                    "Embedding entries require positive source IDs and nonempty text"
                )
            if source_id in unique and unique[source_id] != text:
                raise ValueError(f"Conflicting source text for ID {source_id}")
            unique[source_id] = text
        pending = []
        for source_id, text in unique.items():
            row = self.db.execute(
                "SELECT * FROM embeddings WHERE source_id=?", (source_id,)
            ).fetchone()
            if row is None:
                pending.append((source_id, text))
            elif row[1] != text:
                raise ValueError(
                    f"Changed source text for ID {source_id}; use a new cache"
                )
            else:
                decode(row, self.dimensions)
        if not pending:
            return 0
        values = self._infer([text for _, text in pending])
        with self.db:
            for (source_id, text), vector in zip(pending, values, strict=True):
                blob = vector.tobytes()
                self.db.execute(
                    "INSERT INTO embeddings VALUES (?,?,?,?)",
                    (source_id, text, blob, checksum(source_id, text, blob)),
                )
        return len(pending)

    def embed(
        self, entries: Iterable[tuple[int, str]], *, batch_size: int = 128
    ) -> int:
        """Cache missing IDs in bounded committed batches; return newly embedded count."""
        _positive(batch_size)
        self._check_identity()
        stream, added = iter(entries), 0
        while batch := list(itertools.islice(stream, batch_size)):
            added += self._batch(batch)
        return added

    def vectors(
        self, *, batch_size: int = 128
    ) -> Iterator[tuple[list[int], np.ndarray]]:
        """Stream verified vectors with explicit source IDs in ascending order."""
        _positive(batch_size)
        cursor = self.db.execute("SELECT * FROM embeddings ORDER BY source_id")
        try:
            while rows := cursor.fetchmany(batch_size):
                yield (
                    [row[0] for row in rows],
                    np.stack([decode(row, self.dimensions) for row in rows]),
                )
        finally:
            cursor.close()

    def search(
        self, text: str, *, limit: int = 5, batch_size: int = 256, source_ids=None
    ) -> list[tuple[int, float]]:
        """Exact cosine top-k with bounded memory and deterministic source-ID ties."""
        return self.search_many(
            [text], limit=limit, batch_size=batch_size, source_ids=source_ids
        )[0]

    def search_many(
        self, texts, *, limit=5, batch_size=256, query_batch_size=32, source_ids=None
    ) -> list[list[tuple[int, float]]]:
        """Filter before top-k; share vector decoding across bounded query batches.

        None searches all cached IDs; an empty selection searches none. Every
        selected ID must exist. The caller resolves locale/source-text bindings.
        """
        return search_many(
            self,
            texts,
            source_ids=source_ids,
            limit=limit,
            batch_size=batch_size,
            query_batch_size=query_batch_size,
        )
