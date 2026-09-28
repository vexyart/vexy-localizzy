# this_file: tests/test_embeddings.py
"""Embedding cache resumes bounded work and forbids cross-space comparisons."""

import sqlite3

import numpy as np
import pytest

from vexy_localizzy.experimental.embeddings import EmbeddingCache


class Engine:
    space = "synthetic-space-revision-1"
    cache_identity = "synthetic-output-settings-1"
    dimensions = 2

    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(texts)
        return np.array(
            [{"A": [1, 0], "B": [0.8, 0.6], "C": [-1, 0]}[t] for t in texts],
            dtype=np.float32,
        )


def test_cache_when_reopened_then_reuse_vectors_and_preserve_source_order(tmp_path):
    engine = Engine()
    path = tmp_path / "vectors.sqlite"
    with EmbeddingCache(path, engine) as cache:
        assert cache.embed([(20, "B"), (10, "A")], batch_size=1) == 2
    with EmbeddingCache(path, engine) as cache:
        assert cache.embed([(10, "A"), (20, "B")]) == 0
        blocks = list(cache.vectors(batch_size=1))
        assert [ids for ids, _ in blocks] == [[10], [20]]
        matches = cache.search("A", limit=2)
        assert [entry_id for entry_id, _ in matches] == [10, 20]
        assert matches[0][1] == pytest.approx(1)
    assert engine.calls == [["B"], ["A"], ["A"]]


def test_cache_when_later_batch_fails_then_resume_completed_batch(tmp_path):
    engine = Engine()
    path = tmp_path / "vectors.sqlite"
    with EmbeddingCache(path, engine) as cache:
        with pytest.raises(KeyError):
            cache.embed([(1, "A"), (2, "bad")], batch_size=1)
    with EmbeddingCache(path, engine) as cache:
        assert cache.embed([(1, "A"), (2, "B")], batch_size=1) == 1
    assert engine.calls == [["A"], ["bad"], ["B"]]


@pytest.mark.parametrize(
    "field,value", [("space", "other"), ("cache_identity", "other"), ("dimensions", 3)]
)
def test_cache_when_engine_changes_then_refuse_reopen(tmp_path, field, value):
    engine = Engine()
    path = tmp_path / "vectors.sqlite"
    with EmbeddingCache(path, engine) as cache:
        cache.embed([(1, "A")])
    setattr(engine, field, value)
    with pytest.raises(ValueError, match="identity"):
        EmbeddingCache(path, engine)


def test_cache_when_source_id_changes_text_then_refuse_stale_vector(tmp_path):
    with EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache:
        cache.embed([(1, "A")])
        with pytest.raises(ValueError, match="source text"):
            cache.embed([(1, "B")])


@pytest.mark.parametrize(
    "bad", [[[float("nan"), 0]], [[0, 0]], [[2, 0]], [[1, 0, 0]], []]
)
def test_cache_when_engine_returns_invalid_vectors_then_commit_nothing(tmp_path, bad):
    engine = Engine()
    engine.embed = lambda _: np.array(bad)
    with EmbeddingCache(tmp_path / "vectors.sqlite", engine) as cache:
        with pytest.raises(ValueError, match="vector"):
            cache.embed([(1, "A")])
        assert list(cache.vectors()) == []


def test_cache_when_stored_vector_corrupted_then_detect_before_retrieval(tmp_path):
    path = tmp_path / "vectors.sqlite"
    with EmbeddingCache(path, Engine()) as cache:
        cache.embed([(1, "A")])
    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE embeddings SET vector=?", (np.array([0, 1], dtype="<f4").tobytes(),)
        )
    with EmbeddingCache(path, Engine()) as cache:
        with pytest.raises(ValueError, match="checksum"):
            cache.search("A")


def test_cache_when_engine_changes_during_inference_then_commit_nothing(tmp_path):
    engine = Engine()
    original = engine.embed

    def changing(texts):
        result = original(texts)
        engine.space = "changed"
        return result

    engine.embed = changing
    path = tmp_path / "vectors.sqlite"
    with EmbeddingCache(path, engine) as cache:
        with pytest.raises(ValueError, match="identity"):
            cache.embed([(1, "A")])
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] == 0


def test_cache_when_unknown_database_then_refuse_without_modification(tmp_path):
    path = tmp_path / "vectors.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE unrelated(value)")
    before = path.read_bytes()
    with pytest.raises(ValueError, match="schema"):
        EmbeddingCache(path, Engine())
    assert path.read_bytes() == before


def test_cache_when_empty_input_then_no_model_calls(tmp_path):
    engine = Engine()
    with EmbeddingCache(tmp_path / "vectors.sqlite", engine) as cache:
        assert cache.embed([]) == 0
        assert cache.search("A") == []
    assert engine.calls == []


@pytest.mark.parametrize("entries", [[(0, "A")], [(1, "")], [(1, "A"), (1, "B")]])
def test_cache_when_invalid_input_then_refuse_batch(tmp_path, entries):
    with EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache:
        with pytest.raises(ValueError):
            cache.embed(entries)
        assert list(cache.vectors()) == []


def test_cache_when_streaming_then_commit_before_consuming_next_batch(tmp_path):
    engine = Engine()

    def entries():
        yield (9, "A")
        assert engine.calls == [["A"]], "The input must not be eagerly collected"
        yield (3, "A")
        yield (5, "C")

    with EmbeddingCache(tmp_path / "vectors.sqlite", engine) as cache:
        assert cache.embed(entries(), batch_size=1) == 3
        assert cache.search("A", limit=1, batch_size=1) == [(3, 1.0)], (
            "Equal scores use ascending source IDs"
        )


@pytest.mark.parametrize("size", [0, -1, 1.5, True])
def test_cache_when_invalid_bound_then_refuse_before_consuming_input(tmp_path, size):
    with EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache:
        with pytest.raises(ValueError, match="positive integers"):
            cache.embed([], batch_size=size)
        with pytest.raises(ValueError, match="positive integers"):
            list(cache.vectors(batch_size=size))
        with pytest.raises(ValueError, match="positive integers"):
            cache.search("A", limit=size)


def test_search_when_last_batch_short_then_identical_vectors_keep_id_ties(tmp_path):
    rng = np.random.default_rng(4)
    for dimension in (3, 16, 64, 128):
        vector = rng.normal(size=dimension).astype(np.float32)
        vector /= np.linalg.norm(vector)
    engine = Engine()
    engine.dimensions = 128
    engine.embed = lambda texts: np.tile(vector, (len(texts), 1))
    with EmbeddingCache(tmp_path / "vectors.sqlite", engine) as cache:
        cache.embed([(index, "A") for index in range(1, 258)])
        results = [
            cache.search("A", limit=3, batch_size=size) for size in (1, 128, 256, 257)
        ]
    assert all(result == results[0] for result in results), (
        "Batch shape must not change ranks or scores"
    )
    assert [entry_id for entry_id, _ in results[0]] == [1, 2, 3]
