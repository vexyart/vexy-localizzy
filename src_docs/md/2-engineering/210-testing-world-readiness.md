---
this_file: src_docs/md/2-engineering/210-testing-world-readiness.md
---

# 210. Testing world-readiness: pseudo-localization, locale switching and mixed data

Internationalization defects are cheap to fix and expensive to find late. A hard-coded string, a concatenated sentence or a buffer sized for English costs minutes to repair in the source and a great deal more once it has been found in twenty translated builds. The tests in this chapter find those defects before any translator is involved: a pseudo-localized build that simulates translation, a set of locale settings and data that stress the code, and a record that lets a defect be reproduced and a fix be confirmed. Testing the finished translations belongs to the process part of this book ([706](../7-process/706-pseudo-localization-and-layout.md) and [704](../7-process/704-the-qa-gate.md)); review in the running application is [510](../5-interface/510-review-in-the-running-app.md).

## Three questions, three kinds of test

Dr International (2002) separates three questions that are easy to blur. Globalization testing asks whether the program works in every supported locale with any supported data, whatever its interface language. Localizability testing asks whether the program can be translated without code changes. Localization testing asks whether a particular translated build is correct. The first two need no translation at all and can run from the first build of a feature; the book argues that a team which runs them in parallel with functional testing reduces localization testing to checking translated text, grammar and spelling.

For localizability, the book lists four instruments: pseudo-localization, a code review against a checklist, a review of terminology in the interface and documentation, and a pilot translation into one language chosen because it is likely to expose problems. It suggests German as a pilot: its words run long, as *ausschneiden* does for "cut", and on the Windows of the time its two code pages differed. It adds that pseudo-localization covers more risk than any single pilot language.

The code review checklist translates directly into automated checks. It asks for resources separated from code, no string length assumptions, no run-time composition of strings, no run-time positioning of controls, no text in icons and bitmaps, and no assumed names for folders, accounts or registry keys. The fl10n source audit covers the first three for Qt code ([205](205-qt-instrumentation.md)), and `lrelease -markuntranslated <prefix>` builds a test catalog in which every untranslated string carries a visible prefix.

## Pseudo-localization

Dr International defines pseudo-localization as an automated simulation of the localization process, followed by building and testing the simulated localized version, and gives the reason to do it first:

> "Pseudo-localization gives you a translation without the cost of an actual localization." (Dr International 2002)

The book's list of features has not been improved on:

- **Character replacement.** Replace Latin letters with look-alikes from other alphabets or with accented forms. Any plain English left in the interface is hard-coded, outside the extracted resources or in a format the tools do not read. Non-Latin characters that turn into question marks or boxes show encoding and font defects.
- **Length extension with delimiters.** Pad each string and mark its start and end. Truncated padding shows missing space; the delimiters show where strings were joined at run time.
- **Dialog stretching.** Enlarge dialog templates to find sizes fixed in code.
- **Shortcut replacement.** Change mnemonics and shortcut keys to find the ones assembled or hard-coded outside the catalog.

The delimiters repay a closer look, because they turn a screenshot into a diagnosis. Dr International's example reads a line of pseudo-localized output like this:

```
{string1{string2}} string3 {string4
```

`string2` sits inside `string1`, so the program inserted one resource into another at run time. `string3` has no delimiters, so it never came from a pseudo-localized resource: it is hard-coded or loaded from somewhere the tools do not reach. `string4` has an opening delimiter and no closing one, so it was truncated. One line shows three separate defects, each assigned to a different cause.

The book's list of defects that pseudo-localization reveals is a useful checklist in its own right: resources not exposed to localization, hard-coded text, strings that should never have been translatable (such as the name of an object shared between two programs), non-Latin characters that break processing, overflows from longer text, dependent strings translated inconsistently (such as a folder name used in two places), features that cannot be adapted, interfaces that do not mirror, and strings composed at run time.

## How much to expand, and what must not change

The padding ratio is a guess about translated length, and the sources guess differently. The disagreement is real, not a matter of rounding, because the figures describe different things: some describe average text, some short labels, some a specific language.

| Source | Figure |
|---|---|
| Dr International 2002 | About 30 percent extra room in general; for strings under 10 characters, at least 400 percent |
| O'Donnell 1994 | French and German text averages 10 to 30 percent longer than English |
| fl10n research corpus, 2026 | Most European languages expand 30 to 50 percent from English |
| fl10n `pseudo` command documentation | German typically 20 to 30 percent longer, Finnish up to 60 percent |
| fl10n research and specification | Pseudo-localization padding of about 40 percent |
| Baldurs 2025 | An expansion factor of 1.3 |

The short-string row matters most for an interface. "OK" becoming Spanish *Aceptar* is Dr International's example of a label that grows far beyond 30 percent; a padding rule proportional to length under-tests exactly the buttons that clip first. [109](../1-foundations/109-space-and-growth.md) discusses expansion as a design constraint.

Whatever the ratio, the transformation must leave syntax alone. Placeholders, markup, escape sequences and ICU keywords are code. A pseudo-localizer that accents them produces a catalog that fails for the wrong reason: Baldurs's example implementation replaces every letter, so `{{name}}` and the keyword `plural` would be altered along with the text. The fl10n pseudo-localizer splits each string on a pattern that protects Qt markers such as `%1` and `%n`, brace placeholders, i18next `{{name}}`, ICU arguments, `printf` positional markers and tags, and transforms only the text between them. The pattern is only as good as its list: in the version run for this chapter it did not recognize Qt's locale-aware markers, so `Total: %L1` came out with `%Ł1` in it. Test your pseudo-localizer with every marker your parser accepts before trusting its output. Its output is an ordinary catalog in the pseudo-locale `xx-pseudo`, which compiles and loads like any language.

The fl10n documentation disagrees with itself about two details, and the code settles both. The specification says the `rtl` mode injects right-to-left marks; one documentation page says it reverses character order, and another that it reverses text direction. The implementation in `src/fl10n/engines/pseudo.py` leaves the text unchanged and wraps each string in right-to-left embedding marks. The command reference gives the default padding as 0.3, while both the command-line entry point and the engine default to 0.4. Pass `--expansion` explicitly in scripts that depend on it.

Pseudo-localization has limits that the FontLab runtime review states plainly: it reveals text that escaped extraction, clipped labels and missing character support, but not natural wording, agreement or terminology. An unchanged value in the pseudo build may also be correct, because user data, technical identifiers and third-party components are not supposed to change; trace each one before counting it as a missed string.

## Locale switching and mixed data

Globalization tests change the environment, not the strings. Dr International's list of settings is a good start: an East Asian system locale for multibyte handling; Turkish for case mapping, because dotless *ı* and dotted *İ* break any code that uppercases by rule; locales with unusual separators, such as a period as the time separator; non-Gregorian calendars; a user locale different from the system locale; and data saved under one locale and opened under another. Its test data mixes scripts in one field, including scripts that exist only in Unicode, and includes text in scripts without case.

The FontLab runtime review turns this into a record. Before testing, write down the interface language, the formatting locale, the input method, the document language, the time zone, the currency and the expected fallback, because an English interface can run with Polish number formatting and a French reader can see a price in US dollars. Then follow values through tasks rather than looking at labels:

| Case | What to keep as evidence |
|---|---|
| Interface language differs from formatting locale | The settings, the language of the labels and a formatted value |
| Fractional or negative measurement entered as `1,25` | The entered string, the interpreted quantity and the value after reopening |
| One currency shown in two locales | The unchanged amount and currency in both views |
| An event near midnight or a clock change | The instant, the target zone and the displayed date and time |
| Multilingual file name and document round trip | The original text, the formats used and the reopened result |
| Missing message or missing locale | The key, the fallback sequence and the text actually shown |
| Language changed during a task | An open dialog, a validation error, help and restart behavior |
| Sort and search with *ä*, *ß*, *ł*, *ż*, *ñ* and Turkish *i* | The comparison rule and the actual order or matches |

Two instructions from the review make these tests trustworthy. Record the expected result before running each case, so the observation cannot redefine success. And after a fix, repeat the original case: a new screenshot of a label does not prove that a numeric or fallback defect is gone. To isolate a catalog-dependent failure, change entries in a disposable test build while keeping placeholders and catalog syntax valid, and keep an unchanged control build, because an invalid test catalog introduces a new failure and cannot explain the old one.

## Sources

- Dr International, *Developing International Software*, second edition, 2002 (chapter 7, text expansion; chapter 11, testing for world-readiness; chapter 12, pseudo-localization)
- Sandra Martin O'Donnell, *Programming for the World: A Guide to Internationalization*, 1994 (chapter 9, text expansion and buffers)
- Baldurs L., *TypeScript Internationalization (i18n) and Localization (L10n)*, 2025 (chapter 14, pseudo-localization)
- `research/01-foundations-of-software-localization.md` and `research/04-ai-driven-translation-and-quality-assurance.md` in the fl10n repository
- `spec/05.md`, `docs/commands/pseudo.md`, `docs/getting-started.md`, `src/fl10n/cli.py` and `src/fl10n/engines/pseudo.py` in the fl10n repository
- `lrelease -help` output, Qt Linguist tools 6.11.2
- `src_docs/md/localization/runtime-review.md` in the vexy-fontlab-writing-styleguide repository
