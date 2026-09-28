# this_file: tests/test_embedding_search.py
"""Filtered multi-query retrieval keeps locale eligibility ahead of top-k."""

import pytest
from test_embeddings import Engine

from vexy_localizzy.embeddings import EmbeddingCache


def test_search_when_subset_then_rank_only_eligible_sources_and_batch_queries(tmp_path):
    engine = Engine()
    with EmbeddingCache(tmp_path / "vectors.sqlite", engine) as cache:
        cache.embed([(1, "A"), (2, "B"), (3, "C")])
        engine.calls.clear()
        results = cache.search_many(
            ["A", "C", "B"], source_ids=[2, 3], limit=1, query_batch_size=2
        )
        assert [rows[0][0] for rows in results] == [2, 3, 2], "Filter before top-k"
        assert engine.calls == [["A", "C"], ["B"]], "Inference must be bounded"
        assert cache.search("A", source_ids=[3]) == [(3, -1.0)]


@pytest.mark.parametrize("subset", [[9], [1, 1], [True], [0], [2**63]])
def test_search_when_subset_invalid_then_no_inference_and_cleanup(tmp_path, subset):
    engine = Engine()
    with EmbeddingCache(tmp_path / "vectors.sqlite", engine) as cache:
        cache.embed([(1, "A")])
        engine.calls.clear()
        with pytest.raises(ValueError):
            cache.search_many(["A"], source_ids=subset)
        assert engine.calls == [], "Do not infer an invalid selection"
        assert cache.search("A", source_ids=[1]) == [(1, 1.0)]


def test_search_when_empty_subset_or_queries_then_no_inference(tmp_path):
    engine = Engine()
    with EmbeddingCache(tmp_path / "vectors.sqlite", engine) as cache:
        cache.embed([(1, "A")])
        engine.calls.clear()
        assert cache.search_many(["A", "B"], source_ids=[]) == [[], []]
        assert cache.search_many([]) == []
        assert engine.calls == []


def test_search_when_subset_generator_fails_then_keep_caller_transaction(tmp_path):
    def broken():
        yield 1
        raise RuntimeError("interrupted")

    with EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache:
        cache.embed([(1, "A")])
        cache.db.execute("BEGIN")
        with pytest.raises(RuntimeError, match="interrupted"):
            cache.search_many(["A"], source_ids=broken())
        assert cache.db.in_transaction, "Do not commit or roll back the caller"
        assert cache.search_many(["A"], source_ids=[1]) == [[(1, 1.0)]]
        cache.db.rollback()


@pytest.mark.parametrize("field", ["limit", "batch_size", "query_batch_size"])
def test_search_when_bound_invalid_then_reject(tmp_path, field):
    with EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache:
        with pytest.raises(ValueError, match="positive integers"):
            cache.search_many(["A"], **{field: 0})


def test_search_when_batches_change_then_results_equal_single_query_oracle(tmp_path):
    with EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache:
        cache.embed([(i, "ABC"[i % 3]) for i in range(1, 258)])
        expected = [cache.search(text, limit=7, batch_size=1) for text in "ACBA"]
        for size in (1, 128, 256, 257):
            assert (
                cache.search_many(
                    list("ACBA"), limit=7, batch_size=size, query_batch_size=2
                )
                == expected
            )
