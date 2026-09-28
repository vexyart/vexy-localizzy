# this_file: src/vexy_localizzy/retrieval.py
"""Frozen corpus selections supply exact and semantic translation examples."""

import hashlib
import json
from contextlib import contextmanager

from vexy_localizzy.corpus import export_selection
from vexy_localizzy.corpus.exporter import manifest
from vexy_localizzy.corpus.identity import entry_map_sha256 as entry_map_digest
from vexy_localizzy.embedding_store import decode
from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.translate.catalog_types import PromptContext
from vexy_localizzy.translate.types import TranslationExample


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _bind_vectors(corpus, embeddings, locale):
    corpus.db.execute(
        """
        CREATE TABLE export_selection.targets AS
        SELECT w.entry_id,e.source,c.target,w.candidate_id,w.score,e.source_xml,c.target_xml
        FROM export_selection.winners w JOIN main.candidates c ON c.id=w.candidate_id
        JOIN main.entries e ON e.id=w.entry_id WHERE c.locale=?
    """,
        (locale,),
    )
    corpus.db.execute(
        "CREATE UNIQUE INDEX export_selection.target_id ON targets(entry_id)"
    )
    corpus.db.execute("CREATE INDEX export_selection.target_source ON targets(source)")
    digest = hashlib.sha256()
    for row in corpus.db.execute(
        "SELECT * FROM export_selection.targets ORDER BY entry_id"
    ):
        vector = embeddings.db.execute(
            "SELECT * FROM embeddings WHERE source_id=?", (row[0],)
        ).fetchone()
        if vector is None or vector[1] != row[1]:
            raise ValueError(f"Missing or changed embedding source {row[0]}")
        decode(vector, embeddings.dimensions)
        digest.update(_json([dict(row), vector[3]]).encode() + b"\n")
    return digest.hexdigest()


@contextmanager
def retrieval_memory(
    corpus, embeddings, *, entry_ids, target_lang, source_snapshot, entry_map_sha256
):
    """Keep winners, source bindings and vector space frozen for a translation run.

    Entry IDs must come from a selection tied to both supplied corpus fingerprints.
    Save memory.manifest and memory.references with outputs to resolve prompt links.
    Both connections remain owned by the caller and must be idle on entry.
    """
    locale = canonical_locale(target_lang)
    if corpus.db.in_transaction or embeddings.db.in_transaction:
        raise ValueError("Finish current transactions before opening retrieval memory")
    embeddings._check_identity()
    memory = None
    with export_selection.staging(corpus.db, corpus.path.parent):
        corpus.db.execute("BEGIN")
        embeddings.db.execute("BEGIN")
        try:
            if source_snapshot != export_selection.source_snapshot(corpus.db):
                raise ValueError("Corpus source snapshot changed")
            if entry_map_sha256 != entry_map_digest(corpus.db):
                raise ValueError("Corpus entry map changed")
            selected = export_selection.prepare(corpus.db, entry_ids)
            vector_digest = _bind_vectors(corpus, embeddings, locale)
            evidence = {
                **manifest(corpus.db, selected=True),
                "retrieval_version": 1,
                "source_snapshot": source_snapshot,
                "entry_map_sha256": entry_map_sha256,
                "selection": selected,
                "target_lang": locale,
                "embedding_identity": json.loads(embeddings.identity),
                "targets_and_vectors_sha256": vector_digest,
            }
            memory = RetrievalMemory(corpus, embeddings, evidence)
            yield memory
        finally:
            if memory is not None:
                memory.active = False
            embeddings.db.rollback()
            corpus.db.rollback()


class RetrievalMemory:
    """Use retrieval_memory to construct a scoped, fingerprinted prompt source."""

    def __init__(self, corpus, embeddings, evidence):
        self.corpus, self.embeddings = corpus, embeddings
        self._manifest = _json(evidence)
        self.identity = hashlib.sha256(self._manifest.encode()).hexdigest()
        self._references = {}
        self.active = True

    @property
    def manifest(self):
        return json.loads(self._manifest)

    @property
    def references(self):
        """Full occurrence lists for examples already requested, keyed by digest."""
        return {key: json.loads(value) for key, value in self._references.items()}

    def _example(self, key):
        row = self.corpus.db.execute(
            "SELECT * FROM export_selection.targets WHERE entry_id=?", (key,)
        ).fetchone()
        refs = self.corpus.db.execute(
            "SELECT DISTINCT l.origin_id,l.origin_ordinal,l.family_id FROM lineage l "
            "JOIN sources s ON s.id=l.source_id WHERE l.candidate_id=? "
            "AND s.active=1 AND s.status='complete' ORDER BY 1,2,3",
            (row["candidate_id"],),
        )
        refs = _json([list(ref) for ref in refs])
        refs_sha256 = hashlib.sha256(refs.encode()).hexdigest()
        self._references[refs_sha256] = refs
        provenance = {
            "memory": self.identity,
            "entry": key,
            "candidate": row["candidate_id"],
            "score": row["score"],
            "refs_sha256": refs_sha256,
        }
        return TranslationExample(
            source=row["source_xml"] or row["source"],
            target=row["target_xml"] or row["target"],
            provenance=_json(provenance),
        )

    def context(self, items, *, limit=5, style="", glossary=None):
        """Exact whole-source matches precede semantic neighbors; deduplicate examples.

        Locale matching is exact after canonicalization, with no implicit regional
        fallback. Private style/glossary text remains caller supplied and cache-bound.
        """
        if not self.active:
            raise ValueError("Retrieval memory is closed")
        texts = list(dict.fromkeys(item.source for item in items))
        ids = (
            row[0]
            for row in self.corpus.db.execute(
                "SELECT entry_id FROM export_selection.targets ORDER BY entry_id"
            )
        )
        matches = self.embeddings.search_many(texts, source_ids=ids, limit=limit)
        retained = {}
        for text, neighbors in zip(texts, matches, strict=True):
            exact = [
                row[0]
                for row in self.corpus.db.execute(
                    "SELECT entry_id FROM export_selection.targets WHERE source=? AND source_xml='' ORDER BY entry_id LIMIT ?",
                    (text, limit),
                )
            ]
            for key in list(dict.fromkeys([*exact, *(key for key, _ in neighbors)]))[
                :limit
            ]:
                if key not in retained:
                    retained[key] = self._example(key)
        return PromptContext(
            style=f"{style}\nReference memory snapshot: {self.identity}".strip(),
            glossary=dict(glossary or {}),
            examples=list(retained.values()),
        )
