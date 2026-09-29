---
this_file: src_docs/md/3-formats/301-what-this-part-knows.md
---

# 301. What this part knows

Every localized string spends most of its life in a file. A developer marks it in code, an extractor writes it into a catalog, a translator or an engine fills the catalog, a converter moves it into a tool that someone else prefers, and a compiler turns it into something the application loads at run time. At each step the string travels with its context, its placeholders, its plural forms and its review state, or it travels without them. Which of those happens depends almost entirely on the file format and on the program that reads and writes it.

This part is about those files. It treats them as data models, not as syntax to memorize. Each format answers the same questions in its own way: how is a message identified, where does the context go, how are plural forms stored, what states can a translation be in, and what happens to everything the format does not understand. Once you can ask those questions of any file, you can predict where a conversion will lose information before it does.

## Why formats deserve a part of their own

The research corpus behind this book reaches one conclusion more often than any other about formats: the models are not isomorphic, so a universal lossless converter does not exist. The losses are predictable. Plural arity is the most common silent failure, when a format with six Arabic forms is flattened into one that holds two. Context goes next, when a Qt comment or a gettext `msgctxt` has nowhere to land. Placeholders follow, when `%1` has to become `{0}` or `%1$s` on the way into another runtime. None of these failures raises an error. They surface weeks later as a wrong word on a screen.

The older literature saw the same risk from another side. Esselink (2000) warned that editing a Windows resource file in a plain text editor made it easy to damage the code around the strings, and that different resource editors could restructure the file. The tools changed; the lesson did not. A localization file is shared between people who read it and programs that parse it, and a careless write can break either.

## How the chapters connect

The part moves from single formats to the operations that cross them.

| Chapter | Question it answers |
|---|---|
| [302](302-qt-ts.md) | What a Qt `.ts` file stores, and what `lupdate` rewrites |
| [303](303-gettext-po.md) | How gettext PO carries context, plurals and fuzzy state |
| [304](304-xliff.md) | Why XLIFF 1.2 and 2.x are two formats that share a name |
| [305](305-json-android-apple.md) | How application formats differ from bilingual catalogs |
| [306](306-tmx-and-tbx.md) | How memories and terminology are exchanged |
| [307](307-the-canonical-model.md) | What one typed representation must hold, and what it must refuse |
| [308](308-conversion-tools.md) | Which converter to use, and when to write your own |
| [309](309-byte-preserving-edits.md) | How to edit a catalog so that the diff shows only the edit |
| [310](310-identity-and-upgrade.md) | How a message is recognized across versions, and what happens to retired strings |

Chapters 302 to 306 are reference chapters with a decision in each: which fields to preserve, which tool to trust, which trap to test for. Chapter 307 turns the comparison into a design, a canonical model with explicit fields for context, plurals, placeholders and state, plus a record of every loss a conversion accepts. Chapters 308 to 310 are about operations: converting, editing and upgrading catalogs without losing reviewed work.

## What the part assumes

You should know why strings are externalized and what a message key is; [Part 2](../2-engineering/203-externalizing-strings.md) covers that. You should know what CLDR plural categories are; [chapter 107](../1-foundations/107-plurals-gender-and-message-formats.md) covers that. Qt instrumentation and the `lupdate` and `lrelease` toolchain belong to [chapters 205](../2-engineering/205-qt-instrumentation.md) and [206](../2-engineering/206-qt-toolchain-and-runtime.md); this part picks up where the `.ts` file is written. How memories and glossaries are organized is the subject of [Part 4](../4-terminology/405-core-and-project-memories.md); this part describes only the files that carry them.

## Where the examples come from

The examples come from two projects. `fl10n` is the engineering specification and toolchain for the FontLab localization, whose catalogs hold about ten thousand five hundred messages per language in German, Spanish, French and Polish. `vexy-localizzy` is the Python toolkit that grew out of it: format adapters for TS, PO, XLIFF, Android, i18next and TMX, a canonical JSON catalog, a splice writer that edits `.ts` files without rewriting them, and an upgrade command that ports reviewed translations onto a fresh catalog. Where the specification and the toolkit made different decisions, the chapters say so, because the difference is usually the lesson.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapters 3 and 4)
- `research/05-format-conversion-cicd-and-continuous-localization.md` in the fl10n repository
- `spec/03.md` in the fl10n repository
- `README.md`, [docs/formats.md](../8-toolkit/formats.md) and [docs/upgrade.md](../8-toolkit/upgrade.md) in the vexy-localizzy repository
