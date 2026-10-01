---
this_file: src_docs/md/index.md
---

# Localization

A book in seven parts on making software speak other languages: what a locale
is, how a program is prepared for translation, which files carry the words,
how terms are chosen and remembered, how an interface is translated well, what
a translation engine can and cannot do, and how the whole thing ships without
regressing. It condenses nine published books on internationalization and
localization written between 1993 and 2025, a 2026 research corpus on Qt, web
and model-driven localization, the engineering design of the
toolkit, and the practice of the FontLab localization into German, Spanish,
French and Polish. The book documents the reasoning behind
[vexy-localizzy](https://github.com/vexyart/vexy-localizzy), the localization
toolkit that grew out of that work, but it is written for any team that ships
text.

## The seven parts, and the toolkit

1. **[Foundations](1-foundations/index.md).** Locales, encodings, formats,
   plurals, scripts, space and cost: the facts every other part assumes.
2. **[Engineering](2-engineering/index.md).** Preparing code for translation:
   externalized strings, placeholders, the Qt and web toolchains, mirroring,
   rendering and world-readiness tests.
3. **[Formats](3-formats/index.md).** Qt TS, gettext PO, XLIFF, JSON, Android,
   Apple, TMX and TBX; the canonical model, conversion, byte-preserving edits
   and message identity across versions.
4. **[Terminology](4-terminology/index.md).** Glossaries, the fallback original
   term, core and project memories, evidence-based term choice, the house voice
   across languages, word formation and the ledger.
5. **[Interface](5-interface/index.md).** Translating compact strings: headline
   style, no added detail, mnemonics and keys, plurals, placeholders, registers,
   source defects and review in the running application.
6. **[Machine translation](6-machine-translation/index.md).** From rule-based
   systems to language models; context, memory-first pipelines, glossary
   enforcement, the placeholder protocol, routing and cost, quality estimation,
   post-editing and trust.
7. **[Process](7-process/index.md).** Continuous localization, branches, the
   quality gate, linguistic quality assurance, pseudo-localization, review tools,
   vendors, content beyond the catalog, release and provenance.

8. **[The toolkit](8-toolkit/index.md).** The reference documentation of the
   vexy-localizzy package: commands, memories, upgrades, formats, QA, extraction,
   review and the corpus.

Each part opens with a short chapter on what it covers and how its chapters
connect. Chapters end with the sources they drew on.

## Companion sites

- **[FontLab writing styleguide](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/).**
  The house rules the worked examples come from: the
  [localization principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/),
  the [translation memories](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/memories/),
  the [glossary](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/glossary/) and the
  [language guides](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/)
  for German, Spanish, French and Polish. Chapters cite its pages directly.
- **[abersetz](https://code.twardoch.com/abersetz/).** The translation engine
  underneath vexy-localizzy: engines, providers, chunking and vocabulary
  hints, with its own [CLI](https://code.twardoch.com/abersetz/cli.html) and
  [Python API](https://code.twardoch.com/abersetz/api.html).
- **[vexy-localizzy on GitHub](https://github.com/vexyart/vexy-localizzy).**
  Source, issues and releases of the package this site documents.
