# this_file: tests/test_retrieval_provenance.py
"""Reference examples preserve inline codes without expanding occurrence lists."""

import json

from test_retrieval import Engine, embed_all, options

from vexy_localizzy.corpus import Corpus
from vexy_localizzy.embeddings import EmbeddingCache
from vexy_localizzy.retrieval import retrieval_memory
from vexy_localizzy.translation_types import TranslationItem


def test_context_when_inline_codes_then_preserve_both_segment_structures(tmp_path):
    path = tmp_path / "inline.tmx"
    path.write_text(
        '<tmx><body><tu><tuv lang="en"><seg>Open<ph x="1"/></seg></tuv><tuv lang="pl"><seg>Otwórz<ph x="1"/></seg></tuv></tu></body></tmx>'
    )
    with (
        Corpus(tmp_path / "corpus.sqlite") as corpus,
        EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache,
    ):
        corpus.import_tmx(path, family="one", weight=4)
        ids = embed_all(corpus, cache)
        with retrieval_memory(
            corpus, cache, entry_ids=ids, target_lang="pl", **options(corpus)
        ) as memory:
            example = memory.context([TranslationItem(id="x", source="Open")]).examples[
                0
            ]
            assert (
                '<ph x="1"/>' in example.source and '<ph x="1"/>' in example.target
            ), "Never flatten TMX codes into plain examples"


def test_context_when_many_occurrences_then_compact_resolvable_provenance(tmp_path):
    path = tmp_path / "repeated.tmx"
    unit = '<tu><tuv lang="en"><seg>Open</seg></tuv><tuv lang="pl"><seg>Otwórz</seg></tuv></tu>'
    path.write_text("<tmx><body>" + unit * 5000 + "</body></tmx>")
    with (
        Corpus(tmp_path / "corpus.sqlite") as corpus,
        EmbeddingCache(tmp_path / "vectors.sqlite", Engine()) as cache,
    ):
        corpus.import_tmx(path, family="one", weight=4)
        ids = embed_all(corpus, cache)
        with retrieval_memory(
            corpus, cache, entry_ids=ids, target_lang="pl", **options(corpus)
        ) as memory:
            context = memory.context([TranslationItem(id="x", source="Open")], limit=1)
            assert len(context.model_dump_json().encode()) < 2000, (
                "Occurrence count must not exhaust prompt budget"
            )
            proof = json.loads(context.examples[0].provenance)
            assert len(memory.references[proof["refs_sha256"]]) == 5000, (
                "Resolve every original ordinal outside the prompt"
            )
