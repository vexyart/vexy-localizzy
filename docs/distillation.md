---
this_file: docs/distillation.md
---
# Resumable distillation passes

Install the `embeddings` extra and use `CachedSelector` with a configured transport
and fallback policy. The optional `llm` extra supplies the OpenAI-compatible
transport; `clustering` supplies bounded partition generation.

`run_pass(items, selector, output, expected_count=..., source_identity=...,
embedding_identity=..., rare_locales=...)` consumes `ClusterEntry(cluster_id,
entry, vector)` values ordered by `(cluster_id, entry.id)`. Every source ID must
occur exactly once. Entries are strict `DistillationEntry` records; vectors must
be normalized and belong to the stated embedding space. Supply the embedding
cache's complete identity, including `dimensions`, and an immutable corpus
snapshot/provenance identity. Source IDs resolve back through that snapshot.

All inputs are stored and checked before paid requests. The SQLite artifact
retains source text, all supplied target translations, original criticality and
quality, vectors, checksums, cluster membership and each chunk's full decision.
Requested, routed and reported models remain attached to model decisions.

Selection responses may be raw JSON or exactly one enclosing code block with
an empty or `json` language label. Surrounding prose, extra blocks and other
labels are rejected. The complete raw response still counts toward the 32,000-byte
limit and stays unchanged in the cache. Duplicate fields, unknown IDs, missing
entries and invalid equivalence claims remain errors after removing the wrapper.

The default chunk limit is 100 entries, with at most eight retained candidates
carried into the next chunk. Exact serialized UTF-8 size must fit the selector's
request budget. Entries too large to fit alone remain unchanged with an
`oversized_entry` reason. A one-entry chunk is retained without a model request.

A later chunk cannot remove an entry already serving as an accepted replacement.
The override is recorded as `protected_representative`; requested model votes
remain available. This avoids unsupported chains of purported equivalence and
keeps each dropped entry linked directly to a retained entry in its cluster.
The bounded carry policy does not claim exhaustive nearest-neighbor comparisons.

Only a complete pass is published at `output`. Incomplete work stays in the
sibling `.<output-name>.pending` SQLite file. Call the same function with the
same inputs and policy to resume. Completed chunks and responses are reused;
unavailable clusters stay pending while other clusters are considered. The result
reports completion, counts and locale coverage before/after. For an incomplete
pass, after-coverage describes only decisions completed so far.

One caller owns a pass at a time. Keep its response cache alongside the pending
artifact. Changed input text, vectors, policy or provenance requires a new path;
unknown or inconsistent existing artifacts are rejected. A completed artifact is
read-only to the runner and is rechecked before reuse.

Run a second pass even when the first is unchanged:

```python
second = run_pass(
    retained_items(first_path), selector, second_path,
    expected_count=first_report["kept"],
    source_identity=source_identity,
    embedding_identity=embedding_identity,
    rare_locales=rare_locales,
    predecessor=first_path,
)
```

The next pass must contain exactly its predecessor's retained text, translations
and vectors; cluster assignments may change if those retained entries are
reclustered. The predecessor's file checksum is recorded. A third pass is allowed.
Final TMX export and full-corpus acceptance are separate gates; a bounded sample
pass is not evidence that a whole corpus has been distilled.

Use `Corpus.export_tmx(path, entry_ids=retained_ids, source_snapshot=...,
entry_map_sha256=...)` for the retained source set. Pass both fingerprints from
classification input preparation, not the pass-file hash. The entry-map digest
binds numeric IDs to source text and inline XML; importing identical files in a
different order can otherwise change those IDs. A changed corpus, unknown/inactive source or
duplicate ID fails without replacing the output. An empty iterable exports an
empty memory. The return value counts bilingual target units, not source IDs.

The header records both corpus fingerprints, selected source count and SHA-256 of
sorted decimal IDs separated by newlines. Each unit records its source ID plus
the usual winning candidate, weights and original lineage. The origin registry
includes only origins/families used by selected winners. Selection staging uses a
separate disk file and is discarded after success or failure.

## Selector panel

`experimental.distillation_cache.CachedSelector` uses the same durable provider
fallbacks as classification. `select(entries, vectors, rare_locales=...)`
requires three verified model identities; two must name the same equivalent
retained entry before an entry can be dropped. Similarity and rare-language
coverage are additional checks. Completed responses survive outages, and
`DistillationPending` leaves the work resumable. Changed rarity invalidates the
responses; changed similarity thresholds reuse the votes and recompute the
decision. Full corpus passes and exports are still in development.
