---
this_file: docs/retrieval.md
---
# Retrieval for translation

`retrieval_memory` binds a selected set of source IDs to a frozen corpus and an
existing uubed embedding cache. It reuses the exporter's weighted winners and raw
source registry. It does not decide which entries should survive distillation.
Pass the retained IDs and fingerprints from that completed selection.

```python
from functools import partial
from vexy_localizzy.experimental.retrieval import retrieval_memory
from vexy_localizzy.translate.catalog import translate_catalog

# corpus, embeddings and translation_cache are caller-owned open objects.
with retrieval_memory(
    corpus, embeddings,
    entry_ids=retained_ids,
    target_lang=template.target_lang,
    source_snapshot=selection["source_snapshot"],
    entry_map_sha256=selection["entry_map_sha256"],
) as memory:
    result = translate_catalog(
        template, translation_cache,
        plural_forms=plural_forms,
        context=partial(memory.context, limit=3, style=private_style,
                        glossary=private_glossary),
    )
    evidence = {"manifest": memory.manifest, "references": memory.references}
    # Persist evidence alongside result in the consuming workspace.
```

Keep both connections idle on entry. The context owns read transactions and
temporary disk staging until exit; it neither closes the caller's connections
nor changes the corpus or vector records. A changed corpus source snapshot, entry
map, engine identity, missing vector, changed source text or corrupt vector fails
before the memory becomes usable. Keep this scope reasonably short; long-lived
SQLite readers can delay WAL checkpointing by concurrent writers.

Retrieval filters to the selected IDs **and exact canonical target locale before
top-k**. There is no implicit language/region fallback. Plain whole-source matches
precede cosine neighbors, with ascending source IDs resolving ties. Repeated
queries and retrieved examples are deduplicated within a prompt. Inline TMX
examples retain their complete `<seg>` XML; flattened text with inline codes
cannot displace a plain exact match. References are examples, not automatic
approval of terminology. Caller-supplied glossary entries remain explicit.

Each example carries the memory identity, source/candidate IDs, weight and a
SHA-256 reference key. `memory.references[key]` resolves its complete ordered
`[origin_id, original_ordinal, family_id]` list. The manifest resolves origin and
family IDs to source paths/hashes and weights. Store these outside the prompt:
thousands of original occurrences still require only one short reference key in
the model request. The manifest seals the source/entry-map/selection, target
locale, vector space and every eligible target/vector record. Even an empty
locale result contributes its memory identity to the context's style field.

The translation cache already hashes the complete context, including style,
glossary and reference digests. Use the current `abersetz_transport.TRANSPORT_ID`;
version 2 includes the ordered example provenance in the actual model prompt.
Changing a context or its source evidence cannot silently reuse an old request.

`EmbeddingCache.search_many(texts, source_ids=..., query_batch_size=32,
batch_size=256, limit=5)` exposes the generic exact search independently. It
validates the whole source selection before inference, shares vector decoding
across bounded query blocks, and restores existing caller transactions on failure.
`None` searches every cached source; an empty selection returns empty results
without inference. Missing or duplicate selected IDs are errors. Query vectors
must use the same embedding engine identity as document vectors.

This is exact scanning, not an approximate index. Memory use is bounded by query
and vector blocks plus the returned top-k results; runtime still scales with the
number of selected vectors and queries. Full-workload validation belongs to the
consumer, in addition to the synthetic ranking and provenance regression tests.

If a pinned embedding runtime and translation engine require incompatible
dependencies, use `prepare_contexts` in the embedding environment. It runs the
same eligibility and recursive batching rules as translation, records every
required context and seals the template, items, batch bytes and source evidence.
Do not upgrade the query embedder independently of its document vectors.

```python
from vexy_localizzy.translate.frozen_contexts import FrozenContexts, prepare_contexts

# Inside the retrieval_memory scope, before closing the embedding environment:
options = {"plural_forms": plural_forms, "batch_size": 50, "max_batch_bytes": 48000}
prepared = prepare_contexts(
    template,
    partial(memory.context, limit=3, style=private_style, glossary=private_glossary),
    evidence=lambda: {"manifest": memory.manifest, "references": memory.references},
    **options,
)
prepared.write("contexts.json")

# In the separate translation environment, with the identical template/options:
prepared = FrozenContexts.load("contexts.json")
result = translate_catalog(template, translation_cache, context=prepared, **options)
```

Save only a completely prepared archive. Loading rejects duplicate JSON keys and
checksum mismatches. Translation preflights the entire archive before making any
provider request, including later recursive splits. Changed sources, locale,
notes, plural descriptions, reviewed/invariant selections or batch limits require
preparing a new archive. Glossary order is canonicalized before sealing so the
actual serialized request bytes survive transfer. Returned contexts and evidence
are copies; callers cannot mutate subsequent requests through them.

The byte budget covers serialized translation batches. The adapter separately
checks its final request, which includes its instructions and serialization
overhead. Test complete requests against that transport limit. A single item that
cannot fit fails explicitly; source text and references are never truncated.

Implementation references: [NumPy stable multi-key sorting](https://numpy.org/doc/stable/reference/generated/numpy.lexsort.html)
and [SQLite savepoint semantics](https://www.sqlite.org/lang_savepoint.html).

## Embedding cache and clustering

The `embeddings` extra provides `experimental.embeddings.EmbeddingCache(path,
engine)` for a published `uubed.embeddings.Embedder`.
`embed([(source_id, text), ...])` consumes bounded batches and commits completed
vectors for reuse after an interruption. `vectors()` streams explicit IDs and
checksummed float32 vectors, and `search(text)` performs bounded-memory cosine
retrieval in the same model and prompt space. Changed source text or engine
identity requires a separate cache. Corpus completion is a separate expected-ID
reconciliation; a readable cache does not imply it. For CPU MiniLM inference,
install `sentence-transformers>=5.2,<6` and `transformers>=4.57.6,<5`, then use
`Embedder("minilm", device="cpu", precision="float32")`. The caller owns and
closes the engine.

The `clustering` extra provides `experimental.clustering.cluster_embeddings(cache,
output, expected_count=...)`. It streams bounded batches into MiniBatchKMeans and
publishes an immutable SQLite partition with source IDs, centres, distances and
the input identity. Cluster membership proposes candidates; it does not
authorize deleting entries.
