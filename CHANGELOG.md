---
this_file: CHANGELOG.md
---
# Changelog

## Unreleased

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
