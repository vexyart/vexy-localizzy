---
this_file: src_docs/md/1-foundations/103-a-short-history.md
---

# 103. A short history: from code pages and DOS to continuous delivery

The books this part draws on span thirty-two years. Uren, Howard and Perinotti wrote in 1993 about WordPerfect 5.1 on DOS. Jiménez-Crespo wrote in 2024 about cloud translation management and neural machine translation. The research corpus behind this book was assembled in 2026, when large language models draft most first translations. Reading them side by side shows which advice was a workaround for a machine that no longer exists and which advice has held for three decades. This chapter sorts the two, so that the rest of the book can quote an old source without importing its constraints.

## Before internationalization: the local rewrite

Uren, Howard and Perinotti (1993) open with an observation that is still the best short argument for the whole field. A letter is passive: once translated, it is finished. Software is active. A translated letter contains one alphabetized list; translated software "must know how to alphabetize any and all lists of names". Translating the messages is only part of the job, because the mechanisms that process text also have to follow the rules of the new language.

In the 1980s that job was usually done by a distributor. Uren describes the pattern: a European company that wanted to sell an American product obtained the complete source code, changed every string, sort routine and format for its own language, and shipped the result. The next language started again from scratch. The authors call this *retrofitting* and point out its cost: with more than one target language, every step is repeated.

O'Donnell (1994) describes the same world from the programmer's side. American software printed dates as month, day, year, used English month names, handled only the letters A to Z, and formatted money in dollars, because all of it was hard-coded. O'Donnell is careful to add that American software was not unusual: a French package might accept only day, month, year, and a Japanese one might handle Japanese text and nothing else. Customers faced three choices, all bad: reject the product, accept its limits, or pay for a customized version that replaced one set of biases with another and then failed to interoperate with the original on a shared network.

## Code pages: one byte, 256 characters, many tables

The deepest constraint of that period was the byte. Uren's chapter on the IBM PC lists the character sets available in MS-DOS 5.0, each called a *code page*:

| Code page | Coverage | Introduced |
|---|---|---|
| 437 | U.S. English | shipped with U.S. hardware |
| 850 | Multilingual (Latin 1) | DOS 3.0 |
| 852 | Slavic (Latin 2) | DOS 5.0 |
| 860 | Portugal | DOS 3.3 |
| 863 | Canadian French | DOS 3.3 |
| 865 | Nordic | DOS 3.3 |

Every code page held 256 characters, and the first 128 were identical in all of them. The upper half changed meaning with the active page, so the same byte could be *é* on one machine and a box-drawing line on another. Windows 3.x, running on top of DOS, used a different character set internally (Microsoft called it ANSI) and referred to the DOS pages as OEM. IBM's own reference, Uren notes, listed 34 code pages, and the authors admitted they did not know where all of them were used.

Two habits from this era still cause bugs. The first is case conversion by arithmetic: in the lower 128 characters, upper and lower case differ by 32, so programs added or subtracted 32. Uren already advised against it in 1993; outside ASCII it is simply wrong. The second is assuming that one byte is one character. Chapter [104](104-characters-and-encodings.md) explains why that assumption fails in every modern encoding.

The industry's answer to retrofitting was internationalization: build one program that can be localized many times. Uren describes the intended result as an "International English" version whose code already contains the logic for every target language, so that a French edition becomes a matter of translating text files and setting parameters. O'Donnell's 1994 book teaches the C and UNIX machinery for it: locale categories, message catalogs and the character-handling routines added to the standards.

Jiménez-Crespo (2024) summarizes what the industry learned when it tried to treat programming and translation as two consecutive stages. Engineers extracted strings into text files, translators returned them, engineers put them back, and then discovered that the translations did not fit and that dates and reading direction had not been considered at all. Two practices fixed this: localizable text and assets moved into resource files separate from code, and internationalization was planned from the start of a project. That is the origin of the GILT cycle described in chapter [102](102-what-localization-is.md).

The service industry grew around this model. Esselink (2000) dates the first multi-language vendors to the mid-1980s and the founding of the Localisation Industry Standards Association to 1990. In the 1990s vendors added engineering, testing and desktop publishing to translation, which is when, in Esselink's words, translation became localization. Publishers typically started with French, Italian, German and Spanish plus Japanese; Ireland became the hub where much of the work for the large U.S. publishers was managed.

## Unicode and the single binary

By 2000 two technical changes had reshaped the work. Esselink names Unicode as the development that affected localization most, because it offered one character set for every script. Esselink describes it as using "two bytes (16 bits) for all characters", which was an accurate simplification for that year. By 2015 Roturier describes a standard with room for about 1.1 million code points and UTF-8, a variable-width encoding, as the preferred encoding for web pages. The two-byte description is now historical; chapter [104](104-characters-and-encodings.md) gives the current picture.

The second change was the *single worldwide binary*: one executable that supports all languages, with the interface text in separate resource-only libraries. Replace the resource library and the application runs in another language without changing its code. Microsoft's *Developing International Software* (Dr International, 2002) built its whole method on this idea. It also defined the *release delta*, the time between the domestic release and a localized one, and *sim ship*, a release delta short enough that all languages share the launch. The book's working figure for that window:

**Sim ship: usually within 30 days of the domestic release.**

Microsoft developed English, German and Japanese editions of Windows in parallel, reasoning that German tests European languages and Japanese tests East Asian ones. For a fourth edition the book suggests a right-to-left language such as Arabic, a European language that does not use Latin script such as Russian, or a language with a complex script such as an Indic language.

## The web, agile teams and continuous localization

Websites changed the rhythm. Esselink (2000) already notes that database-driven sites turn web localization into something closer to software localization, and that content changes too fast for a translate-then-ship cycle. Jiménez-Crespo (2024) follows the thread through mobile apps, crowdsourced translation of social networks and cloud translation management systems, and distinguishes the workflows that result:

| Workflow | Shape | Risk |
|---|---|---|
| Waterfall | Development, preparation, localization, integration and testing in sequence | A late defect is expensive because developers have moved on |
| Agile | Localization inside time-boxed sprints | Large volumes due within each short sprint |
| Continuous | Small changes flow from the repository through the translation system and back, possibly several times a day | Needs automation and gates in place of a string freeze |

Jiménez-Crespo also reports Esselink's 2022 judgment that the industry changed less in two decades than one might expect: tools moved into the browser, and the innovation with the greatest effect was neural machine translation, whose post-editing became normal for many content types.

The research corpus of 2026 describes the next step. Its synthesis traces machine translation from rule-based systems through statistical and neural models to large language models, and argues that the limit is now the context supplied with each string rather than the raw model. Its recommended pipeline treats translations as code: extracted by native tools, diffed against the main branch, drafted by a model with glossary and context, checked by deterministic rules, sampled by a model acting as judge, and merged through a reviewed pull request. Human review becomes the exception, reserved for the strings where judgment matters. Part [7](../7-process/702-continuous-localization.md) follows that loop in detail.

## A worked example: one Polish label across four decades

Follow a single Polish menu label, *Zapisz jako…* (Save As…), and the letters it contains, through the periods above.

1. **About 1990.** The label needs no letter outside ASCII, but most Polish labels do: *Wyślij*, *Usuń*, *Właściwości*. Among the MS-DOS code pages Uren lists, the one for Polish, 852 (Slavic, Latin 2), arrived only with DOS 5.0. A distributor retrofitting a product would have edited the source and chosen an encoding, and a file written under code page 852 would show different characters in the upper half on a machine set to code page 850.
2. **About 2000.** The label sits in a resource library of a single worldwide binary. Unicode makes *ś* and *ń* ordinary characters. A localization vendor translates the resource file with translation memory, and an engineer rebuilds and tests it. The Polish edition ships weeks or months after English, depending on the release delta.
3. **About 2015.** The label lives in a translation management system connected to the repository. When a developer adds a string, the system pulls it, matches it against memory and sends only the new text to a translator, perhaps with a machine draft to post-edit.
4. **In 2026.** In the FontLab localization recorded in the writing styleguide, the first Polish catalog of 10,474 messages was generated by a large language model using the Polish core memory as a glossary, an attested seed vocabulary and a Polish style sheet. Every string passed placeholder, markup and plural checks, and the catalog compiled; the styleguide still describes it as a draft that awaits a native editorial pass.

Two things stay constant through all four steps. Someone has to decide what each English string means before choosing the Polish words, and someone has to see the label in the running application before calling it finished. What changed is who does the typing and how much of the checking a machine can take over. The rest of this book is built on that division.

## Sources

- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (chapter 1; chapter 3, sections on WordPerfect, DOS and Windows character sets)
- Sandra Martin O'Donnell, *Programming for the World: A Guide to Internationalization*, 1994 (chapter 1)
- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 1: localization industry, technology)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 1: world-readiness, release delta, sim ship)
- Johann Roturier, *Localizing Apps*, 2015 (section 2.3: encodings)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 2: emergence of localization, software, web and mobile; chapter 3: waterfall and continuous workflows)
- [localization/pl](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/pl/) in the vexy-fontlab-writing-styleguide repository
