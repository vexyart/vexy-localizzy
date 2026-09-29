---
this_file: src_docs/md/1-foundations/102-what-localization-is.md
---

# 102. What localization is: GILT, locale, and the difference between translating and adapting

Every team that ships software in more than one language eventually argues about words. One person says "translation" and means the German file. Another says "localization" and means the German file, the date format, the width of the Save button and the support address in the footer. A third says "internationalization" and means a ticket that nobody has scheduled. The argument is not pedantry. Each word names a different kind of work, done by different people at a different time, and a problem assigned to the wrong kind of work is usually fixed at the wrong cost.

This chapter sets out the vocabulary the rest of the book uses, shows where the published definitions agree and where they do not, and ends with a way to sort a real defect into the layer that owns it.

## Four words and one cycle

The industry groups the work under the acronym GILT: globalization, internationalization, localization and translation. The numeronyms come from counting letters: i18n has eighteen letters between the *i* and the *n*, l10n has ten, g11n has eleven. Jiménez-Crespo (2024) presents GILT as a cycle rather than a sequence, because what translators discover feeds back into how the product is built.

| Layer | What it covers | Who usually does it | How often |
|---|---|---|---|
| Globalization | Business decisions: which markets, which languages, support and distribution in each | Management, product, marketing | Before and after each release |
| Internationalization | Making the product able to handle any language and convention without redesign | Developers | Once per feature, done well |
| Localization | Adapting the product for one locale: text, formats, layout, graphics, testing | Localization engineers, translators, testers | Once per locale per release |
| Translation | Rendering the text itself in another language | Translators, increasingly with machine drafts | Every changed string |

The Localisation Industry Standards Association (LISA), now defunct but still the most quoted source of these definitions, described internationalization as generalizing a product "so that it can handle multiple languages and cultural conventions without the need for re-design", as quoted by Esselink (2000). Its definition of localization is the one most textbooks still cite: making a product "linguistically and culturally appropriate to the target locale (country/region and language) where it will be used and sold", as Jiménez-Crespo (2024) quotes it from LISA (2003).

Globalization is the loosest of the four. LISA meant the business side: restructuring a company so that it can sell, support and bill in many languages. Jiménez-Crespo's example is practical. If the Japanese version of an app says "contact us at this address", somebody has to be able to answer the email in Japanese. That somebody is a globalization decision, not a translation.

## Where the definitions disagree

The terms are stable enough to use, but two published traditions use them differently, and a reader who moves between books needs to know it.

Microsoft's *Developing International Software* (Dr International, 2002) splits the work into two facets. *World-readiness* covers design and code, and it has two parts: *globalization*, which is building a program core that handles the input, display and output of many scripts and locale data, and *localizability*, which is designing the code and resources so that the program can be localized with no change to its source code. *Localization* is the translation and customization for one market. In this vocabulary, globalization is an engineering term. In LISA's vocabulary, as Esselink (2000) and Jiménez-Crespo (2024) present it, globalization is a business term and the engineering is called internationalization.

The disagreement is harmless once you see it, and it explains why a Windows API page from the 2000s talks about "globalization" where a web framework's page from the 2020s talks about "i18n". This book follows the LISA usage and uses *world-ready* for a product that has been properly internationalized.

The second disagreement is about what makes localization different from translation. The industry definitions of the late 1990s and 2000s treated localization as translation plus extra processes: engineering, testing, desktop publishing, project management. Esselink (2000) states it directly: translation is one activity among many in a localization project. Jiménez-Crespo (2024) calls this the "translation plus" metaphor and questions it. Cultural adaptation, Jiménez-Crespo argues, has always been part of translation: subtitlers adapt jokes, advertising translators rebuild slogans. What is specific to localization is the digital, interactive nature of the material, the technology and processes built around it, and the size of the teams. The practical difference for an engineer is small. The practical difference for a translator is large: a translator who believes adaptation is someone else's job will translate the joke literally.

## Locale is not language

The word localization comes from *locale*. Esselink (2000) defines a locale as a combination of language, region and character encoding, and gives the canonical example: French in Canada is a different locale from French in France. Dr International (2002) widens the definition to the whole user environment: sort order, keyboard layout, date, time, number and currency formats, paper and envelope sizes, input methods and text direction. The same book makes an observation that still holds: Windows locales said more about cultural conventions than about languages.

That observation is the one to keep. A locale says as much about how a date is written as about which words appear on the button. Two consequences follow.

First, one language can need several locales. Spanish in Spain and Spanish in Mexico share most interface text but differ in vocabulary, number formatting and currency. Serbian can be written in Cyrillic or Latin script, and the locale identifier records which: `sr-Cyrl` and `sr-Latn` are separate targets. Jiménez-Crespo (2024) lists further pairs, such as Uzbek in three scripts and Chinese in Simplified and Traditional characters.

Second, the language a user reads and the conventions a user expects can differ. An engineer in Zurich may run an English interface and still expect `31.12.2026` and Swiss francs. Chapter [105](105-locales-and-cldr.md) covers the identifiers and the data behind them; for now it is enough to separate the two questions a program must ask: *which language should I show?* and *which conventions should I apply?*

## Translating and adapting are different decisions

Roturier (2015) divides localization work into three kinds. Translation handles textual content, supported by translation memory and machine translation. Non-translation activities, such as file processing and testing, glue the translations back into working files. Adaptation covers everything else: images and video, functionality such as a spell-checker's dictionaries, the location of a web service, and text that needs so much change that the industry calls it *transcreation*. Roturier notes that in practice software strings and user assistance almost never receive that treatment, and that adaptation needs entirely different skills and resources from string replacement.

This split gives a translator a working test. When a string reaches you, ask what kind of change it needs:

- **A rendering.** The meaning stays, the words change. This is most interface text.
- **A convention.** The value stays, the display changes: a date, a number, a unit, a quotation mark. The program should do this, not the translator (chapter [106](106-numbers-dates-and-units.md)).
- **An adaptation.** The content itself changes for the market: an example name, a legal clause, a support address, an image. This needs a decision by someone with authority to make it (chapter [110](110-culture-and-cost.md)).

The FontLab localization of 2026 shows how much of the translator's work falls into the first kind and how hard it still is. Its principles page, in the writing styleguide, notes that the English word *width* names four different things in a font editor: the advance width of a glyph, the geometric width of a box, the width axis of a variable font and tracking. German needs four different words for them. None of this is adaptation. It is rendering, and it requires the translator to know what the software does with each string.

Translating and adapting also have a budget. Not every product is localized completely, and a project that pretends otherwise will overspend or underdeliver. Microsoft, as Jiménez-Crespo (2024) reports, called the amount of translation and customization the *localization level*, and several scales exist. The one described by Brooks (2000) for Microsoft software has three steps:

| Level | What the user gets |
|---|---|
| Enabled | The user can type and use their own language and script; the interface and help stay in the source language |
| Localized | The interface and help are translated; language tools such as spell-checkers may be missing |
| Adapted | All linguistic tools, functions and content are adapted to the locale |

Video game and website scales add levels at both ends, from "sold as is" to "culturally adapted". The useful lesson is that the level is a business decision made before the work begins, tied to expected return. Esselink (2000) gives the example of a publisher that translates the installation and getting-started guides but ships the administrator manuals in English. Chapter [110](110-culture-and-cost.md) returns to the cost side.

## A worked example: sorting one defect report

Suppose a tester files one report against the German build of a desktop application:

> The export status says "3 Datei(en) exportiert nach C:\Users\anna\Export am 03/05/2026". The date is wrong, "Datei(en)" looks unfinished, the path overflows the status bar, and the support link in the same panel points to an English page.

The report contains four problems, and each belongs to a different layer.

1. **"Datei(en)"** is an internationalization defect. The code built the message without a plural mechanism, so the translator had no way to write correct German for one file and for three. The fix is in the source: a plural-aware message (chapter [107](107-plurals-gender-and-message-formats.md)). No translation can repair it.
2. **"03/05/2026"** is also internationalization. The program formatted the date with a fixed pattern instead of asking the locale. German readers expect `03.05.2026`, and a reader in the United States would read the same digits as the fifth of March rather than the third of May. The fix is to pass a date value to a locale-aware formatter.
3. **The overflow** is shared. The layout gave the status text a fixed width, which is an internationalization defect; the German text is also longer than the English, which is a fact of localization. The fix is a layout that grows or wraps, checked in the running German build (chapter [109](109-space-and-growth.md)).
4. **The English support page** is globalization. Nobody decided whether German users get German support. A translator who replaces the link with a guessed German URL has made a business decision without authority.

Notice what is missing: none of the four is a translation error. The German words themselves may be fine. This is the normal distribution. When a localized product looks bad, the cause usually sits upstream of the translator, and the cheapest place to fix it is in the code before the next language is added.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 1: definitions, industry, project components)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 1: world-readiness, locales, glossary)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 1.3: conceptual framework)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 2: locales, GILT, definitions and metaphors; chapter 3: levels of localization)
- `research/01-foundations-of-software-localization.md` in the fl10n repository (section 1.1)
- `src_docs/md/localization/principles.md` in the vexy-fontlab-writing-styleguide repository
