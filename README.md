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
│ your project (for example fl10n)                                     │
│   config, catalog and memory folders, per-language tags, wrappers    │
└───────────────▲──────────────────────────────────────────────────────┘
                │ Python API + `localizzy` CLI
┌───────────────┴──────────────────────────────────────────────────────┐
│ vexy-localizzy  (localization software)                              │
│   formats/  catalog I/O (TS splice writer, PO, XLIFF, TMX, Android…) │
│   memory/   TMX read/write, direct memory, glossary, build-ui        │
│   translate/ batches · cache · QA gate · memory-aware orchestration  │
│   upgrade/  TS upgrade (exact/relocated/fuzzy/memory/engine/retired) │
│   extract/  foreign sources → TMX (ts/po/lproj/adobe/oss, tm norm)   │
│   qa/ · review/ · corpus/ · experimental/                            │
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
| `llm` | openai, filelock | experimental classifiers and distillers |
| `embeddings` | numpy, uubed | experimental embedding cache and retrieval |
| `clustering` | numpy, scikit-learn | experimental clustering |

Development: `uv sync --group dev --extra translation --extra sources --extra review`,
then `./test.sh` (it also needs `npm --prefix review ci` and `npm --prefix icu ci`).

## Commands

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

Build a project memory from a finished catalog, leaving out whole glossary terms:

```sh
localizzy tm build-ui de.ts de-ui.tmx --exclude-memory de-core.tmx
```

Turn a tree of Qt catalogs into TMX with the legacy language policy:

```sh
localizzy tm ts2tmx translations/ --output tmx/
```

Export a core TMX memory as a Qt Linguist phrase book:

```sh
localizzy tm tmx2qph de-core.tmx fontlab_de.qph --target de
```

This preserves every source/target pair, including proposed and identical
translations. Definitions contain the review status and all unit/segment notes;
Qt does not enforce review status. Use the exact TMX target tag (for example
`--target es-419`). Missing, empty, duplicate or inline-marked segments fail
without replacing the output. Other TMX properties are not exported.

Review catalogs in the browser (loopback only):

```sh
localizzy review review.toml
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

`localizzy qa CATALOG` runs the deterministic checks and `localizzy inventory
ROOT OUT` lists every TMX and TS file. The other `tm` commands (`extract`,
`po2tmx`, `lproj2tmx`, `adobe2tmx`, `oss2tmx`, `norm`) are in the
[CLI reference](src_docs/md/8-toolkit/cli.md).

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
| Extract TMX pairs | `vexy_localizzy.extract.single.extract` |
| Voting corpus | `vexy_localizzy.corpus.store.Corpus` |

## Documentation

The book and the package documentation are published as one site at
[fontlab.dev/vexy-localizzy/fl1992mk](https://fontlab.dev/vexy-localizzy/fl1992mk/)
(mirror: [vexy.dev/vexy-localizzy/fl1992mk](https://vexy.dev/vexy-localizzy/fl1992mk/)).
The source is `src_docs/md`; `docs/fl1992mk` is the build output. The
[toolkit part](https://fontlab.dev/vexy-localizzy/fl1992mk/toolkit/) holds these pages:

- [CLI reference](src_docs/md/8-toolkit/cli.md): every command's `--help`.
- [Memories](src_docs/md/8-toolkit/memories.md): translate with direct and glossary memories.
- [Upgrade](src_docs/md/8-toolkit/upgrade.md): tiers, element ownership, RETIRED and the report.
- [Formats](src_docs/md/8-toolkit/formats.md): what each catalog adapter keeps and refuses.
- [Translation](src_docs/md/8-toolkit/translation.md): batches, cache, retries and validation.
- [Quality](src_docs/md/8-toolkit/quality.md): the deterministic QA checks.
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
