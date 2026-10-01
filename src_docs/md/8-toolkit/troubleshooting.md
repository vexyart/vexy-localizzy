---
this_file: src_docs/md/8-toolkit/troubleshooting.md
---
# Troubleshooting

Start with `localizzy doctor`. It lists every external tool with its version,
every extra as installed or not, and the command that fills each gap. Then
read stderr before the exit code.

## Exit codes

Every command keeps to one contract:

| Exit | Meaning |
|---|---|
| 0 | Done; nothing blocking |
| 1 | Done, but not clean or not complete: `qa` at or above `--fail-on`, a critical `qt scan` finding or coverage below `--min-coverage`, a `vocab validate` finding, a `vocab compare` rate below `--min-exact`, untranslated or pending messages after `translate`, `upgrade` or `project upgrade` (their outputs are still written), untranslated `translate_json` items, unfilled shard messages, failed review batches |
| 2 | Usage or input: a missing or malformed input file, an unknown flag value, an output that would overwrite an input, a language without a plural rule, a conversion that would lose data, a failing `lupdate` or `lrelease`, a refusal to replace earlier work |
| 3 | A missing extra or external tool; the message names the install command |
| 130 | Interrupted with Ctrl+C |

A missing or malformed input file prints a single line starting
`localizzy:` rather than a traceback. A traceback (exit 1) means a defect in
the toolkit; report it with the command line that caused it.

## Symptoms

| Symptom | Cause | Fix |
|---|---|---|
| `Missing dependency: lupdate. Install with: ...` | Qt Linguist tools not found on `PATH`, in `$QT_DIR/bin`, the Homebrew Qt prefix or the usual Linux Qt directories | Install Qt's tools (`brew install qt`, `apt-get install qttools5-dev-tools`), or set `QT_DIR` |
| `Missing dependency: clang` | `qt scan --engine clang` without the extra | `uv pip install 'vexy-localizzy[clang]'` |
| `Missing dependency: translate-toolkit (pofilter)` | `qa --layers pofilter` without the extra or the `pofilter` command | `uv pip install 'vexy-localizzy[pofilter]'` |
| `Missing dependency: COMET-QE` | `qa --layers qe` | `uv pip install unbabel-comet`; the first run downloads a model |
| `The judge layer needs --endpoint, --model and the API key variable` | Exit 2 from `qa --layers judge` | Pass both flags and export the variable named by `--api-key-env` (default `OPENAI_API_KEY`) |
| `PLURAL-RULE` findings on every plural message | No required plural forms were given | Add `--plural-forms auto`, or the native forms such as `0,1,2` |
| `No positional plural mapping for 'xx-pseudo'` (exit 2) | `--plural-forms auto` on a pseudo catalog | Spell the forms out: `--plural-forms 0,1` |
| `TARGET-EMPTY` on every message | `qa` on a freshly extracted catalog | Expected. Gate reviewed catalogs only |
| `Pass source paths, or list them under [qt].sources` | `qt scan` or `qt extract` with no paths and no project file | Pass paths, or run `localizzy init` and edit `[qt]` |
| `Extra inputs are not permitted` naming a key | A misspelt key in `localizzy.toml` | Correct the key; unknown keys are refused, not ignored |
| `QT-CLANG-012` on every file | `qt scan --engine clang` without the project's include paths | Pass `--compile-commands build/compile_commands.json` |
| A translation exists but the application shows English | Context drift; `qt extract` does not show `lupdate`'s `lacks Q_OBJECT` warning when extraction succeeds | Run `qt scan`; fix every `QT-CTX-001` |
| Heuristic findings inside comments or generated code | The heuristic engine reads lines, not syntax | Scan the directories you own rather than the whole tree, or confirm with `--engine clang` on the file |
| `... exists and differs from this run's retired messages` | `project upgrade` again on the same two inputs, but the retired file was edited or comes from another run | Inspect the named retired file; move it aside if it is no longer needed |
| `glossary memories missing, so their terms would enter the project memory` | `project build_ui` without the configured glossary TMX | Restore the glossary memory, then rebuild |
| `localizzy: Review inputs changed; choose a new workspace` | The catalog or a `.ui` preview changed after import | Pass a new `--workspace`, or finish and export the old review first |
| `error while attempting to bind on address` | The review port is taken | Pass `--port 8766` |
| `Review frontend is missing; run npm ci and npm run build in review/` | A source checkout without built browser assets | Build them as shown in [review](review.md); wheels already contain them |
| A SARIF upload fails with 403 | Code scanning is not enabled for the repository | Enable it, or keep the SARIF as an artifact |

## When the output is right but surprising

A translation that looks right in the catalog and shows English in the
application is almost always a context problem: the class lost `Q_OBJECT`, or
the string was translated at static-initialization time. Run `qt scan` on the
file. A language that does not appear at all in a macOS build is worth a
`localizzy qt applang list` to see which catalogs were compiled in.
