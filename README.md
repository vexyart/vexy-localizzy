---
this_file: README.md
---
# Localizzy

Build translation memories whose entries can be traced to their sources.

Inventory XML translation memories, retain competing translations and select winners by weighted source votes.
Keep corpus data and application configuration in a separate private workspace.
Requires Python 3.12 or later. Development:

```sh
uv sync --group dev --extra llm
npm --prefix review ci
npm --prefix icu ci
./test.sh
uv run localizzy inventory /path/to/catalogs /private/work/manifest.jsonl
uv run python examples/quickstart.py
```
The inventory reports every `.tmx`/`.ts` XML file, including invalid inputs;
check the `invalid` count and per-file status before using its totals.

The Python API `Corpus.import_tmx(path, family=..., weight=...)` imports
bilingual/multilingual memories, preserving inline XML. `iter_winners()` streams selected
candidates; `provenance(candidate_id)` resolves their source links. Identical
content cannot receive extra votes under another family. Repeated occurrences
within a family contribute one weighted vote.
Database `memory.sqlite` keeps raw input snapshots in `memory.sources/`.
Keep that directory with the database: it preserves original text and metadata
after source paths change. Imports expose exclusions for missing English,
missing targets. Source snapshots retain their full original XML.
Mixed-product files can select families using `family_property` and an explicit
`family_map`. Duplicate-file aliases retain their paths but share a voting
policy. To change the policy of several aliases, deactivate those paths first
and reimport them consistently.

`export_tmx(path, entry_ids=ids)` atomically writes selected
winners; omit `entry_ids` for all winners. Outputs retain original-source links and
the original decision scores/tie flags.
`source_snapshot` and `entry_map_sha256` bind saved IDs to a frozen corpus.
Reimport verifies raw TU content, copies snapshots into the receiving corpus and
preserves original votes. Keep referenced snapshots available when transferring exports.
The database retains alternative candidates; a winner-only export records prior
conflicts in TU decision properties, while reimport computes ties among the
candidates actually imported.

`formats.ts.load()` retains original XML alongside editable catalog units.
`formats.json_io.dump()` saves versioned, self-contained JSON; an unchanged
TS→JSON→TS round trip restores exact bytes. Translation edits preserve message
IDs, locations, unknown metadata, byte escapes and positional plural/length
variants. Unsupported structural edits fail before replacing the output.
Qt finished state maps to `translated`; both `untranslated` and `needs_review`
write as unfinished. Keep canonical JSON when you need richer approval states.

`formats.po` preserves gettext context, comments, previous text, flags, obsolete
entries, encoding and positional plurals. Unchanged PO→JSON→PO restores exact
bytes. New plural output requires an explicit `plural_forms` rule matching every
active entry's indices. Incomplete retained plurals remain untranslated; unchanged
input bytes can still be archived. Source-locale edits update `X-Source-Language`.

```sh
uv run localizzy convert input.po json catalog.json
uv run localizzy convert catalog.json po restored.po
```

`conversion.convert()` supports TS, TMX, PO, XLIFF, Android, i18next and canonical JSON. It prepares and parses
output before replacing the destination, reporting changed or dropped fields.
Lossy conversions require `allow_loss=True` (CLI `--allow_loss=True`); changed
PO plural rules also require this acknowledgement. CLDR categories need an
explicit `plural_order` when converting to positional forms.
`conversion.convert_catalog()` applies the same checks to an in-memory catalog.
Complete ICU message strings remain literal strings when exported to TS; Qt does
not evaluate ICU syntax. The loss report records removal of parsed ICU metadata.

`formats.xliff` writes fresh XLIFF 1.2 and preserves existing 1.2, 2.0, 2.1 and
2.2 documents. It retains all file sections, groups, segments, inline codes,
original code data and extension metadata. Unchanged XLIFF→JSON→XLIFF restores
exact bytes. Inline content is exposed as XML fragments; translation edits must
retain code identities. XLIFF 2 ignorable content stays read-only. Unsupported
state changes fail explicitly: `vanished` has no retained XLIFF representation,
and XLIFF 2 does not represent this catalog model's `needs_review` state.
New XLIFF 1.2 plural groups retain explicit category/index identities; categories
are never assigned a guessed locale order.

`formats.android` preserves string resources, CLDR plurals, arrays, styling,
placeholder markup and unrelated XML. Unchanged Android→JSON→Android restores
exact bytes, including names shared by different resource types. Translation
edits use Android quoting and whitespace semantics; nontranslatable resources,
references and placeholder identities remain protected. Resource XML holds one
locale column: loading projects its values as source text (default `en`, explicitly
overridable); writing uses a supplied target or the source. Cross-format loss
reports cover bilingual metadata and required resource-name changes. Keep locale
selection in the calling application and directory layout.

`formats.i18next` retains nested objects, arrays, interpolation and v4 cardinal,
ordinal and context plural suffixes. Canonical keys use typed JSON paths:
`["menu","open"]` is nested, `["menu.open"]` is literal and `["choices",0]`
addresses an array element. A colliding scalar/plural base gets a `plural:` prefix.
Fresh output accepts these paths or a simple literal key. Retained edits replace
only selected string tokens; all other bytes, including non-string values, remain
unchanged. Locale and runtime separators/plugins stay in application configuration;
v4 grouping uses the default `_` separator and an existing `_other` member.
Legacy or custom suffixes remain literal keys. Null values remain in the original
document and are not converted into editable string units.

Application JSON must be selected explicitly:

```sh
uv run localizzy convert en.json json catalog.json --source_format=i18next
uv run localizzy convert catalog.json i18next restored.json
```

`formats.tmx` exposes an editable language-pair projection while retaining every
original TUV, property and provenance node. Source selection must be unambiguous;
several target languages require explicit selection before editing. For example:

```sh
uv run localizzy convert memory.tmx json catalog.json --source_lang=en --target_lang=fr
uv run localizzy convert catalog.json tmx restored.tmx
```

Unchanged round trips restore exact bytes. Existing and newly filled targets retain
inline codes; edits to exact-origin corpus exports require a separate revision and
are refused here. This document adapter loads the whole file; use `Corpus` and
`read_tmx` for streaming large memories.

Fresh TMX uses `x-localizzy-projection-v1` in the header (a JSON source/target pair)
and `x-localizzy-catalog-v1` per TU (`version: 1`, plus `projections` indexed by
JSON-encoded language pairs). Each projection stores catalog Unit fields except
`source`, `source_hash` and `record_id`; native segments remain authoritative and
must agree with the stored target. Plurals/length variants retain all values in
this property; the native target uses `other`, the first positional form, or the
first length variant. Other TMX tools can ignore these properties and see only
that representative value. Canonical JSON remains the portable full catalog.

`CachedClassifier` accepts ordered `fallbacks` per preferred model.
Provider outages persist a cooldown, honoring `Retry-After` without blocking
other providers. Retry headers take precedence over gateway `reset_seconds`
body hints and Google `RetryInfo.retryDelay`, including error envelopes;
HTTP-success responses carrying a nonempty `error` object or string also enter
cooldown and fallback, for both classification and translation.
Malformed timing falls back to a bounded
default cooldown. `classify_detailed()` returns routed labels and provider-reported
model identities alongside votes; aliases reporting the same backend cannot
supply separate votes. Legacy responses retain unknown reported identities;
an explicit `model_identities` map can resolve known aliases. A completed fallback
choice is cached for that input and policy, consistently across concurrent callers;
pending panels extend cached assignments, including fallbacks, before new requests. New
batches reconsider the preferred model after recovery. Successful votes survive
exhausted alternatives, with `ClassificationPending` identifying unfinished work.
Applications choose their fallback models explicitly.

Install the `llm` extra to use `openai_transport.chat_request` with an
OpenAI-compatible endpoint. Other transports can raise `ProviderUnavailable`
with their retry delay and return `ModelResponse` to retain reported identities.
Plain string transports remain supported with unverified reported identity.
Cache keys include endpoint, routed model, rubric, input and locale coverage; selection keys also include policy.

See [classification to A/B export](docs/classification.md) and the [browser reviewer](docs/review.md). Consumer migrations and full-data processing remain in development.
Complete ICU strings have an optional [Node structural checker](icu/README.md)
and Python cache-validation bridge, separate from brace-format checks.

For newly extracted literal text, `tmx_writer.write_records()` streams
`TMXRecord` objects into an atomic TMX output. It preserves ordered, repeated
properties and every supplied language variant; callers supply provenance and
selection rules. A failed extraction or invalid XML value leaves existing output
intact. Use the document adapter above for retained inline XML and catalog metadata.

Install the `sources` extra for `tmx_names.plan_folder()` and its legacy filename
policy: lowercase tags, explicit Chinese scripts and population-based territory
shortening. It only proposes names and reports collisions; it never renames files.
Territory shortening is a filename convention, not a declaration that regional
translations are interchangeable. Historical territory aliases are caller supplied.

The `embeddings` extra provides `embeddings.EmbeddingCache(path, engine)` for a
published `uubed.embeddings.Embedder`. `embed([(source_id, text), ...])` consumes
bounded batches and commits completed vectors for reuse after interruption.
`vectors()` streams explicit IDs and checksummed float32 vectors; `search(text)`
performs bounded-memory cosine retrieval in the same model/prompt space. Changed
source text or engine identity requires a separate cache. Corpus completion is a
separate expected-ID reconciliation, not implied by the cache being readable.
For CPU MiniLM inference, install `sentence-transformers>=5.2,<6` and
`transformers>=4.57.6,<5`, then use `Embedder("minilm", device="cpu",
precision="float32")`. The caller owns and closes the engine. Full-corpus
embedding and complete distillation passes remain pending; [RAG retrieval](docs/retrieval.md) is available.

The `clustering` extra provides `clustering.cluster_embeddings(cache, output,
expected_count=...)`. It streams bounded batches into MiniBatchKMeans and publishes
an immutable SQLite partition with source IDs, centers, distances and input identity.
Cluster membership proposes candidates; it does not authorize deleting entries.

`distillation_cache.CachedSelector` uses the same durable provider fallbacks as
classification. `select(entries, vectors, rare_locales=...)` requires three verified
model identities; two must name the same equivalent retained entry before it can
be dropped. Similarity and rare-language coverage provide additional checks.
Completed responses survive outages; `DistillationPending` leaves work resumable.
Changed rarity invalidates responses; changed similarity thresholds reuse votes
and recompute the decision. Full corpus passes and exports remain in development.
See [distillation passes](docs/distillation.md), [translation batches and caching](docs/translation.md) and [source projections](docs/legacy-sources.md); use the [extraction command](docs/extraction.md) to create TMX pairs.
