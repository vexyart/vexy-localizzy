---
this_file: src_docs/md/3-formats/308-conversion-tools.md
---

# 308. Conversion tools: lconvert, Translate Toolkit, Okapi and when to write your own

Conversion tools are older than any format in this part. Esselink (2000) describes translation memory tools whose file filters converted proprietary formats into something the memory could read, and lists as a disadvantage that filters were not always updated for new versions of the formats they processed. He also describes a class of software localization tools that edited compiled program files directly, reused translations and hot keys from the previous version, and even carried over dialog resizing. The tools have changed names since then. The trade-off has not: a converter knows a format as well as its authors understood it on the day they wrote it, and everything else becomes loss.

This chapter surveys the tools the research corpus recommends, gives a decision rule for choosing among them, and then takes up the question the sources disagree about: when a team should write its own.

## The standard tools

| Tool | Language and license | What it converts |
|---|---|---|
| Qt `lconvert` | part of Qt Linguist | TS, PO, POT, XLIFF, QM and Qt phrase books |
| Translate Toolkit | Python, GPL | PO to and from TS, XLIFF, Android, JSON, YAML, Java properties, .NET resx, Mozilla DTD, HTML, Markdown and more |
| Okapi Framework | Java, Apache 2.0 | XLIFF 1.2 and 2.0, TMX, many document formats through filters |
| Gettext utilities | C | PO and POT, compiled catalogs |
| `i18next-conv` | Node | i18next JSON to and from PO |
| `xliff` by locize | Node | i18next objects to and from XLIFF 1.2 and 2.0 |
| `polib`, `lxml` | Python libraries | PO, and any XML format by hand |

Each has a reason to exist beyond conversion. The Translate Toolkit's converters mostly end in PO, because its quality checker, `pofilter`, runs more than forty checks on PO files; converting to PO is how other formats get checked. `pot2po` initializes a catalog from a template with fuzzy matching and can replace `msgmerge`. Okapi's tools include Rainbow for batch work, Tikal on the command line, CheckMate for quality checks and Olifant for editing memories, and according to the research the Okapi XLIFF Toolkit, merged into Okapi in late 2024, is the reference implementation of XLIFF 2.0. `lconvert` merges as well as converts: given several input files, it combines them, with translations from later files taking precedence.

Hosted services add another layer. The research lists Localazy, SimpleLocalize, POEditor and Localizely as web converters, and notes that some of them rewrite placeholders between platforms, turning Android's `%1$s` into iOS's `%@`. That convenience is a transformation of the text, and it should appear in the review like any other edit.

## Choosing a tool

The research reduces the choice to a table, and its rules hold up:

| Conversion | Tool |
|---|---|
| TS to or from PO or XLIFF | Qt `lconvert` |
| PO, XLIFF and Android XML in a Python pipeline | Translate Toolkit |
| i18next JSON to or from XLIFF with plurals intact | the locize export |
| XLIFF 2.0 as the canonical handling | Okapi |

The first row carries an exception to the general advice. The research and the fl10n specification both recommend the Translate Toolkit for most conversions, and both carve out Qt: the toolkit's own documentation warns that `po2ts` uses its older TS support and that many newer TS features are not supported. For a Qt catalog, the Qt tool wins.

The rows also imply a direction. The research calls i18next JSON a poor interchange format, because the v3 to v4 migration tool only handles keys with the default `_` separator, and recommends converting into it late in the pipeline. The general principle is to convert toward the richer format early and toward the poorer one at the boundary, so that as few steps as possible run on reduced data.

## When to write your own

Here the sources disagree, and the disagreement is instructive. The research ends its staged rollout plan with a list of things not to do, and the first is "roll your own format converter": use the Translate Toolkit, Okapi or `lconvert`. The fl10n specification follows the advice. Its `convert` command picks `lconvert` whenever a `.ts` file is on either end and the Translate Toolkit otherwise, and passes through to them directly for pairs they round-trip safely.

vexy-localizzy did the opposite. It reads and writes TS, PO, XLIFF, Android, i18next and TMX with its own adapters, keeps the original bytes of every document, and refuses any conversion that loses a field unless the caller acknowledges the loss. Its documentation does not state a motive for the departure, and this book will not invent one. What the record shows is the set of requirements the adapters meet and the existing tools, as the sources describe them, do not:

1. An unchanged round trip must restore the input byte for byte, so that a program can edit a reviewed catalog without rewriting it.
2. Every field a conversion changes or drops must be named in a report, and the output must not be written until the caller accepts the report.
3. Plural forms must never be assigned a category the file does not state.
4. Edits must be confined to the messages that changed.

The same work log shows what the requirements cost. Each adapter went through an independent review that tried to break it, and each review found real defects before the adapter was accepted: two bugs in Android round trips of resources that legally share a name and in whitespace around protected placeholders, a mismatch with empty plural keys in i18next, and eight failing cases in XLIFF, among them segmented target order, inline codes in empty targets and target removal without resetting approval. Every defect became a regression test that failed before its fix and passed after it. None of these would have been found by testing the happy path, and a team writing its own adapters should budget for the same adversarial review.

A team that needs none of these should use the standard tools. A team that needs them should expect to write adapters, and should expect the cost that comes with them: every adapter becomes a parser it must keep correct as the formats evolve.

## Testing a converter

Whether you use a standard tool or write one, test it, and test it on the three losses that the research calls predictable: plural arity, context and placeholders. The sources name four kinds of test.

**Round trips with property-based inputs.** The research recommends generating random placeholder sequences with Hypothesis or fast-check and checking that they survive a trip through the converter. The fl10n specification adopts this for its own conversions, and adds a test file with duplicate sources in different contexts to check that `msgctxt` survives.

**Byte round trips on real catalogs.** vexy-localizzy's work log records them per format: 53,075 messages in eleven PO catalogs, 981 XLIFF messages in 92 file sections, 771 messages in three nested JSON catalogs and 533 TMX units in three native catalogs, each restored exactly after a trip through canonical JSON.

**Validation against the format's own authority.** Output XLIFF was validated against the official OASIS schemas, fresh TMX against a TMX 1.4 DTD, Android output against native AAPT2 compilation in four cases, and i18next behavior against the published i18next 26.3.6 in thirteen runtime comparisons. The work log is careful to call the Android check synthetic validation, not device coverage.

**Golden files for legacy behavior.** When vexy-localizzy took over fl10n's older memory extractors, it captured their output on synthetic inputs and required byte-identical results from the ports.

## Worked example: auditing lconvert on one file

A converter audit does not need a large corpus to be useful. The German fixture from [chapter 302](302-qt-ts.md) has eleven messages, including a duplicate, an unfinished, an obsolete, a vanished and an empty translation, and two plural messages, one with a missing form. Converting it to PO and back with Qt's tool takes two commands:

```sh
lconvert -if ts -of po app_de.ts -o app_de.po
lconvert -if po -of ts app_de.po -o app_de.back.ts
diff app_de.ts app_de.back.ts
```

Run with `lconvert` from Qt tools 6.11 for this chapter, the audit gave these results:

| Behavior | Result |
|---|---|
| Qt context in PO | written as `msgctxt`, the context name followed by a bar and the disambiguation |
| Unfinished translation | written as `#, fuzzy` |
| Obsolete and vanished messages | written as `#~` entries and restored |
| Plural messages | flagged `qt-format`; `Plural-Forms` written from the `language` attribute |
| Duplicate message | dropped with a warning |
| Empty finished translation | returned as `type="unfinished"` |
| One-form plural | returned with a second, empty `<numerusform>` |

Three of the seven are changes, and all three are defensible: a duplicate message cannot be looked up twice, an empty translation was never finished, and German needs two plural forms. They are also exactly the kind of change that makes a review diff larger than the edit, and the kind that a pipeline should know about before it runs the conversion on ten thousand messages. The audit took two commands and a `diff`. Run it for every tool and version you adopt, and keep the fixture in your repository so that the next upgrade of the tool gets the same test.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapters 4 and 11)
- `research/05-format-conversion-cicd-and-continuous-localization.md` in the fl10n repository
- `research-draft/317-cla.md` in the fl10n repository
- `spec/03.md` in the fl10n repository
- [docs/formats.md](../8-toolkit/formats.md), [docs/extraction.md](../8-toolkit/extraction.md), `WORK.md` and `tests/fixtures/legacy_golden/inputs/ts/app_de.ts` in the vexy-localizzy repository
- `lconvert -help` and a local round trip with `lconvert` from Qt tools 6.11.2, recorded for this chapter
