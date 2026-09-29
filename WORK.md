---
this_file: WORK.md
---
# Work

## 2026-09-30: German UI review preferences

Integrated the supplied German catalog diff: 547 translation changes after
excluding XML and location churn. German guidance now covers compact hinzu,
the synchron family and Synchronsprecher, weight/thickness/stem distinctions,
readable tool/window compounds, contextual omissions and separator wordplay.
Regenerated German terminology outputs with existing review statuses intact.
Apparent typos and partial plural edits remain evidence, not general rules.
The writing guide retains the complete before/after ledger and review scope in
`dev/german-ui-2026-09-30/`. No application catalog or dependency was changed
by this task.

Verification: 27 writing-guide tests, four skill tests, both strict site builds,
and direct TMX/table/QPH parity checks. Runtime UI review is not claimed.


## 2026-09-29: source-fix feedback and explicit dispatch

Added flushed stage/elapsed-time messages and a five-second heartbeat on stderr,
with phase-aware Ctrl+C exit 130. Library calls stay silent. The Proteus wrapper
now shows help with no arguments and requires prepare, preview or apply. Preview
forces dry-run even if conflicting options are supplied. No new dependencies.

Verification: 1432 Python tests passed (two existing dependency warnings), Ruff
passed, and three Bash-wrapper regression tests passed. Live FontLab preview
reported zero corrections; all catalog and snapshot hashes stayed unchanged.
Existing unrelated working-tree edits were preserved.

## 2026-09-29: English copy edits upstream from Qt Linguist

Implemented `source-fix prepare/apply` in `sourcefix/`, with the Fire command
group, README example and generated CLI reference. Reuses TS XML/splice code and
tree-sitter with the published tree-sitter-cpp 0.23.4 grammar. Checked official
Qt TS location and lupdate documentation. A real corpus pass exposed a native
Point-accessor crash on macOS; byte offsets avoid it (py-tree-sitter issue 487).

Preparation refuses to overwrite the editing mirror or its hash snapshot. Apply
resolves current identities with Qt, parses literal spans, validates every edit,
then rebuilds all runtime catalogs against a temporary source overlay before
committing anything. The mirror is reconstructed from fresh English source text,
preserving unrelated drafts; the snapshot becomes the next baseline. Foreign
translations, plural forms and review states survive the rebuild. Existing
entries that cannot be extracted in this checkout remain active rather than
being removed. This is a copy-edit operation, not catalog deletion authority.
All available files referenced by the English catalog are extraction inputs;
new files with no prior catalog references require normal project extraction.
Native rebuilds update source locations and can normalize formatting. Significant
spaces before newlines use XML entities without changing their text value.

Created Proteus `i18n/fontlab_en_tofix_fix.sh` and ran preparation: 10,418 ordinary
entries, 66 plurals, 698 internal files, 38 external and 16 missing files. Fixed
the macOS Bash 3 empty-array case found by the first live invocation, before it
wrote anything. The user approved running live, rebuilding, committing and
pushing. Applied Bar_Glyph Shapes count to Elements count in bar_glyph.ui and
all five runtime catalogs, then rebuilt those and the editing mirror. Rebuild
found 46 additional current strings: all six catalogs now have 10,530 active
entries, with every previous key retained except the intentional renamed key.
All existing foreign text, including the user's earlier German edits, survived.
Repeat application reports zero edits and writes no files.

Verification: baseline 1382 tests passed. Added 39 source-fix regressions and
one executable README example; final suite 1422 tests (two existing dependency
deprecation warnings). Sourcefix coverage exceeded 90% before the final whitespace
regression. Native tests cover C++/UI extraction, multiline locations, repeated
application, reconstruction with new messages and retained drafts/missing sources.
Direct live verification checked all six key sets, every existing foreign
translation, the exact UI change and all source snapshot hashes. Proteus's own
validator reports 0 errors; each foreign catalog has 47 unfinished entries
(the corrected message plus 46 new ones). Native lrelease successfully compiled
all five runtime catalogs into temporary QM files. No FontLab binary was built.

## 2026-09-29: core TMX to Qt phrase books

Added `memory/qph.py` and `localizzy tm tmx2qph INPUT OUTPUT --target LANG`.
Reuses the existing TMX reader and lxml; no new dependencies. Format verified
against Qt's `qttools/src/linguist/linguist/phrase.cpp` and the
[Qt Linguist manual](https://doc.qt.io/qt-6/linguist-reusing-translations.html).
Exports exact source/target text in input order, all unit/segment notes and
x-status as definitions. Proposed entries remain included, with their status
visible; Qt has no review-status enforcement for phrase books. Rejects lossy
inline conversion, empty/missing/duplicate segments and input/output identity.
Writes atomically after validating the complete memory. README and generated
CLI reference updated, including executable README coverage.

Ran the CLI on the styleguide's `localization/tm/*-core.tmx`, producing
`fontlab/Proteus/i18n/fontlab_{de,es,fr,pl}.qph`: 222, 222, 222 and 231 phrases.
Spanish retains its es-419 locale as the Qt tag es_419. Independent stdlib XML
comparison verified all 897 pairs, definitions, statuses and language attributes
against the original TMX files. Source memories were not changed.

Verification: baseline 1372 tests passed; nine new exporter regression tests
first failed on the absent module, then passed. Final full Python suite:
1382 passed, two existing dependency deprecation warnings. Ruff lint passes;
changed Python files pass formatting. Repository-wide format check reports
pre-existing formatting in `scripts/gen_cli_docs.py` and `memory/glossary.py`;
those unrelated files were left unchanged. `git diff --check` passes.

## 2026-09-29: fl10n issue 147, x-fallback and the book

Later the same day: `docs/` reduced to the built site only. The thirteen
package pages and the two reviewer design notes moved into `src_docs/md/8-toolkit/`
as Part 8 (explicit order in `nav.yml`), review screenshots into
`src_docs/md/assets/review/`, CLI doc generator and its test repointed. Chapter
sources now link to fontlab.dev styleguide pages and to the toolkit pages;
abersetz linked from the home page, toolkit index, memories, translation and
README. Strict build: 94 files, 0 problems, 0 warnings; `test_docs_cli` passes.

Added `x-fallback` to the glossary memory (`memory/glossary.py`), one test,
docs. Set up `src_docs/` with the same ProperDocs and MaterialX tooling as the
FontLab writing styleguide; wrote the book brief and outline; seven writer
agents drafted the seven parts; `src_docs/build.sh check` enforces frontmatter,
no dashes and the banned-word list, and `build` runs `properdocs build
--strict`. Full test suite: 1372 passed; ruff clean.

## 2026-09-28 — module consolidation and README (toolchain Steps L9, L10)

Done on branch `consolidate` (git worktree `vexy-localizzy-consolidate`), one
commit per step: move script, `qa/`, `translate/`, `memory/`, `cli/`,
`extract/` + `review/` + `corpus/`, `experimental/`, docs.
- `scripts/move_modules.py` did every move and import rewrite. A rerun over all
  groups changes nothing. `tests/test_move_modules.py` covers the rewrite rules.
- Top level keeps `catalog`, `locales`, `json_values`, `json_sequence`, `xmlio`,
  `conversion`, `inventory`, plus 39 deprecated alias stubs: the 25 research
  modules and 14 paths fl10n imports. `tests/test_moved_module_aliases.py`
  checks that each alias is the same module object and warns.
- Two import hazards were fixed on the way: `translate/__init__` exports lazily
  (qa.text → translate.types, translate.run → qa), and `cli/__init__` never binds
  `translate`/`upgrade`/`tm`, so those stay submodules.
- README rewritten (159 lines). Format prose moved to `docs/formats.md`, corpus
  prose to `docs/corpus.md`, research prose to classification, retrieval and
  distillation docs. `docs/cli.md` is generated by `scripts/gen_cli_docs.py`
  and checked by `tests/test_docs_cli.py`; `tests/test_readme_examples.py` runs
  the six README commands on fixtures (review with the server call stubbed).
Checks after every step: full suite, ruff, `localizzy --help` and `tm --help`
identical to the baseline, every module imported in a fresh process, and the
fl10n suite run against this tree through fl10n's venv with `PYTHONPATH`.
Result: 1282 passed (1182 at the start). fl10n: 157 passed; the 16 review
tests fail because `fl10n/engines/_review_app.py` builds the path
`review_server.__file__` + `review_web` itself. With the one-line change to
`review_server.WEB_ROOT` they pass (checked on a scratch copy). fl10n was not
edited.
Next: fl10n switches to the new paths and the WEB_ROOT line, then the fl10n
aliases go; the research aliases go once the classification run is sealed.

## 2026-09-28 — TS upgrade (toolchain Step L5)

New `upgrade/` subpackage and `cli_upgrade.py`, with 60 tests in `tests/upgrade`.
Real-data check, read-only, with no memories and no engine:
- FRESH is fl10n's `i18n-repo/fontlab_de.ts` (10,474 messages). APPROVED is
  `i18n/fontlab_de.ts` (10,587 messages).
- Results: 10,448 exact, 11 fuzzy_similar (typo fixes such as "Horizonal" to
  "Horizontal", ported unfinished with `<oldsource>`), 15 untranslated and 128
  retired. Both invariants hold. The run takes about 0.9 s.
- `upgrade_ts(X, X)` is byte-identical for both files, at about 0.7 s each.
- Two of the untranslated messages had text in FRESH. Tier 10 empties it by
  design, because FRESH never owns translations.
Not wired into `cli.py`; run `python -m vexy_localizzy.cli_upgrade`.

## 2026-09-28 — translate with memories (toolchain Step L3)

New `translate/` subpackage, `cli_translate.py` and `cli_args.py`, plus the
`prefilled=` path in `translate_catalog`. 61 new tests (tests/translate,
tests/test_cli_translate.py) use a recording fake provider and no network.
Real-data check, memory-only, on fl10n's `fontlab_de.ts` (10,587 messages) with
the style guide's de memories:
- keep-existing: output identical to the input bytes; 28 existing translations
  fail QA and are reported as `KEPT-QA-FAIL`.
- `--nokeep-existing`: 10,267 context hits and 269 term hits; 51 pending
  (28 QA-rejected hits plus whitespace-padded sources). All context hits equal
  the existing text. 32 term hits differ from it, because the glossary and the
  catalog disagree (for example Dialog vs Dialogfeld).
Not wired into `cli.py` yet; run `python -m vexy_localizzy.cli_translate`.

## 2026-09-28 — legacy converters moved from fl10n (toolchain Step L7)

`src/vexy_localizzy/extract/` now holds ports of fl10n's `ts2tmx`, `po2tmx`,
`lproj2tmx`, `adobe2tmx`, `oss2tmx` and `tmxnorm`. `cli_tm.TM_COMMANDS` exposes
them for the `tm` group, which is not yet wired into `cli.py`.

- **Goldens.** The old scripts ran from fl10n's `.venv` on synthetic inputs only.
  Re-running `tests/fixtures/legacy_golden/capture.py` reproduces them byte for
  byte.
- **Parity tests.** `tests/extract` has 83 tests. 56 are the ported fl10n legacy
  tests, which also pass 56 of 56 in fl10n. 27 are new parity, registry and CLI
  tests.
- **Wheel.** The wheel ships `extract/oss_apps.toml` without any pyproject change.
- **Next.** fl10n Step F1 rewrites the `run_*.sh` wrappers to call
  `localizzy tm …` and deletes `tools/*2tmx.py` and `tmxnorm.py`.

## 2026-09-28 — memory loaders (toolchain Step L2)

New `src/vexy_localizzy/memory/` (langmatch, direct, glossary) reads TMX through
`tmx.read_tmx`, which now keeps TU and TUV notes. 36 new tests in `tests/memory`
pass; the full suite passes 946 (baseline 910). Real-data check: de and es UI
memories each load 10,373 of 10,373 TUs (`de_DE`→`de`, `es_MX`→`es-419`).
`fontlab_de.ts` gets 10,309 context hits out of 10,587 messages, and every hit
equals the existing translation. The glossary has 206 terms (147 approved and
59 do-not-translate), with 2 proposed terms excluded. Of the 278 misses, 270 are
core terms. The other 8 have leading or trailing spaces or a trailing CR, which
the style guide's `build_tmx.py` trims away, so they correctly miss verbatim
lookup. 24 messages get both a context hit and a whole-term glossary match, so
Step L3 needs a precedence rule. Next: Step L3 wires these into
`localizzy translate`.

## 2026-09-14 — ordered CLIPROXY successor

New classifier work uses the user-specified ordered 24-model CLIPROXY pool. The
first three routes form the consensus panel; every later route is an ordered
fallback. Cache schema 5 saves warm successes and cool failures, probes one due
cool route without displacing a warm panel, and retries a recovered primary after
its provider cooldown expires.

The incomplete run `fcbe3d8b…3491` is superseded without modifying its
1,023,706 decisions. The ready successor `3b8b10ba…f6419` serializes exactly its
1,200 unresolved IDs, frozen input, predecessor binding and routing identity in
private evidence. It becomes running only when the credentialed launcher writes
its PID. Focused verification passed 55 public classifier/parser cases and six
private successor/launcher cases with Ruff checks. This shell has no
`CLIPROXY_API_KEY`, so inference has not started.

## 2026-09-13 — live resume checkpoint

At 22:12 CEST, the credentialed classifier resume remained live and had saved
17,700 decisions beyond the prior 325,984-decision checkpoint: 1,009,881 of
1,024,906 expected source IDs are now durable, leaving 15,025. The exact same
run directory, SQLite decisions/cache, frozen input and model-identity evidence
remain in use. Its final-pipeline watcher remains live but intentionally makes
no outputs until this run writes a valid `complete.json`; it will then execute
the immutable classification export, embedding/cluster handoff, and two-pass
distillation sequentially. If either process stops before that marker, resume
the existing run from the credentialed root; do not create a replacement run or
publish a partial snapshot.

At 22:35 CEST, a read-only `count(*)` of the live `decisions.sqlite` recorded
1,014,681 durable decisions of 1,024,906 expected IDs (10,225 remaining). Use
this database count, rather than a resumed-process counter, for final progress
and completion verification.

At 23:18 CEST, the resumed classifier terminated cleanly but unsealed: it
recorded 1,023,706 of 1,024,906 decisions and reported 1,200 pending entries.
There is no `complete.json`, final classification handoff, embedding, cluster,
distillation, or memory-contract artifact. The three-stage watcher rejected the
stopped classifier without publishing partial output, and its contract
supervisor likewise rejected the absent distillation evidence. The durable
`decisions.sqlite`, frozen input and model-response evidence are the only
resume state. Do not create a replacement run or export a partial snapshot.
Resume this exact run from a credentialed context once an eligible provider
route is available. `classify_public_run.py` atomically updates
`evidence/classification-active.json` with its own new PID before it starts
work; then start `final_pipeline_watch.py` in a separate credentialed process.
The final pipeline must begin only after a valid `complete.json` exists:

```sh
rtk proxy integrations/classification/.venv/bin/python -u evidence/classify_public_run.py \
  --run-id fcbe3d8b1981b770cff76d34270dfad5022e6396229793ac40014e59ec783491 \
  --predecessor cda73d058ed1ab18a13c4b33a97c509761b5aecf408cab58811464bd23b4c7cf \
  --workers 1 --request-interval 7
rtk proxy integrations/distillation/.venv/bin/python -u evidence/final_pipeline_watch.py
```

The shared response cache confirms this is upstream capacity, not a local
runner failure: `gemini-3.6-flash-high` is in `http:429` cooldown until
2026-09-19 19:33 local time; GPT fallback routes until 23:56; and
`claude-sonnet-4-6` until 2026-09-20 06:44. An immediate resume would repeat
the same exhausted panel, so wait for restored access or configure a compatible
additional endpoint before resuming.

The stopped three-stage watcher predated the final memory-contract stage; its
separate postflight supervisor also stopped safely when no distillation evidence
appeared. The current `final_pipeline_watch.py` now runs classification export,
embedding/clustering, two-pass distillation, and `final_memory_contract.py` in
that order. A resumed watcher therefore writes `final-memory-contract.json`
only after all matching sealed evidence exists.

New classification runs now use Gemini 3.6 Flash High as the first requested
route, followed by Claude Haiku 4.5 and GPT-5.6 Terra for the required
three-identity consensus. GPT-5.6 Luna and Claude Sonnet 5 are absent from the
new primary panel and every fallback chain. The live run retains its sealed
identity so existing decisions and cache evidence remain valid; a policy change
there would require a separate full run.

At 12:07 CEST, the full classifier (PID 15278) and the first distillation pass
(PID 95981) are both live. The classifier has 858,722 durable decisions: 192,525
above its 666,197-decision baseline. Its log continued from 190,625 to 192,025
new decisions during this check, and the decision database passed `quick_check`.
There is no classifier `complete.json` yet, so final export, embedding,
clustering and final distillation remain correctly gated on its terminal result.

The distillation staging database has all 436,334 input entries, 54 chunks, 746
completed results and 652 pending clusters; its `quick_check` also passes. Its
response cache contains 800 reusable responses and 38 selections. The live log
shows successful calls through the available Claude and Gemini 3.1 Flash Lite
routes, while individual Claude Sonnet timeouts receive the configured temporary
cooldown instead of stopping the pass.

Resumption is deliberate and tested. Classification owns a `.run.lock` and
replays durable SQLite decisions, pending batches and cached responses; it seals
only after the exact expected count is present. Distillation owns
`.pass-1.sqlite.pending` and validates its staged input before resuming only the
remaining clusters, reusing its response cache. Do not manually restart either
while its lock is held. If an owning process exits, resume with its same
run-specific runner and existing database/cache rather than creating a new run.
The pinned-runtime resume suite passed 27 tests: classification sealed and
interrupted-run recovery, plus distillation pending-cluster, cancellation and
input-validation recovery.

At 13:39:41 CEST, the live distillation process exited after
`sqlite3.OperationalError: database is locked`; no process subsequently held the
staging file. A direct resume attempt correctly made no provider calls because
this shell lacks `CLIPROXY_API_KEY`. The classifier remains live and advancing:
its log reached 246,784 newly saved decisions at 13:40:24 CEST. Resume
distillation only from the credentialed launcher context, using the same
directory and its existing `.pass-1.sqlite.pending` and `responses.sqlite`.

At the later status check, the classifier process was no longer present and no
`complete.json` existed. Its last durable log checkpoint was 325,984 new
decisions, or 992,181 of 1,024,906 total (96.807%), leaving 32,725 entries.
Resume from the existing run directory and cache with the credentialed
`classify_public_run.py` launcher; do not create a replacement run or modify
the sealed identity.

The classifier was restarted from the credentialed workspace root as PID 43893
with the same run ID, one worker and a seven-second request interval. It holds
the run lock and has the frozen input, decisions database and shared response
cache open while it revalidates saved batches. That preflight completed and the
worker resumed durable saves at 20:57 CEST; it had saved 400 additional decisions
by 20:58 CEST. The preflight preserves the prior checkpoint instead of
reclassifying it.

A separate credentialed `final_pipeline_watch.py` process now watches PID 43893.
It is live and deliberately quiet until this exact run writes a valid
`complete.json`; it will then run the tested classification handoff, final
embedding handoff and final distillation handoff in that order. If the classifier
exits without sealing, the watcher refuses to publish partial data.

## Provider recovery and JSON presentation

A recovered route repeatedly wrapped selection JSON in a code block, including
when the proxy received JSON response mode. Added recognition of exactly one
complete JSON/unlabelled code block; surrounding prose and extra content remain
invalid. The original response stays in cache and its full byte budget is checked
before parsing. Thirteen new parser cases and the fenced fallback/cache variant
exercise formatting compatibility without changing selection or quorum rules.

Fresh full verification passes 892 Python tests, 66 ICU tests and 14 reviewer
tests, lint/format, TypeScript and frontend build. The stopped selection runtime
was updated from the built wheel; all 108 Python modules and 113 package files
match the installation. Its 226 classification, transport and selection tests
pass. Existing cached responses remain byte-identical. A live alternate still
returned explanatory prose outside its JSON block: that response remains invalid
and follows bounded retry/fallback, rather than weakening the selection contract.

## Shared keyed JSON resources

Added generic JSON leaf projection with typed paths and paired CLI extraction.
Reused existing strict standard-library JSON hooks and shared path encoding with
i18next, keeping plural grouping confined to native i18next editing. No dependency
was added. Official decoder documentation and existing implementations were read.
Seventeen public cases cover nested/literal keys, arrays, empty leaves, malformed
input, duplicate keys and Unicode. Eleven private consumer cases reproduce and fix
silent malformed-resource omission, replacement decoding and ambiguous dotted
keys while retaining UI filters, locale policy and provenance. A real-resource
audit additionally reproduced destructive trailing-dot removal in consumer keys;
the corrected wrapper preserves literal dots and restores a collapsed record.
The full gate passes 878 Python, 66 ICU and 14 reviewer tests, lint/format and
frontend build. The installed consumer passes 194 tests. Native JSON comparison
and installed-artifact evidence are recorded privately; no source data changed.

## Shared multilingual Apple tables

Added ordered binary/XML loctable reading and explicit source/target table pairing
to the extraction command, keeping raw names separate from output locale tags.
Factored keyed resource pairing into source_resources without changing other
format policies. Twelve public cases cover locale selection, metadata, provenance,
plural fallback and error preservation. Consumer regressions reproduce partial
publication after a malformed resource; the wrapper now stops before any output
write and retains its existing locale aliases and Base fallback policy. Fresh
focused verification passes 43 cases. Full test.sh passes 861 Python, 66 ICU and
14 reviewer tests, lint/format and frontend build. Native resource and installed
consumer verification passes; detailed application evidence remains private.

## Mozilla resource extraction

Moved Mozilla properties/DTD extraction to published moz.l10n 0.14.2 after
API/source inspection and isolated parser checks. The adapter preserves DTD
reference spelling, omits includes/comments and decodes properties values while
joining valid surrogate pairs. Public CLI supports DTD and explicit Mozilla
properties syntax. Six consumer regressions reproduce commented entity extraction,
truncated/undecoded values, invalid input omission and false plural-key pairing;
all now pass. Twenty public cases cover parser and command behavior, including
the documented upstream DTD quoted-comment restriction. Real private audits cover
377 entries and 188 CLI bilingual units, preserving sources and provenance while
correcting two escaped properties values against native Java. Installed artifacts
and final test counts are recorded in private evidence.

## Shared properties resource projection

Added published javaproperties 0.8.2 to the sources extra, after official API/source
inspection and an isolated PoC. A small shared adapter retains ordered duplicate
keys and exact decoded values; the public extraction command joins UTF-8 resource
pairs by key. Fourteen new public cases pass; full test.sh passes 829 Python, 66
ICU and 14 reviewer tests, lint/format, TypeScript and frontend build. Consumer
regressions reproduce and fix merged lines, surrogate corruption and partial
publication after reported resource errors. Real native Java comparisons pass
193 input files plus three encoding fixtures, covering 124,288 consumer entries.
Private installed-command evidence records final artifact verification.

## Shared extraction entrypoint

Added the generic extract command over existing source projections and the atomic
TMX writer. Keyed resources require explicit source/target language; native regional
tags stay intact. Output aliases and invalid XML are refused. Nineteen cases cover
CLI dispatch, all readers, source preservation, deduplication and plural fallback.
Review reproduced an ordinary-key/plural-key false match; fallback now uses only
actual projected plural metadata. Full gate passes 815 Python, 66 ICU and 14
reviewer tests, lint/format and frontend build. Real installed-command comparisons
and source hashes are recorded in private evidence.

## Shared Fluent resource projection

Moved legacy message/term/attribute and selector extraction to fluent_resources,
using published fluent.syntax 0.19.0 in the sources extra. Official AST/parser
docs and installed serializer source were inspected. Fifteen new tests and three
consumer tests pass. The malformed-entry omission is reproduced and now rejected;
Cartesian expansion is bounded before allocation. Two revision-pinned real source
files retain all 1,329 projected entries and all 666 old/new CLI bilingual units.
The full test.sh gate passes 796 Python, 66 ICU and 14 reviewer tests, lint/format
and frontend build. Real OSS Qt output also matches across all 119,796 units,
269 source catalogs and 34 languages. Installed evidence is recorded privately.

## Shared Apple resource values

Moved binary/XML/text resource reading and the legacy plural/device projection
into the shared package. Text parsing uses openstep-plist 0.5.2 in the sources
extra, after official documentation/source inspection and an isolated PoC.
Duplicate keys retain order. Quoted comment markers and supplementary Unicode
now survive; invalid syntax/encoding is rejected. Application discovery, locale
normalization and pairing stay with consumers. Twenty-two new cases and seven
consumer legacy tests pass. Full test.sh passes 781 Python, 66 ICU and 14 reviewer
tests, lint/format, TypeScript and frontend build. The native plutil comparison
passes UTF-8/BOM/UTF-16 values and reproduces the old corruption; all 41,347
real Qt/gettext/Apple/Adobe output units still match their legacy commands.
Installed-package evidence is retained privately.

## Shared legacy source projections

Moved the Qt/gettext TMX pair-selection rules into an explicit compatibility
module, retaining parsed input contracts and historical first/last plural policy.
Native document conversion remains separate and preserves complete catalog state.
No resource discovery, application defaults or private locale policy was copied.
Official Qt schema/polib contracts and existing implementation were inspected.
Attribution is included in NOTICE; no new dependencies are required.

Fresh relevant baseline: 58 public tests and four consumer writer tests pass.
Eight new projection cases and the consumer delegation check pass. The full gate
passes 759 Python tests, 66 ICU tests, 14 reviewer tests, lint/format and frontend
build. Real old/new CLI and installed-package verification are recorded privately.

## Preserve partial assignments during provider outages

Fresh full baseline: 748 Python, 66 ICU and 14 reviewer tests pass. A new
overlapping-route regression reproduced a replacement request despite two usable
cached votes and a third slot in a seven-day cooldown. Model assignment now starts
from the cached partial panel and extends it, retaining distinct identities and
allowing reassignment when needed to complete a panel.

Three added cases cover the reproduced no-request path, fetching one missing vote
and moving a cached vote to complete a distinct panel. Full test.sh passes:
751 Python tests, 66 ICU tests, 14 reviewer tests, lint/format, TypeScript and build.
The response schema and durable selection identities are unchanged. Running
consumer processes retain their pinned runtime until their next controlled restart.
The wheel and source archive build successfully; all 100 Python modules match an
isolated installation, which passes 192 provider/classification/distillation tests.

## Reuse fallback votes across partial-panel recovery

The existing quota path already persists multi-day cooldowns, immediately tries
configured alternatives, retains actual model identities and leaves exhausted
work pending. A fresh 71-test baseline passed. Two new regressions then exposed
unnecessary requests when an incomplete panel's primary recovered, or overlapping
fallback chains could supply all three votes from cache.

Routing now resolves a complete cached assignment first and prefers accepted
votes while filling incomplete panels. Completed selections and cache schemas
remain unchanged. The concurrency regression still exercises a different winning
selection by completing an already-in-flight primary request before publication.

Both regressions failed before the fix and pass afterwards. Full test.sh passes:
748 Python tests, 66 ICU tests, 14 reviewer tests, lint/format, TypeScript and build.
The private classifier runtime was updated after verifying no worker was active;
all 100 installed Python modules match the wheel and source, and 160 installed
classification/transport tests pass. No live provider requests or classification
data writes were made. Dependency versions are unchanged.

## Numbered ICU component validation

The optional Node checker now walks the published ICU parse tree with component
scope and branch nesting state, without expanding selector combinations. It
preserves compact numbered tags, counts, labels and argument ownership while
allowing sibling reordering and required target-locale branch expansion.
Independent review exposed empty-link acceptance and tag construction across
tokens; failing regressions reproduce both and the fixes pass. Default ICU-only
behavior remains unchanged. The separate npm package is now 0.1.1.

Full test.sh passes: 746 Python tests, 66 Node tests, 14 review tests, lint/format,
TypeScript and frontend build. An installed private consumer matches all 100
Python modules and six npm files; cache/HTTP/native compiler checks exercise the
updated component mode. Consumer cutover evidence stays private. No source
catalog or provider/cache classification identity was changed.

## ICU QA and private PO integration

Added a separate optional Node checker with published MessageFormat parser 5.1.1
and a bounded Python bridge suitable for TranslationCache validation. It checks
native ICU syntax, argument contracts, nested selectors, locale plural categories,
format styles and offsets. Independent review reproduced duplicate-offset
acceptance and a selector-reordering false rejection; both regressions failed
before fixes and now pass. Native ICU's grammar independently confirms duplicate
offsets are invalid. Reordering uses compatible branch matching.

Final source gate passes 746 Python tests, 32 ICU Node tests, 14 frontend tests,
lint/format, TypeScript and frontend build. Built wheel/sdist and separate npm
tarball; an isolated installation verifies all 100 Python modules and five Node
files byte-for-byte. Real SDK/abersetz HTTP fixtures plus the installed ICU checker
prove quota fallback, rejection of three malformed candidates, valid alternate
selection and zero-call reopen. No live provider or canonical catalog was changed.

Private PO audit covers 11 catalogs/53,075 records with exact JSON round trips.
The published native compiler accepts all 52,804 nonblank targets; strict content
QA still finds 399 blocking review issues. Compiler success is not translation
approval. Consumer application baseline dependency issues and remaining RAG/MT
migration are recorded privately; the full MVP goal remains open.

## Quota errors returned with HTTP success

Baseline: 723 Python tests pass. Four new HTTP fixture regressions reproduced
quota errors bypassing durable cooldowns in classification and translation.
The shared completion boundary now uses the SDK raw-response API to retain
headers and recognizes nonempty error envelopes before content validation.
Both transports immediately defer these failures through existing fallback
policies; persistent diagnostics contain a fixed reason, not provider text.
Successful response parsing, cache keys and provider identity rules are unchanged.

Eight additional regression cases verify seven-day cooldown persistence, zero-call
reopen, all-provider exhaustion, recovery of only missing work, actual fallback
identity, successful replies with empty error fields, and missing/invalid reset
timing. Final test.sh passes: 735 Python tests, 14 frontend tests, lint, formatting,
TypeScript checking and the frontend build; two existing upstream deprecation
warnings remain. git diff --check also passes. Official OpenAI SDK
raw-response documentation and installed implementation were consulted; fixtures
exercise the installed SDK and published abersetz engine without network calls.
The active classification process and its separately pinned environment are
unchanged; this source update does not hot-patch its running interpreter.

## Consumer reviewer preparation

The consumer review migration exposed incomplete Qt plural shapes that could be
displayed but neither edited nor exported. Explicit prepare_review appends missing
positions without clearing existing translations or length variants, and rejects
extra positions or unsupported content instead of discarding them. Nine focused
public tests pass, plus three consumer regressions covering zero/one existing
plural forms through approval and native TS export. Consumer setup locking also
rejects a reproduced hard-link alias that could truncate an input.

The full installed consumer browser run exposed a RangeError for underscore
locale codes. Display-only normalization plus missing/unknown locale labels fix
the failure; seven new frontend regressions pass. Final source gate: 723 Python
tests, 14 frontend tests, lint/format, TypeScript checking and frontend build.
The isolated consumer passes 159 tests, 34-file mypy, full module-byte comparisons,
and a 10,543-message real-browser save/reload/CLI restart/export check. Independent
XML comparison preserves every unselected message and original source bytes;
Qt compiles the downloaded catalog. The one changed target is a synthetic audit
value, not a model translation. All corpus/real-translation MVP work remains open.

## Provider fallback envelope recovery

Fresh baseline: 709 Python tests pass. Five HTTP/SDK regressions reproduced an
uncaught AttributeError for null, list, string, numeric and boolean response
envelopes. Read the optional model identity safely at the transport boundary,
so invalid envelopes reach the existing bounded retry and ordered fallback path.
All 102 focused provider/cache tests pass, including multi-day quota cooldowns,
cached vote preservation, distinct model identities and zero-call cache reopen.
The complete test.sh gate passes lint, formatting, 714 Python tests, seven
frontend tests, TypeScript checking and the frontend build. Two existing
upstream test-client deprecation warnings remain.
No cache identities, dependencies or installed integration pins changed.

## Consumer translation migration and QA review fixes

Shared scalar QA now checks length before returning a blank-target finding.
The consuming QA adapter rejects conflicting scalar/plural length-variant aliases.
Three consumer regressions reproduce the review findings; the real historical
comparison still preserves exact scalar findings across 41,936 catalog units.

The published abersetz adapter accepts an explicit finite temperature, retaining
0.2 by default. HTTP tests prove the passed setting and reject invalid values.
The consumer now runs through shared catalog translation, native forms, content
QA, durable cache and provider fallback. It retains private tier/glossary/context
policy and accepts RAG context with provenance. Two independently reproduced
consumer preservation defects were fixed: equivalent locale spellings must not
replace approvals, and empty-source messages must retain their existing target.

Full source gate: 709 Python tests, seven frontend tests, lint/format and frontend
build pass. Installed consumer: 144 tests without skips, 33-file mypy, dependency
check and CLI conversion checks pass. All 99 toolkit/33 consumer module bytes
match source, wheels and installation. The installed consumer repeats all five
full-catalog HTTP fixtures: 53,128 scalar targets, 2,231 successful requests plus
one quota response; maximum HTTP body 42,735 bytes. Every replay makes zero
requests, source metadata is identical and all five Qt compilations pass.
The actual installed CLI also verifies quota fallback, recorded backend identity,
cache replay and exit 1 with a saved pending candidate. These are synthetic
outputs, not the required real translations or final corpus distillation.

## Custom transport fallback boundary

Verified the existing quota fallback against a fresh 697-test baseline. Four new
cases reproduced SQLite binding failures when custom transports returned lists
or dictionaries; a fifth null-response case already recovered. Validate the
transport result before assigning attempt content so all five follow bounded
retries and select the configured alternative. Reopening the cache makes no
additional calls for completed votes. All 94 focused provider/cache tests pass;
the full gate passes 702 Python tests, seven frontend tests, lint, formatting,
type checking and frontend build. Two existing upstream deprecation warnings
remain. No dependencies, routing policy or installed integration pins changed.
Quota tests cover multi-day reset timing, one HTTP attempt, persisted cooldowns,
distinct model identities, recovery and retention of partial successful votes.

## Shared consumer QA contracts

Added a small literal-token compatibility API, retaining PH/TAG diagnostic
contracts while sharing the existing Qt tokenizer and counting repeated tokens.
Thirteen public tests pass. The complete source gate passes 697 Python tests,
seven frontend tests, lint/format and build. Legacy ICU inventory remains an
explicit compatibility boundary rather than a full ICU validator.

The consuming package now shares token checks, structural HTML and length checks,
and native target traversal. Seven failing-before regressions cover repeated
tokens, localized/numerus Qt arguments, gettext plural sources and malformed
nesting. All 126 consumer tests and its 32-file mypy check pass. A historical
comparison found identical scalar findings across 41,936 units in four real
catalogs; source files remain unchanged. Installed artifacts match all 99 toolkit
and 32 consumer module bytes and pass CLI conversion/loss-boundary checks.
No running classification, retrieval or review environment was updated.

## Classification fallback response boundary

Fresh baseline: 680 Python tests and seven frontend tests passed. Two new
HTTP/SDK regressions reproduced SQLite ProgrammingError when a provider returned
list/object content: malformed attempt logging aborted before fallback. The
shared ModelResponse now requires text before any response enters that path.
Four added cases cover list/object/numeric/boolean content, bounded attempts,
actual fallback identities and zero-call cache reopen. All 103 focused provider,
classification, distillation and translation cache tests pass. Existing quota
coverage verifies one outage attempt, persistent multi-day cooldowns, primary
recovery and preservation of successful votes when every alternative fails.
Consulted official OpenAI SDK documentation and installed response definitions.
Final ./test.sh passes lint, formatting, all 684 Python tests, seven frontend
tests and the frontend build. Two existing upstream deprecation warnings remain.
No dependencies, cache identities or pinned integration environments changed.

## Frozen context handoff

Added sealed context preparation and translation preflight, with twelve passing
tests covering full input/batch identity, missing contexts, corruption and cache
replay. Initial preparation now canonicalizes glossary order and seals actual
serialized batch bytes; the reproduced write/load ordering regression passes.
The private context sizing failure was reproduced at 48,088 bytes for one complete
enriched item. Its explicit batch budget is now 50,000 bytes, preserving all source
text and references. All five archives prepare successfully. The installed
translation runtime verifies 98 module bytes, passes 123 isolated tests, and
replays all 53,128 scalar targets through 1,169 actual SDK HTTP-mock requests.
Every request preserves frozen batch bytes, style, glossary, examples and links;
the largest HTTP request is 53,353 bytes against the adapter's 64,000-byte limit.
Second passes make zero requests. Independent native XML checks and all five
lrelease runs pass; original sources remain unchanged. Outputs are synthetic,
using the four-source RAG test selection; final distillation and real translations
remain open. Wheel/sdist builds pass; wheel SHA-256:
`ad6a71742caa96a3650253ddb9f319130bb29408d6f6ed5967e5fc72c48bad2f`.

The isolated embedding environment repeated full preparation from this wheel,
with 98 module-byte checks and 19 passing context/editorial tests. All five
archives remain byte-identical, and an independent before/after hash preserves
every field and vector byte in all 345,626 embedding rows. Both sides of the
handoff therefore run from the same installed wheel without editable imports.

## Frozen RAG retrieval

Added source-filtered batch search with deterministic ties, bounded query/vector
blocks and caller-safe transaction cleanup. The retrieval context stages existing
weighted winners, filters by exact canonical target locale before top-k, verifies
source/vector bindings and seals target/vector content in a memory identity.
Plain exact matches precede semantic examples. Independent review reproduced lost
inline codes and occurrence lists exceeding the prompt budget; both now have
failing-before/passing-after regressions. Full XML segments remain in examples and
occurrence lists resolve through SHA-256 references outside the prompt. Follow-up
review verified both fixes and found no further high-impact issue in scope.

The actual SDK request previously omitted example provenance; its new regression
now passes and TRANSPORT_ID is version 2. No provider calls are needed for these
checks. Full selected-corpus retrieval, private style/help selection and five real
translated catalogs remain required; the four-source private audit is a bounded
integration check, not completion of those requirements.

Final source gate: 668 Python tests, seven frontend tests, lint/format and build
pass. Wheel/sdist builds pass. The isolated retrieval installation verifies all
97 module bytes, passes 46 tests and repeats 25 real queries across five locales
against independent target/lineage/cosine oracles. Every persisted manifest,
context-file hash and occurrence-reference digest was read back and verified;
all 345,626 vector records remain unchanged. Retrieval wheel SHA-256:
`c2e0e9d5e80ba9a261a783b13f6f033271c9c3fc012f15acaf32701bd403aeb8`.

The pinned embedding stack and published translation adapter have incompatible
huggingface-hub requirements, confirmed by dependency resolution. The private
retrieval environment preserves the existing embedding space. Next, freeze
prepared contexts for transfer to the separate translation runtime, then bind the
private style/terminology/help selection and final distilled corpus.

## Provider fallback response boundary

Verified the existing durable quota fallback with a fresh 641-test baseline.
Three new HTTP/SDK regressions reproduced uncaught AttributeError failures for
missing/null messages and non-text content in the abersetz adapter. Validate this
response boundary explicitly so the existing three-attempt malformed-response
policy reaches the next configured provider. Empty/null choices retain fallback.
All five new cases verify the actual fallback model and zero-call cache reopen;
58 focused transport/cache tests pass. The complete ./test.sh gate passes lint,
formatting, 646 Python tests, seven frontend tests and the frontend build; only
the two existing upstream test-client deprecation warnings remain.
Checked the official OpenAI Python error
documentation and installed abersetz invocation before changing the adapter.
No dependencies, cache identities, provider policy or installed runtimes changed.

## Browser reviewer delivered and checked

Connected the FastAPI store to a packaged React/TypeScript reviewer using published
quiht-core 1.0.8. Synthetic and private real-browser flows verify native forms,
preview selection/translation, keyboard saves, approval/advance, filters, conflicts,
invalid edits, reload and TS downloads. Fixed root-dialog positioning, missing
native input text, `notr` handling, mobile toolbar/preview clipping and the
independently reproduced approval-reason edit race. Fit/percentage scaling keeps
native geometry inspectable; unknown custom widgets retain renderer placeholders.
External/QRC image loading is explicitly outside this first reviewer.

The full source gate passes 641 Python tests; frontend build and seven tests pass.
Wheel/sdist include browser assets, frontend source/lock and dependency licenses.
The isolated installation passes 209 tests, all 95 module-byte comparisons,
four served-asset comparisons, actual browser save/reload and the five full-size
synthetic native catalog audits. The pinned translation/review wheel SHA-256 is
`8c6d91c03f4daf2f6ddfac727c258dcbecd0c8709afc83cc6b543a3e782e3a1e`.
The private workflow retained every message and original source hash. Public
screenshots contain only synthetic content; see `docs/design/review-fidelity.md`.
Two upstream test-client deprecation warnings remain. Full corpus processing,
distillation, RAG translation and consumer migration are still required by PLAN/101.

## Structured quota fallback

Extended the shared retry-delay reader to recognize Google's structured
RetryInfo durations, including error envelopes unwrapped by the installed OpenAI
SDK. A seven-day hint previously became the default 60-second cooldown. Header
and proxy-reset precedence remain unchanged; boolean and malformed hints are
ignored. Classification and abersetz translation share this normalization.

Fresh baseline: 608 tests passed. New regression tests reproduced 17 failures
before the fix. The final suite passes 638 tests, including real SDK/HTTP mock
coverage for immediate fallback, persisted cooldown and zero-call cache resume.
Existing tests verify primary recovery, distinct backend identities and pending
work when every alternative fails. Lint and formatting of touched Python files
pass. Repository-wide formatting still reports four pre-existing review API
files; two upstream test-client deprecation warnings remain. No live provider
requests, cache migrations or pinned runtime changes were made for this patch.

## Full catalog verification and reviewer storage

Catalog orchestration and explicit Qt template preparation now pass the complete
source gate. The independent full-source audit initially omitted Qt byte-node
tails; its corrected ElementTree oracle verifies all 10,543 messages in each of
five synthetic catalogs, exact target values, source metadata, complete native
plural shapes, zero-call repeat and successful lrelease. These are sentinel
outputs, not model translations or RAG acceptance. The 585-test wheel passed 153
isolated tests and byte identity for all 89 installed modules. Independent review
found unsupported XML could disappear in removed plural positions; two reproduced
regressions now pass.

The new reviewer filesystem layer stores canonical JSON and retained native
documents. Expected revisions, strict slot edits, QA, draft/approval states,
per-catalog locks and append-only intent/completion journals are implemented.
Recovery checks old/new hashes without replay. Review reproduced sidecar path
collisions that could truncate a catalog and missing directory synchronization;
five failing-before regressions now pass. The complete gate passes 604 tests,
including 19 reviewer tests. HTTP API, browser UI and private review remain open.
The rebuilt wheel/sdist pass, with 172 isolated installed-wheel tests, exact bytes
for all 92 installed modules and another five-catalog native audit. The pinned
translation/review integration uses wheel SHA-256
`1b98f2f8b81dd04b4ca0e69d4077b8a78c8dc6c637adb5dc8f2eddfb2315f0ea`.

The latest frozen classification snapshot has 519,120 decisions and 345,626 A/B
sources. Incremental embedding added 180,786 vectors, preserved all previous
164,840 rows exactly and reopened with zero inference. Direct vendor inference
for 17 samples matches within 1.53e-7 absolute component error. Classification
stopped cleanly at 543,363/1,024,906 decisions with provider cooldowns; all 239,507
predecessor decisions remain unchanged. Additional synthetic probes of three
advertised provider routes failed, so they were not added to the routing policy.

## Provider fallback and catalog acceptance

Fresh baseline: 575 passing tests and two reproduced catalog regressions.
Catalog policy now participates in provider acceptance before a response is
cached or selected. Additional validation preserves the original validator,
uses a separate cache identity and leaves the owning cache configuration intact.
Invalid reviewed variant aliases are rejected before reconstruction. Six new
cache tests cover policy isolation, original rules, callback mutation and invalid
identities. Split catalog fixtures and boundary tests into focused files.

The complete lint/format/test gate passes 583 tests. HTTP regressions verify
week-long quota cooldowns from headers and proxy bodies, one outage attempt,
fallback, preserved votes and zero-call resume. A fresh live read-only audit
finds 493,635 decisions and exact preservation of all 239,507 predecessor
decisions, including all 20,698 original decisions. The running producer remains
on its existing fallback-capable pinned environment. Full classification and
catalog artifact validation remain incomplete; these checks do not claim the
overall MVP is complete.

## Shared translation content QA

Added explicit Qt, Python-brace and native GNU printf policies, structural HTML,
mnemonic/length/empty checks and traversal of every native plural/length variant.
Plural keys are supplied from the application's native locale rules; unchanged
text and retained source markup defects remain visible review findings.
Fifty-five new tests include the real QA-to-cache fallback path. Direct reflection
found nested mnemonic, script-detection and implicit-format-index gaps; four
failing regressions now pass. Independent review reproduced automatic brace
roots with suffixes, empty visible HTML and msgfmt silently skipping malformed
source formats. Seven failing-before cases now pass; follow-up review verified
all fixes, native zero-argument/positional/star formats and meaningful entities.

The complete source lint/format/test gate passes 553 tests. Wheel/sdist builds
pass, and 57 isolated installed-wheel tests verify QA plus provider identity
fallback. The installed real-source audit covers all 10,543 messages, detects all
433 deliberate placeholder removals and leaves original files unchanged. Five
synthetic native catalogs confirm two plural forms for de/es/fr and three for
pl/ru; compiled QM values round-trip exactly. Twenty previously generated
synthetic translations pass the new validator with zero provider requests.
Full catalog translation, RAG and consumer QA migration remain pending.

## Provider fallback recheck

The fresh 496-test baseline passed. HTTP integration regressions then reproduced
blank and numeric provider model identities being accepted as distinct votes.
ModelResponse now rejects both before caching; the existing three-attempt malformed
response policy chooses an alternative, and reopening makes zero requests.
Both regressions and the complete 498-test lint/format/test gate pass. Existing
tests cover week-long header/body quota cooldowns, unavailable alternatives,
preservation of completed votes, distinct model assignment and recovery.
The running consumer already has durable quota fallback; its pinned environment
was not replaced during processing. This validation change applies to subsequent
installations.

## Translation adapter and durable cache

Added strict batch identities, the published abersetz 1.0.28 adapter, mandatory
caller-supplied content validation and durable ordered fallback/cache selections.
Transport and validation callback mutation, duplicate JSON fields, blank model
identities and invalid timeouts have regression coverage. The 496-test version
built successfully and passed 45 tests against its isolated installed wheel.
Its live synthetic audit translated four messages in each of five locales,
including one fallback result, and reused all results with zero provider calls.
This verifies the adapter and cache foundation; complete native catalogs, shared
content QA, full RAG integration and the review interface remain pending.

## Incremental corpus embeddings

The consuming workspace now freezes and validates sealed A/B classification
batches while the producer continues. Its first real snapshot covered 242,716
classified decisions and selected 161,530 sources. Published uubed MiniLM inference
filled all 161,530 vectors; independent checks reconciled every source ID/text,
vector shape, normalization and checksum, followed by zero-inference reopen.
Direct vendor inference for 17 distributed/longest-source samples matched within
1.58e-7 absolute component error. A newer snapshot added 3,310 missing vectors,
reaching 164,840; its complete reopen again performed no inference.

Seventeen private orchestration tests cover interrupted/pending classifications,
changed inputs, corrupt decisions/model records, source holes, corrupt vectors,
manifest corruption and snapshot deadlines. Independent review found whole-copy
SQLite locking and unchecked existing manifests; both failing regressions now
pass. The snapshot copies bounded pages, proves concurrent source-writer progress,
and checks existing manifests. Follow-up review found no remaining defect. These
are incremental caches; final A/B export, clustering and complete distillation
remain gated on classification completion.

## Public classification producer

Added bounded scheduling, immutable SQLite run identity, per-batch payload and
decision seals, resumable pending work and atomic final completion. Filelock
excludes duplicate writers. Twenty-seven tests cover quota fallback, malformed
batches, interruption, zero-call resume, schema/write/publication failures,
changed identities and six-call maximum concurrency for two workers. Independent
review reproduced input changing after preflight and poisoning a checkpoint; the
failing regression now passes with preflight hashes checked before dispatch and
commit. Follow-up review found no new defect. Full-input preflight discovered
one real source beyond the batch target: its full request is 59,103 bytes and
fits the 64 KB request budget. A failing-before regression now passes with
versioned singleton batching that preserves earlier cache boundaries. The full
lint/format/test gate passes 458 tests. An isolated installed-wheel audit replays
all 236,501 frozen real decisions/model records exactly, seals 2,607 batches,
and reopens with zero additional requests. It checks all 1,024,906 input records,
uses no network calls and leaves remaining work pending. The live cutover retained
all 239,507 final predecessor decisions and model records. Its first launch
encountered connection failures across providers; an authenticated endpoint and
completion probe passed using the inherited task environment. Restarting with
that environment resumed saved work and reached 240,107 decisions at the next
audit, with all predecessor records unchanged. The fresh lint/format/test gate
still passes 458 tests. Full classification and later MVP stages remain incomplete.

## Completed classification handoff

Added a public completed-run reader and A/B exporter with bounded input/decision
reconciliation, exact source-text binding, locale coverage and consensus replay.
Independent review reproduced a swapped decisions database being accepted under
another run identity. The failing regression now passes: completion must seal
the ordered decision/model digest, and readers never invent a legacy binding.
A second failing regression now rejects numeric completion flags; another rejects
classified text that differs from the bound corpus. Follow-up review reproduced
an omitted source and omitted rare target in self-consistent input; both regressions
now fail before the fix and pass with complete corpus ID/text/locale reconciliation.
Input preparation and export share exact eligibility queries. Final review found
no further defects. Full lint/format/test gate: 431 tests pass; 49 isolated
installed-wheel handoff/input/transport tests pass. The installed full-data audit
matches all 1,024,906 IDs/texts and 28,819,455 target-locale pairs across 343 locales
to the original input hash and corpus fingerprints; no full AB corpus is claimed.

## Selected-source TMX export

Added source-ID selection and optional frozen-corpus checks to the atomic exporter.
Selected IDs and winner scores are staged on disk; original family weighting,
lineage and all target locales are preserved. The origin registry excludes losing
and unrelated candidates. Twelve tests cover reimported weights, empty/invalid
selections, iterator failure and concurrent source changes. A failing ordering
regression caught source-ID properties after TUVs; output now follows TMX order.
Independent review reproduced stale numeric IDs after identical source files were
imported in reverse order. Classification input now includes a source/inline-XML
entry-map digest; frozen selected exports require and verify it as well as the
source snapshot. Existing live classification input/cache files are unchanged.
The 390-test gate and installed real export audit passed: four retained sources
yielded 84 bilingual units, with independently matched text, weights, lineage and
TMX DTD validation. The complete 1,024,906-record legacy classification input was
matched to corpus IDs/text and bound to the current source/inline-XML entry map.
Full-data AB/final export is still gated on completed classification/distillation.

## Durable distillation passes

Added ordered input reconciliation, bounded chunk/carry scheduling, checkpointed
decisions and no-overwrite complete-pass publication. Later chunks cannot remove
accepted representatives. Subsequent passes must exactly match predecessor kept
records and retain their source/embedding identity. Oversized entries are retained
verbatim; missing model votes remain pending. Nineteen pass tests cover two/three
passes, cancellation, malformed predecessor links, changed inputs, partial model
failure, bounded carry and oversized entries. Full gate: 375 tests pass.
Independent review reproduced interrupted schema initialization, unchecked dropped
predecessor inputs and missing chunk evidence. Failing regressions now pass with
atomic schema/identity creation, complete checksums, policy replay and binding of
final results to chunk evidence. Follow-up review found no additional defects.
Two installed real-data passes preserve four input records and vectors, retain
predecessor hashes and reopen with zero model calls. Full-corpus work remains open.

## Clustering and resumable subset selection

Added bounded clustering over a consistent embedding snapshot and strict
three-model subset selection. The shared cache preserves successful responses
through quota exhaustion and malformed output, records actual model identities,
and resumes missing votes after recovery. Reductions require majority semantic
equivalence, sufficient similarity and retained rare-language coverage.
A new regression reproduced omitted rarity context in selection requests; rarity
now enters the payload/cache identity. Similarity-only changes reuse model votes.
Full lint/format/test gate: 356 tests pass, including 42 new component regressions.
The built wheel reproduces partitions for 256 real cached vectors; independent
distance/nearest-center checks pass and the original cache hash is unchanged.
A live four-source selection with all weighted winner translations uses three
reported model identities through quota fallbacks; reopening makes zero calls.
All four sources are retained because the votes do not justify a reduction.
Complete corpus passes and their output exports remain pending.

## Resumable embeddings

Implemented bounded uubed vector caching, immutable source/engine identity checks,
checksums and streaming cosine retrieval. Twenty-four tests cover interruption,
resume, corruption, invalid vectors/inputs and batch bounds. Independent review
reproduced batch-dependent ranking for identical float32 vectors; a regression
failed before row-wise float64 accumulation fixed the tie ordering.
The full lint/format/test gate now passes 314 tests.
The installed-wheel CPU check embedded 256 real classified A/B sources in eight
batches, reused all vectors on reopen, and matched independent cosine retrieval.
This verifies the component, not full-corpus A/B export, clustering or distillation.

## Legacy source utilities

Added the shared atomic TMX record writer and optional filename planner. The
writer's seven tests cover literal values, repeated origins and extraction/XML
failures; independent review also injected fsync/replace failures without losing
existing output. Real old/new consumer commands matched 41,347 units across four
source formats. Filename plans matched all 3,135 real paths in 64 folders; rename
and dry-run commands matched on ten private copies with hash-preserved collisions.
The planner's 21 tests additionally protect scripts, population ties, invalid tags
and private-use subtags. Full lint/format/test gate: 290 passing tests. Source
parsers and their legacy first/last plural projection remain consumer policies;
this checkpoint does not complete the entire source-adapter migration.

## In-memory conversion integration

Added `convert_catalog` so callers use the same loss detection and atomic output
gate without intermediate files. Complete ICU source/target strings remain literal
TS messages instead of becoming truncated numerus arms. A failing regression
reproduced the lost surrounding sentence; it now passes. Added the typing marker
and accurate string/Path JSON signatures for installed consumer type checking.
The full 262-test lint/format/test gate passes. An isolated installed consumer
checks shared type identity, exact TS/JSON CLI round trips and loss refusal; the
consumer's native-format audit also checks 701 source catalogs without modification.

## Provider outage verification

Confirmed the configured Gemini fallback chain selects GPT Terra, then Claude
Haiku, subject to distinct-model voting. The existing 255-test baseline passed.
Three new reset-parser regressions failed before the fix: an error envelope was
ignored, a body hint overrode an HTTP-date header, and an oversized integer raised
instead of using the default cooldown. All now pass. Added HTTP-to-classifier
integration checks for a 598,850-second quota reset, with and without Retry-After;
reopening the cache reuses completed votes and skips the unavailable primary for
new input. Full lint/format/test verification: 260 tests pass. No live credentials
or paid requests are required by these tests; ongoing consumer processes are unchanged.

## Initial data core

Implemented streaming catalog inventory, multilingual TMX records, SQLite
candidate voting, bounded import commits and compressed source snapshots.
Source versions become active only after a complete successful import.
Restoring a previous version reactivates its votes. Independent source families
vote once per candidate; occurrence links retain all contributing rows.

Independent review reproduced and prompted fixes for extension-element counting,
symlink identity, incomplete counters, unsafe changed-source resume, raw
provenance retention and missing durable failure details. Regression tests
were run failing before fixes.

Added per-unit product policies, duplicate-file aliases, inline-code aggregation,
schema migration and atomic TMX export/import. Derived imports verify each
original ordinal and source/target pair against preserved raw snapshots; they
cannot earn a new family vote. Namespace-normalized inline XML round-trips.
Exports reject destinations overlapping their own database or managed snapshots.

Pending: remaining format adapters,
classification/distillation, translation, review UI and consumer integrations.
This is a development foundation, not a completed 1.0 release.

Added strict 300–399 classification parsing, bounded request data, conservative
three-model consensus, rare-language promotion, and durable response caching.
Cache identity includes endpoint, model, rubric, text and locale coverage;
failed responses stay pending and successful providers are reused on resume.

Verification: 262 tests pass, including independent-review regressions for policy
history, legacy schemas, forged provenance, protected export paths and namespaces.
Wheel/sdist and an isolated installed-wheel import/export/provenance check pass.
The cache transport has a real three-provider bounded-data check and zero-call
reuse evidence in the consuming workspace; full-data classification is pending.

Added original-document TS/JSON fidelity and compatibility catalog types with
MIT attribution. All 701 real TS files (515,928 messages) round-trip through
canonical JSON byte-for-byte; 672 catalogs also pass an isolated target edit
checked independently with ElementTree. Original files retain their hashes.
Independent review found internal-DTD loss and a plural variant shape change;
both now have failing-before/passing-after regression tests.

A live quota exhaustion prompted user-authorized provider fallback support.
The v2→v3 migration preserved all 632 cached responses. A real 100-entry fallback
batch used three actual models and repeated with zero additional calls; another
100-entry check verified the secondary alternative's response format. Full-data
work resumed with explicit actual-model provenance and resumable pending batches.

Further fallback review fixes preserve the winning concurrent selection and keep
provider-reported identities separate from route labels. Alias collisions cannot
earn duplicate votes. Cache schema v4 preserves all 895 prior responses; historical
reported IDs remain unknown, with explicit configured aliases when available.
A fresh real batch verifies three distinct reported IDs and zero-call repeat.
The rebuilt wheel passes isolated corpus, TS/JSON and fallback/cache checks,
including its bundled attribution notice.

Added PO preservation, plural source text, TS/PO/JSON conversions with loss reports
and a real CLI round-trip check. All 11 consuming PO catalogs (53,075 messages)
round-trip through JSON byte-for-byte and pass isolated edit comparisons.
Independent review reproduced missing plural-count checks, silent rule changes
and ignored source-language edits; 12 regressions failed before the fixes.
The full lint/format/test command passes, as does a fresh installed wheel covering
corpus provenance, TS/PO/JSON and provider fallback/cache reuse.

Added XLIFF 1.2 generation and retained 1.2/2.0/2.1/2.2 editing. Both existing
XLIFF catalogs (981 messages in 92 file sections) round-trip byte-for-byte through
JSON and pass independent inline-edit tree comparisons. Fresh and edited outputs
pass official OASIS 1.2, 2.0 and 2.2 core schemas, including the real catalogs.
Independent review and direct checks produced eight failing regressions covering
segmented-target order, empty-target inline codes, explicit language labels,
unsupported states and target removal without resetting approval. All now pass.
The 191-test lint/format/test gate and fresh installed wheel pass; format work
continues with Android, i18next and catalog-level TMX conversion.

Added Android string/plural/array preservation and conversion. Independent review
reproduced two bugs in legal shared-name round trips and whitespace around
transparent placeholders; failing regressions now pass. The 24 Android tests and
four native AAPT2 comparison cases cover escaped/quoted text, Unicode, styling,
plurals, arrays, resource references and quoted/unquoted placeholder whitespace.
This is synthetic compiled-resource validation, not device or full-format coverage.
Full package verification now passes 215 tests. Provider fallback regression checks
also pass (26 focused tests); the live consumer audit preserves all 20,698 original
decisions and confirms continued fallback processing with no pending batches.

Added i18next v4 resources with typed nested/array paths, plural groups and
byte-scoped edits through published Tree-sitter parsers. Explicit source-format
selection distinguishes application JSON from canonical JSON. All 22 adapter/CLI
tests pass; review reproduced an empty plural-key mismatch, now rejected before
writing. Published i18next 26.3.6 matches 13 independent runtime comparisons.
Three existing generic nested JSON catalogs (771 messages) pass exact JSON round
trips, independent scoped-edit comparisons and original-hash checks. The complete
237-test gate passes. Catalog-level TMX conversion and later MVP stages remain open.

Added catalog TMX language projections, multilingual byte-preserving JSON round
trips and scoped target edits. Fresh TMX retains full catalog metadata and plural
values in documented properties. Three real native catalogs (533 units) pass exact
round trips, independent XML edit comparisons and source hashes; fresh rich output
validates against a bundled TMX 1.4 DTD. Review regressions cover empty-target inline
codes, protected exact-origin lineage and missing target-language declarations;
projection metadata stays isolated across language pairs. All 18 TMX adapter tests
and the full 255-test gate pass. Consumer migration and later MVP stages remain open.

2026-09-28, TS splice writer (plan Step L1): `ts.dump` on a retained TS document
now splices only edited messages into the original bytes (`formats/ts_splice.py`).
The span tokenizer is checked against the lxml parse on every write. Rendering
unedited messages reproduces all 42,348 messages of the four FontLab catalogs
exactly. Smoke check: a one-character edit in `fontlab_de.ts` gives a 5-line
`diff -U0` (was 38,139). 22 new tests in `tests/test_ts_splice.py`; full suite
passes. `ts_template.py` still re-serializes prepared documents; not changed here.
