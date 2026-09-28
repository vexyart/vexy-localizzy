# this_file: tests/test_retrieval.py
"""RAG context preserves weighted winners, locale selection and raw provenance."""

import json

import numpy as np
import pytest
from test_selected_export import populated

from vexy_localizzy.corpus.export_selection import source_snapshot
from vexy_localizzy.corpus.identity import entry_map_sha256
from vexy_localizzy.experimental.embeddings import EmbeddingCache
from vexy_localizzy.experimental.retrieval import retrieval_memory
from vexy_localizzy.translate.types import TranslationItem


class Engine:
    space = "synthetic"
    cache_identity = "retrieval-test"
    dimensions = 2

    def embed(self, texts):
        return np.array(
            [[1, 0] if t == "Close" else [0, 1] for t in texts], dtype=np.float32
        )


def options(corpus):
    return dict(
        source_snapshot=source_snapshot(corpus.db),
        entry_map_sha256=entry_map_sha256(corpus.db),
    )


def embed_all(corpus, cache):
    entries = [tuple(row) for row in corpus.db.execute("SELECT id,source FROM entries")]
    cache.embed(entries)
    return [key for key, _ in entries]


def test_context_when_locale_sparse_then_filter_before_topk_and_keep_provenance(
    tmp_path,
):
    with (
        populated(tmp_path) as corpus,
        EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache,
    ):
        ids = embed_all(corpus, cache)
        with retrieval_memory(
            corpus, cache, entry_ids=ids, target_lang="pl", **options(corpus)
        ) as memory:
            context = memory.context(
                [TranslationItem(id="x", source="Close")], limit=1, style="Be concise."
            )
            assert [(e.source, e.target) for e in context.examples] == [
                ("Open", "Otwórz")
            ], "Best global neighbor has no Polish target"
            proof = json.loads(context.examples[0].provenance)
            assert proof["memory"] == memory.identity
            refs = memory.references[proof["refs_sha256"]]
            assert refs, "Carry original occurrence links"
            for origin, ordinal, family in refs:
                assert memory.manifest["origins"][str(origin)]["sha256"]
                assert memory.manifest["families"][str(family)]["weight"] == 4
                assert ordinal == 1
            assert "Be concise." in context.style and memory.identity in context.style


def test_context_when_exact_source_then_prioritize_weighted_winner_and_deduplicate(
    tmp_path,
):
    with (
        populated(tmp_path) as corpus,
        EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache,
    ):
        ids = embed_all(corpus, cache)
        with retrieval_memory(
            corpus, cache, entry_ids=ids, target_lang="de", **options(corpus)
        ) as memory:
            result = memory.context(
                [TranslationItem(id=str(i), source="Open") for i in range(2)], limit=1
            )
            assert [(e.source, e.target) for e in result.examples] == [
                ("Open", "Öffnen")
            ]
            assert json.loads(result.examples[0].provenance)["score"] == 7
            assert {r["name"] for r in memory.manifest["families"].values()} == {
                "one",
                "two",
                "three",
            }
        assert not corpus.db.in_transaction and not cache.db.in_transaction


@pytest.mark.parametrize(
    "mismatch", ["source_snapshot", "entry_map_sha256", "text", "missing"]
)
def test_context_when_binding_invalid_then_refuse_and_release_transactions(
    tmp_path, mismatch
):
    with (
        populated(tmp_path) as corpus,
        EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache,
    ):
        ids = embed_all(corpus, cache)
        kwargs = options(corpus)
        if mismatch in kwargs:
            kwargs[mismatch] = "0" * 64
        elif mismatch == "missing":
            with cache.db:
                cache.db.execute("DELETE FROM embeddings")
        else:
            with cache.db:
                cache.db.execute("UPDATE embeddings SET text='Changed'")
        with pytest.raises(ValueError):
            with retrieval_memory(
                corpus, cache, entry_ids=ids, target_lang="de", **kwargs
            ):
                pytest.fail("Invalid memory must not become usable")
        assert not corpus.db.in_transaction and not cache.db.in_transaction


def test_context_when_no_locale_then_empty_examples_but_snapshot_bound(tmp_path):
    with (
        populated(tmp_path) as corpus,
        EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache,
    ):
        ids = embed_all(corpus, cache)
        with retrieval_memory(
            corpus, cache, entry_ids=ids, target_lang="ar", **options(corpus)
        ) as memory:
            result = memory.context([TranslationItem(id="x", source="Open")])
            assert result.examples == [] and memory.identity in result.style


def test_context_when_selection_changes_then_identity_changes_and_old_manifest_immutable(
    tmp_path,
):
    with (
        populated(tmp_path) as corpus,
        EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache,
    ):
        ids = embed_all(corpus, cache)
        identities = []
        for selection in (ids, ids[:1]):
            with retrieval_memory(
                corpus, cache, entry_ids=selection, target_lang="de", **options(corpus)
            ) as memory:
                identities.append(memory.identity)
                manifest = memory.manifest
                manifest["origins"].clear()
                assert memory.manifest["origins"], "Expose a copy of frozen evidence"
        assert identities[0] != identities[1]
