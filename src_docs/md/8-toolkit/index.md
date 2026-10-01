---
this_file: src_docs/md/8-toolkit/index.md
---

# Part 8. The toolkit

The reference documentation of the vexy-localizzy package: what each command
and module does, what it keeps, what it refuses and what it writes. The seven
parts before this one explain why the toolkit works the way it does; these
pages say what it does, in the order a user meets it. The source is on
[GitHub](https://github.com/vexyart/vexy-localizzy) and the package is on
[PyPI](https://pypi.org/project/vexy-localizzy/).

## Pages

Start here:

- [Getting started](getting-started.md): install, extras, `doctor` and a first run on a small Qt project.
- [Project configuration](project.md): `localizzy.toml`, `init` and the `project` commands.
- [Command-line reference](cli.md): every command's `--help`, generated from the code.

Qt source and catalogs:

- [Scanning Qt source](scanning.md): the `qt scan` rules, engines, coverage and SARIF.
- [Qt extraction, release and launch](qt-tools.md): `qt extract`, `qt release` and `qt applang`.
- [Pseudo-localization](pseudo.md): the three modes and what they never touch.
- [Upgrading a Qt catalog](upgrade.md): the ten tiers, element ownership, RETIRED, the report and `diff`.
- [Catalog formats](formats.md): what each adapter keeps and refuses.

Translation and quality:

- [Translating with memories](memories.md): direct and glossary memories, match classes, the QA gate, the provenance sidecar, glossary JSON and lookups.
- [Translation batches and cache](translation.md): batches, cache keys, retries, validation and shards.
- [Translating JSON text files](json-files.md): `translate_json` for help and tips files.
- [Translation content QA](quality.md): the deterministic checks and the optional layers.
- [Browser catalog review](review.md): the reviewer, its workspace, store and journal.
- [Editorial review](editorial.md): model-proposed corrections, guarded and recorded.
- [Vocabulary corpus](vocabulary.md): a golden set for fixtures and benchmarks.

Running it:

- [Continuous localization](ci.md): a GitHub Actions gate and a nightly judge.
- [Troubleshooting](troubleshooting.md): exit codes and common errors.

Memories and sources:

- [Extract translation-memory pairs](extraction.md): `tm extract` and the legacy tree converters.
- [Legacy source projections](legacy-sources.md): how foreign resource formats are read.
- [Voting corpus](corpus.md): inventory, weighted votes, import and export.
- Experimental: [classification](classification.md), [distillation](distillation.md) and [retrieval](retrieval.md).

Design:

- [Toolkit architecture](design/architecture.md): tenets, the canonical model, the pipeline and exit codes.
- Reviewer design: the [design contract](design/review.md) and the [visual verification](design/review-fidelity.md).

## Where the toolkit sits

vexy-localizzy owns catalogs, memories, upgrades, QA and review. Two other
projects complete the picture:

- [abersetz](https://code.twardoch.com/abersetz/) is the translation engine.
  Text goes in, text comes out, through pluggable engines and providers with
  chunking and vocabulary hints. The toolkit calls its
  [Python API](https://code.twardoch.com/abersetz/api.html) and never parses a
  catalog through it; [installation](https://code.twardoch.com/abersetz/installation.html)
  and [configuration](https://code.twardoch.com/abersetz/configuration.html)
  of the engines are documented there.
- The [FontLab writing styleguide](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/)
  is the project layer's source of truth for words. Its
  [localization principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/)
  set the rules that [Part 4](../4-terminology/index.md) and
  [Part 5](../5-interface/index.md) generalize, its
  [memories](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/memories/)
  are the TMX files that `--direct-memory` and `--glossary-memory` read, its
  [glossary](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/glossary/)
  defines every term with its fallback original term, and its
  [language guides](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/)
  for German, Spanish, French and Polish record the decisions behind the
  worked examples in this book.
