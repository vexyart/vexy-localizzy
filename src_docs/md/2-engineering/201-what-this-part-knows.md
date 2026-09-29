---
this_file: src_docs/md/2-engineering/201-what-this-part-knows.md
---

# 201. What this part knows

Part 1 described the facts a localized program has to respect: locales, encodings, plural rules, scripts, text direction and the space translated text needs. This part is about the code that respects them. It is written for the engineer who owns a code base that will be translated, and for the localization engineer who has to explain to that engineer why a translation that exists does not appear on screen. Its subject is internationalization in the narrow, practical sense: the changes to design, source code, build and tests that make translation possible without further changes to the code.

## The argument in one paragraph

The oldest books in this field and the newest research agree on the central point. O'Donnell wrote in 1994 that localizing software replaces one set of hard-coded rules with another, and that the better approach removes the hard-coded rules. The Microsoft team behind *Developing International Software* made the same argument in 2002 as a single world-ready binary for every language. The 2026 research corpus behind this book states it as a short list of principles: extract every user-facing string, mark it with a literal, never concatenate fragments, give translators context, delegate plurals and formatting to engines built on CLDR, and treat translations as code. Everything in this part elaborates one of those principles, shows where it breaks in practice, and shows how to catch the break before a user does.

## How the chapters connect

The chapters follow the order in which the work is done.

- **Design.** [202](202-world-ready-design.md) explains what a first-language program assumes, why the four kinds of resource (interface, adaptation, debug and functional) must be kept apart, and how to replace compile-time language decisions with runtime data.
- **Messages.** [203](203-externalizing-strings.md) covers the message-key model: what identifies a message, why one English word may need several messages, and how context reaches the translator. [204](204-placeholders-and-grammar.md) covers what happens when a message contains a value: numbered and named placeholders, agreement, and the assembly that still breaks the no-concatenation rule.
- **Toolchains.** [205](205-qt-instrumentation.md) and [206](206-qt-toolchain-and-runtime.md) take Qt, the framework of the FontLab applications, from `tr()` and its macros through `lupdate`, `lrelease` and `QTranslator` to switching languages while the program runs. [207](207-web-and-typescript.md) covers the web: the `Intl` API, the choice of message library, typed keys and delivering catalogs.
- **Presentation.** [208](208-mirroring-and-rtl.md) covers right-to-left layouts, what flips and what must not, and mixed-direction text. [209](209-rendering-and-opentype.md) covers the path from characters to glyphs: shaping, OpenType layout, font fallback and the defects they cause.
- **Verification.** [210](210-testing-world-readiness.md) covers the tests that need no translation: pseudo-localization, locale settings and mixed data, and a record that makes defects reproducible.

## What this part does not cover

Catalog formats get their own part: what a Qt `.ts` file contains, what `lupdate` rewrites and how message identity survives an upgrade are in [part 3](../3-formats/302-qt-ts.md). The translator's side of placeholders, plurals, mnemonics and review in the running application is in [part 5](../5-interface/504-mnemonics-shortcuts-and-keys.md). The continuous pipeline that runs these tests on every change, and the quality gate for finished translations, are in [part 7](../7-process/702-continuous-localization.md).

## How to read the sources here

Three kinds of evidence meet in this part, and they age differently. The 1994 and 2002 books are historical. Their examples use X/Open message catalogs, 8-bit code pages and Win32 resource files, and the chapters say so; what they teach about separating text from code, about fragments and about fonts has not changed. The 2015 and 2025 books add the translator's view and the TypeScript view; where the 2025 book contains mistakes, such as hand-written plural rules or an `Intl.MessageFormat` that does not exist, the chapters point them out rather than repeat them. The research corpus and the fl10n specification are the modern layer. Their figures, such as bundle sizes and text expansion ratios, often disagree, and the chapters report the ranges instead of choosing one number.

The toolkit appears where it is the clearest example. The fl10n `scan` command audits Qt source for the mistakes described in [205](205-qt-instrumentation.md); its `pseudo` command produces the pseudo-localized catalogs of [210](210-testing-world-readiness.md); and Localizzy's `upgrade` command ports reviewed translations onto a fresh `lupdate` catalog without losing them silently ([206](206-qt-toolchain-and-runtime.md)). The FontLab writing guide supplies the reviewer's side: which strings are not text, what a message contract should say, and how to review a working interface. None of these tools is required to follow the advice. Any team that ships text can apply the same checks with its own tools.

## Sources

- Sandra Martin O'Donnell, *Programming for the World: A Guide to Internationalization*, 1994 (chapter 3)
- Dr International, *Developing International Software*, second edition, 2002 (chapter 2)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (chapters 2 and 3)
- Baldurs L., *TypeScript Internationalization (i18n) and Localization (L10n)*, 2025
- `research/01-foundations-of-software-localization.md` in the fl10n repository
- `spec/02.md` and `spec/05.md` in the fl10n repository
- `README.md` in the vexy-localizzy repository
