---
this_file: WORK.md
---
# Work log

Earlier entries are in the git history of this file.

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

- `./test.sh`: ruff check and format clean; 1874 Python tests pass (94% line
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
