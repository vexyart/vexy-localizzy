---
this_file: src_docs/md/1-foundations/101-what-this-part-knows.md
---

# 101. What this part knows

Localization looks like a translation problem from the outside and turns out to be a data problem, a rendering problem, a layout problem and a business decision as soon as you start. This part covers the ground under all of those: the vocabulary of the field, its history, and the facts about text, locales, formats, grammar, scripts, space, culture and cost that every later part assumes. It is written for software engineers who have never localized anything, for localization engineers who want the reasoning behind rules they already follow, and for translators who want to know why a string arrives the way it does.

## Why start here

Most localization defects are not translation errors. A plural that cannot be written, a date in the wrong order, a label cut off by a fixed-width button, an English support page linked from a German dialog: each of these is decided long before a translator opens the file. The published literature has said so since Uren, Howard and Perinotti's introduction of 1993, and the FontLab localization of 2026, whose catalogs and review decisions appear throughout this book, confirmed it string by string. A team that understands the foundations fixes such problems once, in code or in process, instead of once per language.

The part also calibrates the older sources. Nine books from 1993 to 2025 stand behind this one, and some of their advice was a workaround for machines that no longer exist. Where the books and the 2026 research disagree, the chapters say so and show the evidence, so that you can decide which figure applies to your product.

## How the chapters connect

The chapters follow a string from its meaning to its pixels and then to its price.

| Chapter | Question it answers |
|---|---|
| [102](102-what-localization-is.md) | What are globalization, internationalization, localization and translation, and which layer owns a given defect? |
| [103](103-a-short-history.md) | What changed between DOS code pages and continuous delivery, and which old advice is still valid? |
| [104](104-characters-and-encodings.md) | What is a character, which encoding should catalogs use, and why do two identical-looking strings fail to match? |
| [105](105-locales-and-cldr.md) | How are locales named, why does one user have several, and how does a program choose a translation? |
| [106](106-numbers-dates-and-units.md) | How are numbers, dates, money and units displayed for a locale without changing the values behind them? |
| [107](107-plurals-gender-and-message-formats.md) | How do message formats let translators write correct plurals and agreement for every count? |
| [108](108-scripts-direction-and-fonts.md) | What must software do for right-to-left text, shaping scripts and font coverage? |
| [109](109-space-and-growth.md) | How much do translations grow, and how do you build a layout that survives it? |
| [110](110-culture-and-cost.md) | What should be adapted for a market, what does the law require, and what does it cost? |

Chapters 102 and 103 give the frame. Chapters 104 to 106 cover the data layer: characters, locales and formatted values, which the program handles and translators should never retype. Chapters 107 and 108 cover what happens when grammar and writing systems meet code: the message formats that carry plural and gender variants, and the rendering path for scripts unlike Latin. Chapters 109 and 110 bring the translated text back onto the screen and into the budget.

Each chapter ends with a worked example that follows one realistic case through the concepts: a defect report sorted into layers, a Polish word that will not match its memory entry, a user whose interface language and formats differ, a plural tested at twelve, a layout pseudo-localized before translation, a release planned item by item. Several use the Polish localization of FontLab, because its decisions are recorded in detail and because Polish exercises plurals, diacritics and case in ways English never does.

## What this part does not do

It teaches concepts and decisions, not a toolchain. Instrumenting code with Qt's `tr()`, loading translators at run time, mirroring an interface and testing world-readiness belong to Part [2](../2-engineering/201-what-this-part-knows.md). File formats such as TS, PO and XLIFF are in Part [3](../3-formats/301-what-this-part-knows.md). Terminology, memories and glossaries are in Part [4](../4-terminology/401-what-this-part-knows.md), the daily craft of translating interface strings in Part [5](../5-interface/501-what-this-part-knows.md), machine translation in Part [6](../6-machine-translation/601-what-this-part-knows.md), and quality, process and delivery in Part [7](../7-process/701-what-this-part-knows.md). Where a foundation chapter touches one of those subjects, it links forward rather than repeating it.

The vexy-localizzy toolkit appears only where it illustrates a principle, such as how its memory lookup normalizes text before comparing. Everything in this part applies to any software team, whatever tools it uses.

## Sources

- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (chapter 1)
- The sources listed at the end of chapters 102 to 110
