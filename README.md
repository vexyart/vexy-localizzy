---
this_file: README.md
---
# Localizzy

Localization software: catalogs, translation memories, memory-aware machine
translation, TS upgrades, QA and review. It uses
[abersetz](https://github.com/twardoch/abersetz) as its translation engine.

A catalog is filled from what is already known before a model is asked: kept
translations first, then your memories, then the engine. Every choice is
recorded, and an edited Qt catalog changes only in the messages that changed.

```
┌──────────────────────────────────────────────────────────────────────┐
│ your project                                                         │
│   localizzy.toml, catalog and memory folders, per-language tags      │
└───────────────▲──────────────────────────────────────────────────────┘
                │ Python API + `localizzy` CLI
┌───────────────┴──────────────────────────────────────────────────────┐
│ vexy-localizzy  (localization software)                              │
│   formats/  catalog I/O (TS splice writer, PO, XLIFF, TMX, Android…) │
│   memory/   TMX read/write, direct memory, glossary, build-ui        │
│   translate/ batches · cache · QA gate · memory-aware orchestration  │
│   upgrade/  TS upgrade (exact/relocated/fuzzy/memory/engine/retired) │
│   extract/  foreign sources → TMX (ts/po/lproj/adobe/oss, tm norm)   │
│   qt/       source scanner, lupdate/lrelease, app language launcher  │
│   editorial/ model-assisted review: candidates, guarded apply        │
│   qa/ · review/ · pseudo · vocab · corpus/ · experimental/           │
└───────────────▲──────────────────────────────────────────────────────┘
                │ engine API only: EngineRequest(text, voc, examples)
┌───────────────┴──────────────────────────────────────────────────────┐
│ abersetz  (translation engine)                                       │
│   engines/providers (ll, lm, ml, gg, tr, dt) · chunking · voc hints  │
└──────────────────────────────────────────────────────────────────────┘
```

abersetz never parses a catalog or a TMX. Localizzy never hard-codes a product
path, name or language roster; that belongs to the project on top.

## Install

Requires Python 3.12 or later.

```sh
uv tool install 'vexy-localizzy[translation,sources]'
```

| Extra | Adds | Needed for |
|---|---|---|
| `translation` | abersetz, openai | `translate` and `upgrade` with an engine |
| `sources` | Fluent, Java/Mozilla properties, OpenStep plists, CLDR population data | `tm extract` on those formats, `tm oss2tmx`, `tm norm` |
| `review` | FastAPI, uvicorn | `review` |
| `clang` | libclang | `qt scan --engine clang` |
| `pofilter` | Translate Toolkit | `qa --layers pofilter` |
| `llm` | openai, filelock | experimental classifiers and distillers |
| `embeddings` | numpy, uubed | experimental embedding cache and retrieval |
| `clustering` | numpy, scikit-learn | experimental clustering |

Development: `uv sync --group dev --extra translation --extra sources --extra review`,
then `./test.sh` (it also needs `npm --prefix review ci` and `npm --prefix icu ci`).

## Commands

See what is installed, and start a project file. `localizzy.toml` holds the
catalog layout, memories, language tags and engine settings, so the `project`
commands need only a language code:

```sh
localizzy doctor
localizzy init .
localizzy project upgrade de --no-engine
```

Audit Qt sources for strings that will never translate (a `QObject` subclass
without `Q_OBJECT`, `tr()` on a variable, a hard-coded label, a `.ui` string
marked `notr`). Findings print as a table, JSON or SARIF; a critical finding
exits 1. `qt extract` and `qt release` wrap `lupdate` and `lrelease`:

```sh
localizzy qt scan src --format sarif --out scan.sarif
```

Write a pseudo-localized catalog to test layouts before any translation exists.
Text is accented, padded and bracketed; placeholders, tags and accelerators
stay intact:

```sh
localizzy pseudo app_de.ts app_xx.ts
```

Check a catalog. The deterministic checks always run; `--layers
pofilter,qe,judge` adds the optional ones:

```sh
localizzy qa app_de.ts --plural-forms auto --format sarif --out qa.sarif
```

Translate a catalog from memories. Replace `--memory-only` with
`--endpoint URL --model NAME` to send the remaining messages to a model:

```sh
localizzy translate app_de.ts --target de --out app_de.new.ts --direct-memory de-ui.tmx --glossary-memory de-core.tmx --memory-only
```

Port approved translations onto fresh `lupdate` output, writing NEW, RETIRED and
a report. Exit code 1 means some messages are still unfilled:

```sh
localizzy upgrade fresh_de.ts approved_de.ts --out de.ts --retired de-retired.ts --no-engine
```

Convert between TS, PO, XLIFF, TMX, Android, i18next and canonical JSON:

```sh
localizzy convert de.po json de.json
```

Build a project memory from a finished catalog, omitting exact glossary pairs while keeping contextual translations:

```sh
localizzy tm build-ui de.ts de-ui.tmx --exclude-memory de-core.tmx
```

Turn a tree of Qt catalogs into TMX with the legacy language policy:

```sh
localizzy tm ts2tmx translations/ --output tmx/
```

Export a core TMX memory as a Qt Linguist phrase book:

```sh
localizzy tm tmx2qph de-core.tmx app_de.qph --target de
```

This preserves every source/target pair, including proposed and identical
translations. Definitions contain the review status and all unit/segment notes;
Qt does not enforce review status. Use the exact TMX target tag (for example
`--target es-419`). Missing, empty, duplicate or inline-marked segments fail
without replacing the output. Other TMX properties are not exported.

Render any two-language TMX as a self-contained HTML page with search, filters
on its `x-*` properties, notes and click-to-copy (the target is detected when
the file has one):

```sh
localizzy tm tmx2html de-core.tmx de-core.html --title "German terms"
```

Find what your memories already say about every source of a catalog: each
exact match in the `<lang>-*.tmx` files of a folder, with the files that hold it,
as JSON and a filterable page:

```sh
localizzy tm lookup app_en.ts memories --langs de,fr
```

Review catalogs in the browser (loopback only). A `.ts` or `.json` catalog in
place of the TOML is imported into a resumable `CATALOG.review/` workspace; the
source file is never edited:

```sh
localizzy review review.toml
```

Validate a vocabulary corpus, the golden set for tests and benchmarks (an
example ships in `examples/vocabulary/`):

```sh
localizzy vocab validate translations.js
```

Edit English wording in Qt Linguist, then apply finished corrections to C++ and
Qt UI sources and matching messages in sibling TS catalogs:

```sh
localizzy source-fix prepare app_en.ts app_en_tofix.ts --root .
```

Preview with `localizzy source-fix apply app_en_tofix.ts app_en.ts --root . --dry-run`;
omit `--dry-run` to apply; add `--rebuild` to refresh catalogs and the mirror
from current sources without finished corrections. Keep the generated `.ts.json` snapshot. Applying needs
Qt `lupdate`; all catalogs and the mirror are rebuilt, and existing foreign
translations are retained and marked unfinished for changed sources.
See [source corrections](src_docs/md/8-toolkit/formats.md#english-source-corrections)
for conflict handling and the plural limitation.

`localizzy inventory ROOT OUT` lists every TMX and TS file. The other `tm` commands (`extract`,
`po2tmx`, `lproj2tmx`, `adobe2tmx`, `oss2tmx`, `norm`, `glossary_json`), `editorial
review|apply`, `diff`, `shard`, `translate_json`, `qt extract|release|applang` and
`project translate|build_ui` are in the [CLI reference](src_docs/md/8-toolkit/cli.md).

## Memories

A **direct memory** is a verbatim cache of reviewed messages: a source matches
only after Unicode NFC and CRLF-to-LF normalization, and a hit is classed by
message id, then context, then source alone. A **glossary memory** is a set of
terms; each engine batch gets only the terms that occur in it, and a message
whose whole text is a term takes the term's rendering. Every hit passes the
placeholder QA gate first. Catalog and memory tags rarely agree (`de_DE` and
`de`, `es_MX` and `es-419`), so the memory language is the exact tag, else the
only or the closest variant; a tie is an error, and `--memory-lang` decides.
Each run writes a provenance sidecar, `OUT.localizzy.json`, with one row per
message. See [memories](src_docs/md/8-toolkit/memories.md).

## Guarantees

- **Byte preservation.** Edited TS catalogs go through a splice writer that
  replaces only the changed `<message>` spans; everything else keeps its bytes.
- **Atomic writes.** Outputs are written to a temporary file and renamed. A
  failed run leaves the previous file in place.
- **Generated text is never finished.** Engine output and weak memory matches
  are written unfinished for review; `--finish-on` names the classes that may be
  written finished.
- **Checked upgrades.** `upgrade` writes nothing unless every FRESH message is
  classified and every APPROVED message is consumed or retired. The report
  records both invariants.

## Python API

| Task | Entry point |
|---|---|
| Translate a catalog | `vexy_localizzy.translate.translate_file` |
| Upgrade a TS catalog | `vexy_localizzy.upgrade.upgrade`, `upgrade_ts` |
| Correct English sources | `vexy_localizzy.sourcefix.prepare`, `apply` |
| Read memories | `vexy_localizzy.memory` (`DirectMemory`, `Glossary`) |
| Load, edit, write catalogs | `vexy_localizzy.formats`, `vexy_localizzy.conversion` |
| Check text and catalogs | `vexy_localizzy.qa` |
| Scan Qt sources | `vexy_localizzy.qt.scan.run` |
| Pseudo-localize | `vexy_localizzy.pseudo.pseudo_catalog` |
| Project configuration | `vexy_localizzy.project.load_config` |
| Review and apply corrections | `vexy_localizzy.editorial` |
| Extract TMX pairs | `vexy_localizzy.extract.single.extract` |
| Voting corpus | `vexy_localizzy.corpus.store.Corpus` |

## Documentation

The book and the package documentation are published as one site at
[fontlab.dev/vexy-localizzy/fl1992mk](https://fontlab.dev/vexy-localizzy/fl1992mk/)
(mirror: [vexy.dev/vexy-localizzy](https://vexy.dev/vexy-localizzy/)).
The source is `src_docs/md`; `docs/` is the build output. The
[toolkit part](https://fontlab.dev/vexy-localizzy/fl1992mk/toolkit/) holds these pages:

- [Getting started](src_docs/md/8-toolkit/getting-started.md): install, extras, a first run.
- [Project file](src_docs/md/8-toolkit/project.md): `localizzy.toml` and the `project` commands.
- [CLI reference](src_docs/md/8-toolkit/cli.md): every command's `--help`.
- [Scanning](src_docs/md/8-toolkit/scanning.md): the Qt source scanner and its rules.
- [Qt tools](src_docs/md/8-toolkit/qt-tools.md): `lupdate`, `lrelease` and launching an app in a UI language.
- [Pseudo-localization](src_docs/md/8-toolkit/pseudo.md): layout testing before translation.
- [Memories](src_docs/md/8-toolkit/memories.md): translate with direct and glossary memories.
- [Upgrade](src_docs/md/8-toolkit/upgrade.md): tiers, element ownership, RETIRED and the report.
- [Formats](src_docs/md/8-toolkit/formats.md): what each catalog adapter keeps and refuses.
- [Translation](src_docs/md/8-toolkit/translation.md): batches, cache, retries and validation.
- [Quality](src_docs/md/8-toolkit/quality.md): the deterministic checks and the optional layers.
- [Editorial review](src_docs/md/8-toolkit/editorial.md): model-proposed corrections, guarded apply, ledgers.
- [Vocabulary](src_docs/md/8-toolkit/vocabulary.md): a golden corpus for tests and benchmarks.
- [CI](src_docs/md/8-toolkit/ci.md): a continuous-localization workflow.
- [Troubleshooting](src_docs/md/8-toolkit/troubleshooting.md): exit codes and common failures.
- [Architecture](src_docs/md/8-toolkit/design/architecture.md): the design tenets and layers.
- [Extraction](src_docs/md/8-toolkit/extraction.md): `tm extract` and the legacy tree converters.
- [Legacy sources](src_docs/md/8-toolkit/legacy-sources.md): source projections for extraction.
- [Review](src_docs/md/8-toolkit/review.md): the browser reviewer.
- [Corpus](src_docs/md/8-toolkit/corpus.md): inventory, weighted votes, import and export.

## Related documentation

- [abersetz](https://code.twardoch.com/abersetz/): the translation engine
  (its [Python API](https://code.twardoch.com/abersetz/api.html) is what
  `vexy_localizzy.translate.abersetz_transport` calls).
- [FontLab writing styleguide](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/):
  the [localization principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/),
  the [memories](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/memories/)
  that this package reads, and the [glossary](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/glossary/).

## Experimental

Research code lives in `vexy_localizzy.experimental` and is outside the supported
CLI: see [classification](src_docs/md/8-toolkit/classification.md),
[distillation](src_docs/md/8-toolkit/distillation.md) and [retrieval](src_docs/md/8-toolkit/retrieval.md).
