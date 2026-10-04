---
this_file: WORK.md
---
# Work log

Earlier entries are in the git history of this file.

## 2026-10-04: Issue 160 glossary and QPH reconciliation

- Fixed whole-term matching for appended Qt shortcut annotations in ASCII and
  fullwidth parentheses. Embedded shortcuts still match, while escaped
  ampersands, longer parenthesized text, and nonterminal annotations retain
  their meaning. Added twelve regression cases, including whole-term lookup
  and ASCII/fullwidth colon suffixes.
- Documented the existing replacement behavior of QPH export and the required
  upstream reconciliation of curated translations before regeneration.
- Verification: five new failing cases reproduced before the fix; 202 focused
  tests passed afterward. Full `./test.sh` passed: 2,064 Python tests, ICU and
  reviewer tests, lint, formatting, and reviewer production build.
- No dependencies added. Existing Apple extraction work is outside this commit.

## 2026-10-01: Four limits found while drafting new languages

A project drafted fifteen languages with the toolkit and had to wrap four
limits in its own code. The generic part of each wrapper moved in; details are
in CHANGELOG.md.

- `editorial review --glossary-status` (`cli/editorial`, `editorial/candidates`).
- Term hits capitalize a lowercase target for a capitalized label
  (`memory/glossary`: `Term.label`, `capitalize_first`; `translate/run`).
- `%n` may be omitted in a numerus form that one count selects
  (`formats/qt_numerus`: `form_index`, `single_number_forms`; `qa/text`,
  `qa/catalog`, `translate/run`, `editorial/guards`).
- `translate_json`: one request per distinct text, fallback models, and a
  second chance for each item of a failed batch (`translate/json_file`,
  `json_request`, `json_sidecar`, new `json_rescue`).

### Verification

- `./test.sh`: ruff check and format clean; 2049 Python tests pass; ICU checker
  (66) and reviewer (14) suites pass; reviewer build succeeds.
- `src_docs/build.sh check` passes, and a strict book build into a scratch
  folder succeeds. The committed `docs/` site was not rebuilt.
- Real CLI, synthetic files: `qa --plural-forms auto` on an Arabic catalog
  reports only the range form that lacks `%n`; the new flags parse and
  validate.
- The numerus rules were transcribed from qttools `numerus.cpp` (branch 5.15);
  a test checks that every language's rule reaches exactly the forms of the
  count table.

### Not verified

- Live model calls. The paragraph and masked paths of `translate_json`, the
  fallback models and the `--glossary-status` prompt ran only against fake
  transports.
- `numerus.cpp` lists Filipino under both the French rule and the Tagalog rule,
  and the French entry comes first; the count table here gives `fil` and `tl`
  three forms. Neither rule has a one-count form, so the `%n` check is the
  same either way, but the count deserves a check against `lupdate`.

### Left as it was

- `localizzy upgrade` writes whole-string term hits without the capitalization
  step, as before.
- The engine prompt still tells the model to keep `%n` in every form, and the
  batch items do not say which counts a form serves, so an engine rarely uses
  the new freedom on its own; memory hits, kept translations and reviewers do.
- The `pofilter` QA layer applies Translate Toolkit's own tests and may still
  report a form without `%n`.

## 2026-10-01: Qt tooling, project file, editorial review, QA layers

The toolkit took over the Qt and project tooling that a separate project layer
used to hold. What arrived, by module:

- `project`, `cli/project`: `localizzy.toml`, `init`, `project upgrade|translate|build_ui`.
- `qt/`: source scanner (heuristic and libclang engines, `.ui` pass), `lupdate`
  and `lrelease` wrappers, app language launcher.
- `qa/layers`, `report`, `plurals`: optional QA layers, table/JSON/SARIF
  renderers, plural tables.
- `pseudo`, `vocab`, `doctor`, `external`.
- `editorial/`: model-assisted review candidates and guarded apply with ledger.
- `upgrade/diff`, `formats/ts_shards`, `translate/json_*`, `memory/glossary_json`,
  `memory/lookup`.
- `review/workspace`: catalog import into a resumable workspace.
- Book: eleven new toolkit pages (getting started, project, scanning, Qt tools,
  pseudo, editorial, JSON files, vocabulary, CI, troubleshooting, architecture);
  parts 1 to 7 no longer cite private repository paths.

### Verification

- `./test.sh`: ruff check and format clean; 1875 Python tests pass (94% line
  coverage over the package); ICU checker and reviewer suites pass (14 reviewer
  tests); reviewer build succeeds.
- Real tools, not mocks: `lupdate` and `lrelease` 6.11 round trips (a finished
  translation whose string left the source survives as vanished; an empty source
  directory replaces nothing); libclang on self-contained fixtures (exact
  `file:line:column` for `QT-CTX-001` and `QT-TR-002`; `QT-CLANG-012` plus the
  heuristic fallback when includes do not resolve; headers parse); `pofilter`
  3.20 through the QA layer.
- Real data, outputs to a scratch folder: `project build_ui` and memory-only
  `project translate` on four 10,500-message Qt catalogs; `tm lookup` over 7,516
  sources against a large TMX corpus; `diff`, `shard split`, `qt applang list`.
- An independent code review found one critical and twelve major defects
  (lupdate deleting obsolete translations, ledger overwrite on rerun, outputs
  that could overwrite inputs, printf and ICU corruption in pseudo, pofilter
  findings lost on multi-line sources, missing-path scans passing CI). All are
  fixed, each with a test.

### Not verified

- Live model calls: `editorial review`, `translate_json`, `translate` and
  `upgrade` with an engine, and the judge layer ran only against stubbed
  transports. No endpoint was reachable during this work.
- `qt scan --engine clang` on a real project with `compile_commands.json`.
- COMET quality estimation (`qa --layers qe`): only the missing-dependency path.
- The `translation` extra from PyPI: it needs abersetz 1.1, which is not
  published yet; the suite ran against the abersetz checkout.

### Next

The release gates in PLAN.md, section 1.
