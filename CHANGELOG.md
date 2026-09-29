---
this_file: CHANGELOG.md
---
# Changelog

## Unreleased

### 2026-09-29: fallback original term and the localization book

- Glossary memory: a unit may carry `x-fallback`, the fallback original term
  (a plain English phrase such as *main stroke* for *stem*). `Term.fallback`
  and `Term.hint`: a translatable term with an empty target and a fallback is
  sent to the engine as `(translate the plain phrase: …)`; a term with a target
  is sent as before. Test in `tests/memory/test_glossary.py`; `docs/memories.md`
  documents the property.
- Documentation site: `src_docs/` (ProperDocs + MaterialX over MkDocs, tooling
  in `src_docs/tooling/python`, `src_docs/build.sh`) with a seven-part,
  seventy-chapter book on software localization under `src_docs/md/`, built
  into `docs/fl1992mk/`.

### 2026-09-28: review fixes

Fixes for the issue 145 code review. Each finding has a regression test.

- **L1** (critical). Memory language matching rejects a variant in another
  script (zh-Hans for zh_TW, sr-Latn for sr_Cyrl), any pt-BR/pt-PT cross, and
  any variant further than `tag_distance` 4 (es-ES for es_MX, en for en_GB).
  This now applies when the memory has only one variant of the language too.
  Otherwise `--memory-lang` is required. The source side stays lenient. Bare
  `pt` in a memory counts as Brazilian.
- **L2** (critical). `build-ui` tags its output with the catalog language (or
  `lang`), never the exclusion glossary's language. The glossary is loaded for
  that tag with the normal matching rules and only decides exclusions.
- **L3**. Upgrade takes the plural count from the target's Qt rule and uses
  FRESH's slot count only for languages Qt does not know. When a port would
  still drop reviewed forms, the APPROVED message is reserved, not consumed,
  so RETIRED keeps it whole.
- **L4**. An upgraded message counts as filled only when every `numerusform`
  and `lengthvariant` has text, so a plural with an empty form keeps exit 1.
- **L5**. `--relocated-finished` keeps APPROVED's own state. It no longer
  promotes an unfinished translation to finished.
- **L6**. `translate` derives its placeholder QA from the catalog format
  (`qa.formats.format_policy`). PO uses per-entry flags: `c-format` (printf
  through msgfmt), `python-brace-format` and `qt-format`. Unflagged PO entries
  get no placeholder check, following gettext. i18next uses `{{name}}`,
  Android uses printf for strings with a conversion, and XLIFF/TMX use the
  style detected per unit. TS keeps Qt. `TextPolicy` gains `unit_styles`, which
  serializes only as a digest, so TS cache identities are unchanged.
  `check_text` supports the `i18next` style.
- **L7**. `translate --nokeep-existing` (and `keep_existing=False`) is refused
  without an engine, or when the output is the input catalog.
- **L8**. `build-ui` excludes a source only when the term tier would really
  fill it: a plain message that `Glossary.whole_match` finds and whose term
  rendering passes the blocking QA. `&Kerning`, `Kerning %1` and plural
  messages stay in the project memory.
- **L9**. The legacy tag normaliser keeps script subtags (`sr-Latn`) and
  numeric regions (`es-419`), writes European Portuguese as `pt-PT`, and maps
  Apple `pt.lproj` and `Portuguese.lproj` to `pt-BR`. Two po2tmx goldens were
  updated because their inputs exercise this; the golden README records it.
- **L18**. Glossary term hits are written unfinished by default. The default
  `--finish-on` for `translate` and `upgrade` is now `id,context`.
- **L19**. A glossary TU with an unknown `x-status` such as `deprecated` is
  excluded instead of aborting the whole glossary load.
- **L20**. `build-ui` writes `x-numerus-form` for one-form plurals (zh, ja,
  ko), so such messages match their own reviewed translation.
- **L21**. `translate` exits 1 whenever the result is not ready, not only when
  units are pending.
- **L22**. The Qt numerus table knows Norwegian `no` (2 forms) and strips a
  Qt `@modifier` such as `sr@latin` before parsing.

### 2026-09-28: module consolidation

- Top-level modules moved into subpackages. The top level keeps only the
  shared model and primitives (`catalog`, `locales`, `json_values`,
  `json_sequence`, `xmlio`, `conversion`, `inventory`).
  - `qa/`: `qa` → `qa.text` (the package re-exports `TextPolicy`,
    `check_text`, `validate_batch`), `qa_<name>` → `qa.<name>`.
  - `translate/`: `abersetz_transport`, `openai_transport`, `provider_errors`,
    `frozen_contexts`; `translation_types|cache|store` → `types|cache|store`;
    `catalog_translation` → `catalog`, `catalog_translation_inputs|batches|types`
    → `inputs|batches|catalog_types`. The package exports resolve lazily.
  - `memory/`: `tmx` → `tmx_read`, `tmx_writer` → `tmx_write`,
    `tmx_names` → `names`.
  - `cli/`: `cli` → `cli/__init__`, `cli_args|translate|upgrade|tm` →
    `cli._args|translate|upgrade|tm`. The command tree is unchanged.
  - `extract/`: `source_extraction` → `extract.single`, plus the
    `*_resources` parsers and `legacy_pairs`.
  - `review/`: `review_<name>` → `review.<name>`; the built frontend moved from
    `review_web/` to `review/web/` (`review.server.WEB_ROOT`).
  - `corpus/`: `corpus` → `corpus.store`, `corpus_identity|schema` →
    `corpus.identity|schema`, plus importer, exporter, export lineage and
    selection, lineage validation, migrations, snapshots, source store and
    policy, unit writer.
  - `experimental/`: the research code (`classification*`, `distillation*`,
    `embeddings`, `embedding_search`, `embedding_store`, `clustering`,
    `retrieval`). It is not part of the supported CLI.
- **Deprecated aliases.** Every research module and every old path fl10n
  imports stays importable at its old name. The old name is the same module
  object as the new one and emits a `DeprecationWarning`. The research
  aliases exist for the live classification run's private driver scripts;
  delete them once that run is sealed. Delete the fl10n aliases once fl10n
  imports the new paths.
- `scripts/move_modules.py` performs the moves and import rewrites
  (idempotent, `--dry-run`, `--consumer DIR` for other repositories).
- `vexy_localizzy.corpus` is now a package; it re-exports `Corpus` lazily, so
  `from vexy_localizzy.corpus import Corpus` keeps working. Likewise
  `vexy_localizzy.qa` re-exports everything the old `qa.py` defined.
- `review.server.WEB_ROOT` names the shipped frontend. Code that built the path
  from `review_server.__file__` and `review_web` must use it instead.

### 2026-09-28: README and docs

- README rewritten as an outline (under 200 lines): layering, install extras,
  six commands with one example each, memories, guarantees, API pointers, docs
  index. Its examples are run by `tests/test_readme_examples.py`.
- New `docs/formats.md` (catalog adapters) and `docs/corpus.md` (voting corpus),
  holding the prose the README used to carry. Research prose moved into the
  classification, retrieval and distillation docs.
- New `docs/cli.md`, generated from `localizzy … --help` by
  `scripts/gen_cli_docs.py`; `tests/test_docs_cli.py` fails when it is stale.
- `docs/extraction.md` uses `localizzy tm extract` (formerly `localizzy
  extract`) and documents the legacy tree converters. `docs/memories.md` and
  `docs/upgrade.md` show the wired `localizzy translate` and `localizzy upgrade`.
- DEPENDENCIES: abersetz `>=1.1,<2` from a local editable path source until 1.1
  is on PyPI, the public single-attempt engine call, and the source of the Qt
  numerus table.

### 2026-09-28: TS upgrade

- Add `vexy_localizzy.upgrade`. `upgrade_ts(fresh, approved, ...)` ports
  APPROVED translations onto FRESH lupdate output. It returns NEW bytes,
  RETIRED bytes and an `UpgradeReport` (`localizzy-upgrade/1`).
  `upgrade(...)` writes the three files atomically, and only when both
  invariants hold.
- Ten tiers run as global passes: exact, shape_changed, plural_count_changed,
  memory id/context, relocated, fuzzy_exact_loose, fuzzy_similar, memory
  term/source, machine, pending/untranslated. Tier 9 reuses `translate_catalog`
  with batch-relevant glossary terms. `shape_changed` sends APPROVED's text as
  an example.
- NEW is FRESH's bytes with only changed messages spliced in through
  `ts_splice`. `upgrade_ts(X, X)` is byte-identical on both FontLab German
  catalogs.
- Element ownership: FRESH owns locations, source, comment and extracomment.
  APPROVED's whole `<translation>` is copied. translatorcomment, userdata and
  extra-* are carried when FRESH lacks them. oldsource and oldcomment are
  written for relocated and fuzzy ports.
- RETIRED resolves relative locations to absolute ones using Qt's reader rule.
  The result matches `lconvert -locations absolute` on 10,587 real messages.
- Add `cli_upgrade.upgrade`, ready for Fire but not yet wired into `cli.py`.
  Exit codes: 0 all filled, 1 empty messages remain, 2 usage, 3 missing
  translation extra.
- Docs: `docs/upgrade.md`. Tests: `tests/upgrade` (60 tests) with synthetic
  fixtures in `tests/fixtures/upgrade`.

### 2026-09-28: translate with memories

- Add `vexy_localizzy.translate` (`run`, `engine`, `context`). `translate_file`
  fills a catalog in this order: kept existing targets, direct-memory and
  glossary hits, then the engine. It writes the output catalog and a JSON
  report (`localizzy-translate/1`, default `OUT.localizzy.json`) with each
  message's origin, match class, memory TU ids, glossary terms and models.
- Memory precedence is `id` > `context` > `term` > `source`. Every hit passes a
  placeholder, markup and accelerator QA gate first. A failing hit gives a
  `MEMORY-QA-REJECT` finding and falls through to the next candidate or to the
  engine. A glossary term's first letter is capitalized when the UI label's is.
- A catalog already in the target language keeps its complete translations
  (`kept`); `de` matches a `de_DE` catalog. An existing target that fails QA or
  is only partly filled is left byte-for-byte unchanged, with a `KEPT-QA-FAIL`
  or `KEPT-INCOMPLETE` finding. Memory-only on the German FontLab catalog with
  keep-existing reproduces the input bytes exactly.
- `catalog_translation_types.Prefill` and the `memory`/`kept` dispositions are
  new. `translate_catalog(..., prefilled=...)` accepts prefilled units and
  `cache=None`, which calls no provider and leaves the rest pending. Existing
  callers are unaffected. `prepare_units` takes `prefilled` as a keyword.
- `translate.engine.open_cache` wires `abersetz_transport.translate_batch` into
  `TranslationCache` with ordered model fallbacks. `engine_identity` is
  `TRANSPORT_ID` plus the temperature.
- New Fire-ready `cli_translate.translate` and `cli_args.csv_paths`/`csv_strings`.
  Exit codes: 0 done, 1 pending units remain, 2 usage or configuration error,
  3 the `translation` extra is missing. `--provenance=extra` writes
  `<extra-localizzy-origin>` into TS messages; the default writes the sidecar only.

### 2026-09-28: legacy converters moved from fl10n

- Add `vexy_localizzy.extract`, ported from the fl10n `tools/` scripts. The
  ports cover `ts2tmx`, `po2tmx`, `lproj` (lproj2tmx), `adobe` (adobe2tmx),
  `oss` (oss2tmx) and `names.normalize_folder` (tmxnorm). They share
  `legacy_lang` (region shortening, filename guessing, XML-illegal character
  stripping), `walk.plan_jobs` and the `legacy_tmx.write_tmx` row writer. Each
  `main` became `run(...) -> dict` with its old parameters and defaults. Output
  goes through loguru and the returned dict, so `rich` is no longer used. Failed
  files still raise `SystemExit`.
- `oss2tmx` reads its app registry from the packaged `extract/oss_apps.toml`.
  `registry=` replaces it, `output` is required, and `Repo`/`App` are pydantic
  models. `norm` has no default folder.
- Add `cli_tm.TM_COMMANDS` for the `localizzy tm` group. It holds the six
  converters plus the strict `extract`, and imports each converter on first call.
- The TMX headers are unchanged. ts2tmx and oss2tmx still write
  `creationtool="po2tmx"` and `o-tmf="gettext"`, because they shared po2tmx's writer.
- Golden parity tests compare parsed records against outputs of the old scripts
  on synthetic inputs, in `tests/fixtures/legacy_golden`. The fl10n
  `test_legacy_*` suites were ported to `tests/extract/`.

### 2026-09-28: TS splice writer

- Add `formats/ts_splice.py`. `message_spans` tokenizes `<message>` elements as
  byte spans, skipping comments, CDATA, processing instructions and the DOCTYPE.
  `check_spans` parses every span and compares its exclusive C14N with the lxml
  message. Any disagreement raises `ValueError`; there is no silent fallback.
- `detect_style` records the declaration line, newline, indent unit, which empty
  tags are written expanded (`<location …></location>`), and whether text uses
  `&apos;`, `&quot;` or `&#32;` before a newline. `render_message` reproduces
  every unedited message of the four FontLab catalogs byte for byte.
- `ts.dump` on a retained document now re-renders only the edited messages and
  splices them into the original bytes. A `language` change rewrites only the
  `<TS>` start tag. New elements, such as an added `<translation>`, get their
  neighbours' indentation; existing whitespace is never re-laid-out. The
  unchanged-returns-raw path and the post-write `load_bytes` check remain.
- Appending one character to one translation in the 10,587-message German
  catalog now gives a 5-line `diff -U0`, down from 38,139 lines.
- No existing test pinned the old re-serialized bytes, so no assertion changed.
  Behaviour change: editing a retained TS document that is not in an
  ASCII-compatible encoding (for example UTF-16) now fails the span check
  instead of being re-serialized. Unchanged documents still write raw bytes
  without tokenizing.
- New whitespace goes only into layout containers: the message itself, and a
  `translation` or `numerusform` holding only `numerusform`/`lengthvariant`
  children. Text made of `<byte>` elements is never indented.

### 2026-09-28: memory loaders

- Add `vexy_localizzy.memory`. `select_language` maps catalog locales to a
  memory's TUV language (`de_DE`→`de`, `es_MX`→`es-419`) and refuses ties.
- `DirectMemory` does verbatim lookups (NFC, CRLF→LF only) with `id`, `context`
  and `source` match classes, native Qt plural shapes, first-file precedence and
  info findings (`MEMORY-CONFLICT`, `MEMORY-PLURAL-SHAPE`). `lookup_text` serves
  callers without a catalog unit.
- `Glossary` filters core terms by `x-status`, maps do-not-translate terms to
  themselves, selects prompt terms at word boundaries and returns them in a
  deterministic order.
- `tmx.Unit` and `tmx.Segment` now keep their direct `<note>` texts (additive).

- Accept a single JSON code block around a distillation vote, preserving raw
  cached responses and all strict selection, identity and byte-budget checks.

- Add paired keyed JSON extraction with typed paths, explicit locale selection,
  provenance and unmatched-key reporting, without application text filters.
- Share strict JSON string projection and path encoding; reject duplicate keys
  and invalid Unicode before returning extracted pairs.

- Add multilingual Apple `.loctable` extraction with explicit raw table selection,
  independent output language tags, compact provenance and unmatched-key reporting.
- Share ordered loctable reading without guessing locale aliases or Base fallback.

- Add shared Mozilla properties/DTD projections through moz.l10n 0.14.2 and
  paired extraction via `dtd` and explicit `mozilla-properties` formats.
- Preserve DTD references, omit commented declarations/includes, decode properties
  escapes and continuations, and reject unparsed input before returning pairs.

- Add Java-style properties extraction and paired `.properties` support in
  `localizzy extract`, using published javaproperties 0.8.2.
- Preserve escapes, surrogate pairs, continued lines, duplicate keys and trailing
  whitespace; reject malformed Unicode escapes before returning resource pairs.

- Add the installed `localizzy extract` command for TS/PO and explicitly paired
  Apple/Fluent resources, with provenance and unmatched-key reporting.
- Preserve regional locale tags; reject input/output aliases and invalid XML
  before atomic publication. Plural fallback requires actual projected variants.

- Add shared Fluent resource projections using the published syntax parser; retain
  ordered message/term/attribute keys and historical selector/whitespace behavior.
- Reject malformed Fluent entries and bound selector Cartesian expansion.

- Add shared Apple resource reading with the optional published OpenStep parser;
  preserve duplicate keys, quoted comment markers, Unicode and plural categories.
- Reject malformed text instead of silently returning partial or corrupted values.

- Add shared legacy Qt/gettext source projections, preserving ordered eligibility,
  context, fuzzy handling and the explicit first/last plural selection policy.

- Reuse accepted fallback votes when resuming incomplete model panels after
  provider recovery. Resolve complete cached panels before making new requests,
  including overlapping fallback routes with distinct model identities.
- Extend cached partial assignments when fallback routes overlap, avoiding
  replacement requests while another panel slot remains unavailable.

- Add optional numbered rich-text component QA within ICU branches: retain IDs,
  multiplicity, ancestry, argument ownership and labels through plural expansion.
- Reject malformed component syntax and tags assembled across ICU boundaries;
  keep sibling reordering and the default non-component ICU policy compatible.

- Add optional ICU MessageFormat structural QA using the published MessageFormat
  parser, locale plural rules, and a bounded Python batch/cache validator bridge.
- Preserve nested argument contracts through plural expansion and selector
  reordering; reject duplicate cases/offsets and altered protected formatting.

- Normalize proxy error envelopes returned with HTTP success into provider
  cooldowns and immediate fallback for classification and translation. Preserve
  retry headers, structured reset times, cached votes and actual model identities.

- Add explicit Qt review preparation that fills missing plural positions while
  retaining existing translations, length variants and source metadata.
- Display Qt underscore locales and absent/unrecognized locale values without
  crashing the browser reviewer or changing the underlying catalog language tags.

- Reject null, list and scalar provider response envelopes before translation
  parsing, allowing bounded retries and configured fallback instead of aborting.

- Check blank targets against length limits and support an explicitly configured
  abersetz sampling temperature, with validation before provider requests.

- Reject invalid custom transport result types before recording classification
  attempts, preserving bounded retries, provider fallback and cached votes.

- Add literal-token compatibility findings for consumer migrations, preserving
  diagnostic fields while checking repeated tokens and complete Qt arguments.

- Add sealed frozen-context archives and complete translation preflight for
  handoff between incompatible embedding and translation environments. Preserve
  canonical glossary order, exact serialized batches and external provenance.

- Reject non-text ModelResponse content before classification attempt logging,
  preventing malformed proxy responses from aborting provider fallback in SQLite.

- Add filtered batched cosine retrieval and frozen, locale-specific RAG context
  using existing weighted winners, exact source bindings and compact provenance.
- Preserve inline TMX references and keep full occurrence lists outside prompts;
  include ordered reference provenance in abersetz transport identity version 2.

- Reject missing messages and non-text provider content before translation parsing,
  so malformed HTTP-success responses follow bounded retries and provider fallback.

- Add the packaged FastAPI/React browser reviewer with published quiht previews,
  native target forms, QA, provenance suggestions, search/filter, keyboard actions,
  conflict-safe saves, draft/approval states and native TS downloads.
- Protect unsaved navigation and in-flight approval reasons; preserve drafts on
  failed/stale submissions. Add responsive fit/percentage preview scaling, RTL,
  native input text and Qt `notr` handling in isolated sanitized previews.
- Include synthetic workspace generation, browser build sources and bundled licenses.

- Honor Google RetryInfo quota reset durations in the shared classifier and
  translation transports, preserving multi-day cooldowns through fallback/resume.
- Ignore malformed and boolean timing hints; retain existing header/proxy precedence.

- Add filesystem review storage with strict edits, expected revisions, draft and
  approval states, native-form QA, per-catalog locks and intent/completion journals.
- Reconcile interrupted saves by old/new hashes without replay; reject external
  conflicts, truncated journals and catalog/sidecar aliases before acquiring locks.
- Sync journal and replacement directory entries before recording completion.

- Add complete catalog batch orchestration, stable native-form addressing,
  explicit reviewed/invariant handling and per-message coverage/provider evidence.
- Prepare new Qt target locales with explicit plural rules and source metadata
  preservation; reject unsupported XML even in plural positions being removed.
- Bound enriched batches without truncation and propagate per-message length
  limits into provider validation while preserving old unconstrained cache keys.

- Apply catalog content policy before caching provider results, allowing bounded
  retries and ordered fallback when a stricter policy rejects a candidate.
- Preserve caller validation and isolate cache selections by additional policy;
  reject inconsistent reviewed variant aliases before rebuilding approved output.

- Add shared Qt/brace/printf content QA, structural HTML and mnemonic checks,
  and complete native plural/length-variant traversal with explicit locale rules.
- Reject empty visible markup, implicit brace index mixing and skipped native
  printf checks; retain unchanged/source-defect findings for review.
- Document the shared cache validator and correct the adapter callback order.

- Reject blank and non-string reported model identities so malformed provider
  responses take the bounded fallback path instead of becoming cached votes.

- Add strict translation-batch contracts, published abersetz integration and
  actual provider identity capture with bounded single-attempt transport.
- Add durable translation caching, ordered fallback/cooldowns, required content
  validation on cache hits and fresh responses, and atomic winning selections.
- Reject duplicate response fields, blank model identities, invalid timeouts and
  mutation by transport/validation callbacks before caching accepted results.

- Add bounded public classification scheduling, immutable run identity, sealed
  batch checkpoints and atomic completion after full evidence replay. Resume
  missing votes through existing provider fallback/cache handling.
- Allow oversized batch entries as untruncated singletons when the complete
  request still fits its budget; preserve earlier batch/cache boundaries.
- Prevent concurrent run writers with filelock; verify preflight payload hashes
  before dispatch/commit so changed inputs cannot poison resumable checkpoints.

- Add complete-run A/B export with input/decision reconciliation, consensus and
  rare-language replay, distinct model evidence and a sealed decision digest.
- Hold checked decisions and corpus text in consistent read snapshots; reject
  incomplete runs, swapped evidence and changed input before replacing output.
  Legacy unbound completion markers require producer reconciliation.

- Export source-ID subsets with the existing weighted winners and original raw
  lineage. Require an optional corpus snapshot, retain all selected target locales,
  and record source IDs plus a compact selection fingerprint.
- Stage selected IDs/scores on disk, include only used origins/families, and
  preserve previous outputs on invalid input or interrupted extraction.
- Bind frozen source selections to an ID/text/inline-XML map digest as well as
  source-file identity, rejecting stale IDs after a corpus is rebuilt in a
  different import order. Include the digest in newly prepared classifier inputs.

- Add resumable distillation passes with complete input reconciliation, immutable
  predecessor links, bounded chunk carry and protected retained representatives.
- Retain oversized/singleton entries without truncation or paid requests; preserve
  completed chunks through provider outages and interruption. Record full chunk
  votes, policy overrides, source IDs, vectors and multilingual coverage.
- Initialize pass schemas atomically; reject corrupted predecessor inputs and
  missing chunk evidence. Recompute stored policy decisions and bind final
  results to their latest chunk before reuse or complete publication.

- Share durable response routing between classification and subset selection:
  preserve completed votes, skip exhausted providers until recovery and require
  distinct verified model identities before approving a reduction.
- Add strict numbered subset selection with majority equivalence, similarity and
  rare-language coverage checks. Changed rarity refreshes model context; changed
  similarity thresholds reuse cached votes and recompute deterministic decisions.
- Add bounded MiniBatchKMeans partitions with immutable SQLite output, explicit
  source IDs, centers, distances, input checksums and reproducibility metadata.

- Add optional resumable uubed embedding storage with source IDs, explicit model
  and prompt identity, float32 encoding and checksums. Reuse committed batches on
  restart and reject changed source text, invalid vectors or mismatched spaces.
- Add bounded-memory cosine retrieval with ranks independent of batch size,
  including identical-vector ties in partial final batches.

- Add atomic streaming TMX output for extracted literal records, preserving
  repeated provenance properties and leaving destinations intact on failures.
- Port optional legacy TMX filename planning with population-based shortening,
  script preservation, collision reporting and explicit consumer territory aliases.
  Alias substitution does not alter private-use or extension subtags.

- Expose checked in-memory catalog conversion for consumer adapters; retain full
  literal ICU sentences when exporting to TS and report parsed metadata loss.
- Include the Python typing marker and accept string paths for canonical JSON IO.

- Handle gateway reset times inside error envelopes, prefer valid retry headers
  over body hints, and ignore overflowing reset values without interrupting fallback.
- Verify HTTP quota fallback and cache reopening with both header and body-only
  recovery times, preserving distinct provider identities and completed votes.

- Add catalog-level TMX conversion with explicit language selection, complete
  multilingual document preservation and scoped target edits.
- Preserve catalog-only metadata, plurals and length variants in documented TMX
  properties, isolated by source/target pair; keep untranslated target declarations.
- Enforce source inline codes when filling empty targets and refuse content edits
  that would invalidate exact-origin corpus lineage.

- Add i18next v4 nested/array resources, native plural groups and interpolation
  retention, with typed key paths and byte-scoped translation edits.
- Add explicit `source_format` selection for application JSON in the API/CLI;
  preserve canonical JSON detection and require acknowledged cross-format losses.
- Reject duplicate JSON keys, invalid paths and unrepresentable fresh plural keys
  before replacing outputs; preserve original non-string values and number precision.

- Add Android string/plural/array preservation, exact JSON round trips and scoped
  translation edits with Android quoting, whitespace and protected placeholders.
- Preserve legal names shared across Android resource types; trim unquoted outer
  whitespace around transparent xliff:g placeholders without changing quoted spaces.
- Report monolingual conversion losses and fresh Android resource-name changes
  before replacing output files.

- Add fresh XLIFF 1.2 output and original-document preservation/editing for
  XLIFF 1.2/2.0/2.1/2.2, including multiple files, nested groups, positional or
  categorical plural groups, segments, inline codes and extension metadata.
- Preserve segmented-source/target ordering, enforce inline codes when filling
  empty targets, update explicit primary language labels on retargeting and
  reject unsupported state changes instead of silently downgrading them.

- Add PO/JSON byte-preserving round trips and scoped gettext edits through polib,
  retaining plural source text, indexed forms, obsolete order and metadata.
- Add atomic TS/PO/JSON conversion and CLI dispatch with explicit field-loss
  acknowledgement, including changed gettext plural rules.
- Require plural form counts to match declared rules before writing new output;
  keep incomplete retained inputs visibly untranslated and source-locale edits
  explicit in the PO header. Preserve interleaved contexts in fresh TS output.

- Preserve original Qt TS documents through versioned canonical JSON and scoped
  translation edits, including positional plurals, length variants and byte nodes.
  Reject unsupported metadata/shape changes before replacing outputs.
- Add attributed catalog compatibility types and keep internal DTD declarations
  during edits; retain exact bytes on unchanged round trips.
- Add ordered provider fallbacks, persistent cooldowns, distinct model assignment
  and reproducible actual-model identities. Migrate existing response caches
  without changing saved votes; preserve pending work when alternatives fail.
- Add optional OpenAI-compatible transport that honors provider retry timing
  without SDK retry waits, plus HTTP failure and cache-resume tests.
- Preserve provider-reported model identities separately from routed labels;
  prevent aliases from supplying duplicate votes and make concurrent callers
  return the same durable fallback selection. Historical reported IDs stay unknown.

- Add strict bounded numbered classification, three-model consensus and useful
  rare-language protection, with durable model-response caching and retry evidence.
- Add atomic classification input/coverage snapshots and documented canonical
  aliases for legacy Serbian Ijekavian and Meitei Mayek locale labels; preserve
  raw locale spellings and source bytes.

- Add per-unit family mappings and duplicate alias provenance; enforce active
  policies consistently after revisions.
- Add schema-v2 origin lineage and transactional migration of snapshot-aware v1
  corpora; reject older schemas with explicit recovery guidance.
- Preserve inline XML through atomic TMX export and reimport, retaining original
  source votes, compact links and decision metadata.
- Verify imported references against original TU content and retain local copies
  of referenced snapshots. Refuse export paths overlapping database files.

- Add streaming TMX/TS inventory with SHA-256 identities, explicit partial counts
  and atomic JSONL manifests.
- Add TMX records preserving language spelling, inline XML and source ordinals.
- Add SQLite candidates and deterministic weighted source-family votes.
- Preserve compressed content-addressed source snapshots so raw provenance
  survives input replacement; retain resumable commits only for valid identities.
- Add original synthetic tests and a runnable source-voting example.
