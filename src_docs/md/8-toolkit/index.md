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

- [Command-line reference](cli.md): every command's `--help`, generated from the code.
- [Translating with memories](memories.md): direct and glossary memories, match classes, the QA gate and the provenance sidecar.
- [Upgrading a Qt catalog](upgrade.md): the ten tiers, element ownership, RETIRED and the report.
- [Catalog formats](formats.md): what each adapter keeps and refuses.
- [Translation batches and cache](translation.md): batches, cache keys, retries and validation.
- [Translation content QA](quality.md): the deterministic checks.
- [Extract translation-memory pairs](extraction.md): `tm extract` and the legacy tree converters.
- [Legacy source projections](legacy-sources.md): how foreign resource formats are read.
- [Browser catalog review](review.md): the reviewer, its store and its journal.
- [Voting corpus](corpus.md): inventory, weighted votes, import and export.
- Experimental: [classification](classification.md), [distillation](distillation.md) and [retrieval](retrieval.md).
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
