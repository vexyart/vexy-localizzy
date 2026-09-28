# this_file: tests/test_clustering.py
"""Bounded clustering covers every source exactly once and publishes atomically."""

import json
import sqlite3

import numpy as np
import pytest

from vexy_localizzy.experimental.clustering import cluster_embeddings
from vexy_localizzy.experimental.embeddings import EmbeddingCache


class Engine:
    space = "synthetic-cluster-space"
    cache_identity = "synthetic-output-settings"
    dimensions = 2

    def embed(self, texts):
        return np.array(
            [[1, 0] if text == "A" else [-1, 0] for text in texts], dtype=np.float32
        )


def read(path):
    with sqlite3.connect(path) as db:
        return (
            json.loads(db.execute("SELECT value FROM metadata").fetchone()[0]),
            db.execute("SELECT * FROM members ORDER BY source_id").fetchall(),
            db.execute("SELECT * FROM centers ORDER BY cluster_id").fetchall(),
        )


def test_clusters_when_two_directions_then_complete_deterministic_membership(tmp_path):
    with EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache:
        cache.embed([(index, "A" if index % 2 else "B") for index in range(1, 32)])
        first, second = tmp_path / "one.sqlite", tmp_path / "two.sqlite"
        result = cluster_embeddings(
            cache, first, expected_count=31, n_clusters=2, batch_size=4, epochs=2
        )
        assert result["entries"] == 31 and result["populated_clusters"] == 2
        cluster_embeddings(
            cache, second, expected_count=31, n_clusters=2, batch_size=4, epochs=2
        )
        one, two = read(first), read(second)
        assert one == two, (
            "Same input and configuration must reproduce the artifact records"
        )
        assert [row[0] for row in one[1]] == list(range(1, 32))
        by_id = {row[0]: row[1] for row in one[1]}
        assert by_id[1] != by_id[2]
        assert all(by_id[index] == by_id[1 if index % 2 else 2] for index in by_id)
        assert one[0]["embedding_identity"] == json.loads(cache.identity)
        assert one[0]["batch_size"] == 4


def test_clusters_when_expected_count_wrong_then_no_artifact(tmp_path):
    with EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache:
        cache.embed([(1, "A")])
        with pytest.raises(ValueError, match="expected"):
            cluster_embeddings(cache, tmp_path / "out.sqlite", expected_count=2)
    assert not (tmp_path / "out.sqlite").exists()


def test_clusters_when_output_exists_then_preserve_without_training(
    tmp_path, monkeypatch
):
    path = tmp_path / "out.sqlite"
    path.write_bytes(b"existing")
    with EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache:
        cache.embed([(1, "A")])
        with pytest.raises(FileExistsError):
            cluster_embeddings(cache, path, expected_count=1)
    assert path.read_bytes() == b"existing"


def test_clusters_when_fit_fails_then_remove_partial_output(tmp_path, monkeypatch):
    from sklearn.cluster import MiniBatchKMeans

    def fail(*args, **kwargs):
        raise RuntimeError("fit interrupted")

    monkeypatch.setattr(MiniBatchKMeans, "partial_fit", fail)
    with EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache:
        cache.embed([(1, "A")])
        with pytest.raises(RuntimeError, match="fit interrupted"):
            cluster_embeddings(cache, tmp_path / "out.sqlite", expected_count=1)
        assert not cache.db.in_transaction
    assert sorted(p.name for p in tmp_path.iterdir()) == ["vectors.sqlite"]


def test_clusters_when_vectors_corrupt_then_refuse_publication(tmp_path):
    with EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache:
        cache.embed([(1, "A")])
        with cache.db:
            cache.db.execute("UPDATE embeddings SET checksum='bad'")
        with pytest.raises(ValueError, match="checksum"):
            cluster_embeddings(cache, tmp_path / "out.sqlite", expected_count=1)
    assert not (tmp_path / "out.sqlite").exists()


@pytest.mark.parametrize(
    "option,value",
    [
        ("batch_size", 0),
        ("epochs", 0),
        ("n_clusters", 0),
        ("n_clusters", 3),
        ("expected_count", 0),
        ("seed", -1),
    ],
)
def test_clusters_when_invalid_configuration_then_refuse(tmp_path, option, value):
    with EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache:
        cache.embed([(1, "A"), (2, "B")])
        options = dict(expected_count=2, n_clusters=1, batch_size=2)
        options[option] = value
        with pytest.raises(ValueError):
            cluster_embeddings(cache, tmp_path / "out.sqlite", **options)
    assert not (tmp_path / "out.sqlite").exists()


def test_clusters_when_identical_vectors_then_report_empty_centers_and_keep_all(
    tmp_path,
):
    with EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache:
        cache.embed([(index, "A") for index in range(1, 8)])
        result = cluster_embeddings(
            cache, tmp_path / "out.sqlite", expected_count=7, n_clusters=2, batch_size=3
        )
    assert result["entries"] == 7
    assert result["populated_clusters"] == 1
    assert len(read(tmp_path / "out.sqlite")[1]) == 7
