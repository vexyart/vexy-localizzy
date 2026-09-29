---
this_file: src_docs/md/5-interface/509-language-portraits.md
---

# 509. Four language portraits: German compounds, Spanish dialect, French spacing, Polish cases

The rules in this part are meant to hold for any language. Each language still has a place where the rules bite hardest, a habit that native translators bring and reviewers must check, and a set of facts that no general rule supplies. This chapter describes four of them as they appeared in the FontLab localization of 2026: German, Latin American Spanish, French and Polish. The portraits are not grammars. Each names what a reviewer of that language needs to know first, and how far the review had progressed when this book was written, because a rule applied to a reviewed catalog and a rule written for a draft carry different weight.

| | German | Spanish (es_MX) | French | Polish |
|---|---|---|---|---|
| Review state, 29 September 2026 | all 10,587 entries reviewed, 1,943 changed | first 7,200 messages reviewed, 1,940 corrected | targeted corrections and a terminology pass; full review outstanding | machine draft awaiting native review |
| Qt plural forms | 2 | 2 | 2 | 3 |
| Decimal and grouping | `1.234.567,89` | `1,234,567.89` | `1 234 567,89` (U+202F) | `1 234 567,89` |
| Shift in text | Umschalt | Mayús | Maj | Shift |
| Quotation marks | „…“ | «…» | « … » | „…” |
| *smart* | schlau | astuto | futé | sprytny |
| em, for units per em | Geviert | eme | cadratin | firet |
| Planning expansion | a tenth to a third; up to double for single words | a fifth to a quarter | a sixth to a fifth | comparable to German |

## German: compounds and compression

German gives a translator two freedoms that must both be restrained: any speaker can form a compound, and any sentence can be spelled out in full. [502](502-headline-style.md) and [503](503-no-added-detail.md) describe the restraint. Headline style drops articles and the verb *sein* from compact labels (*Wenn Maske aktiv*), conversions drop their verb (*Pinsel zu Konturen*), and compounds do not add specificity (*Paar*, not *Kerningpaar*).

The compound rule has a second half, about spelling. In fl10n issue 133 the founder set it out: German compounds may be written as one word when they form naturally from native words, but when a part is an English word thinly loaned, it takes a hyphen. So *Glyphenfenster* and *Dicktenausdruck* are closed, while *Kerning-Klasse*, *Demo-Modus*, *Stil-Gruppe*, *Master-Dickten*, *Code-Editor* and *Element-Referenz* are hyphenated. The test is whether a native reader sees one word or a borrowed word with a suffix. The rule applies retroactively: the consistency pass changed *Kerningpaar* to *Kerning-Paar* throughout, and the current catalog has no closed form left.

German distinguishes concepts that English merges, and the review chose a word for each. Advance width is *Dickte*, the geometric width of a box *Breite*, the width axis *Weite*, tracking *Laufweite*. For variation axes, *Stärke* and *Weite* suffice where context is clear, with *Strichstärke* and *Schriftweite* only where the short form would be ambiguous. Units per em is *Geviertauflösung*, the resolution of the em square, after the founder rejected *Kegelauflösung*, the resolution of the type body.

Two smaller German facts cause frequent defects. The founder's remark on smart filters wrote *Schlauer Filter hinzufügen*; the catalog has *Schlauer Filter* as the feature name and *Schlauen Filter hinzufügen* for the command, because the object of *hinzufügen* is accusative. A rule about a word never suspends the grammar around it. And uppercasing *ß* gives *SS* or *ẞ*, so code must never uppercase a translated string.

## Spanish: one catalog for a continent

The Spanish catalog is `es_MX`, and its guide describes its register as Latin American: *tú* in product help, *ustedes* for several people, the infinitive in commands. It aims to serve Latin America as a whole and does not turn every regional usage into a Mexican one. Spain will have its own catalog.

That choice has consequences a reviewer must check in every string with a number. Mexican Spanish writes a decimal point and groups with commas, `1,234,567.89`; Spain writes `1.234.567,89`. The guide classes a dialect mixed into the other variety as a compliance error, not a spelling choice. Vocabulary follows the same split: *computadora* in Latin America, *ordenador* in Spain. Dr International (2002) gives a finer map for the same word, *computador* in Mexico and Puerto Rico and *computadora* in the rest of Latin America, and recommends using one wording acceptable in all locales where one exists. The two sources disagree about Mexico; for a catalog that serves the whole region, the practical answer is the guide's, checked against current usage in the market.

Spanish headline style is milder than German. The review wrote *Si máscara activa* and *Seleccionar misma marca*, dropping articles, but kept the verb in a comparison: *si nuevo ancho es menor que actual*. Spanish also has a plural category, `many`, for exact millions (*1 millón de glifos*) that a two-form Qt catalog cannot express.

The mechanical facts come from the platform and from CLDR: *Mayús* for Shift, *Intro* for Enter, *Supr* for Delete; «…» in prose with inverted opening marks for every question and exclamation; month and language names in lowercase; and false friends such as *actual*, which means current.

## French: spacing and the long word

French typography puts space where English has none. A narrow no-break space precedes `;`, `!` and `?`, a no-break space precedes `:`, and guillemets take no-break spaces inside: « … ». In a catalog those spaces are characters, and they must be the right characters. A regular space before a colon lets the colon wrap to the next line on its own; a missing space looks like an English string. The rule is easy to state and easy to miss. On 29 September 2026 the French catalog had the space in the right places but mostly the wrong character:

| Before a colon | Occurrences |
|---|---|
| ordinary space | about 1,360 |
| no-break space (U+00A0) | 25 |
| narrow no-break space (U+202F) | 0 |

The color-flag tooltip, *Diminuer la marque de couleur*, has ordinary spaces before both of its colons. A script that counts the characters before `:`, `;`, `!` and `?` finds all of them in seconds; a reviewer reading the screen finds only the ones that happen to wrap. Numbers use the narrow no-break space U+202F as the group separator, with a regular no-break space as the fallback, and because the comma is the decimal separator, lists use a semicolon.

French capitals keep their accents (*Édition*, *À propos*), which matters for mnemonics ([504](504-mnemonics-shortcuts-and-keys.md)) and for clipping at tight line heights ([510](510-review-in-the-running-app.md)).

For terminology, the French guide takes Haralambous, *Fontes et codages*, as its model source: *chasse* for advance width, *approche* for sidebearings, *crénage* for kerning, *interlettrage* for tracking, *fût* for stem, *cadratin* for the em. French also shows how a platform word can collide with a product meaning. Issue 146 changed the French for the source panel's *Revert* button from *Rétablir* to *Recharger*, because *Rétablir* is the French platform word for Redo, and the button discards edits and reloads.

Two French facts need care in review. CLDR places 0 in the `one` category, so *0 glyphe sélectionné* is correct and an English-style zero branch is often unnecessary. And market claims carry legal weight: the guide asks reviewers to flag an absolute claim such as *totalement sécurisé* against its source rather than soften it silently ([507](507-registers-of-the-interface.md)).

The French guide describes its own state in two ways, as targeted corrections with the full review still to be done, and as a full pass of the catalog against the Haralambous and Frutiger memories under issue 145. Both are true of different passes. The catalog has had a terminology review; a message-by-message linguistic review is outstanding.

## Polish: cases, and a draft awaiting its reader

Polish is the language where the grammar of numbers and names reaches furthest into the interface. [505](505-plurals-in-practice.md) and [506](506-placeholders-and-agreement.md) show the effects: three Qt plural forms and four CLDR categories, verbs that agree with the plural category, prepositions and verbs that fix a case so that forms coincide, and inserted names that cannot decline. The label-and-value recast is used more in Polish than in the other three languages, because it is often the only way to make a sentence correct for every value.

The Polish terminology has a particular history. A September 2026 evidence review compared the core memory with nineteen Polish interface glossaries and a shelf of Polish typographic books, approved 74 proposals, replaced 18 and kept 59 as proposed for want of attestation. On 29 September the founder's update in issue 146 overrode several of its conclusions: advance width became *szerokość pola* where the evidence review had kept *szerokość posuwu*, stem became *trzon* instead of *kreska główna*, line gap *interlinia* instead of *światło międzywierszowe*, and nudge *holowanie* instead of *pchnięcie*. The Polish guide keeps both records. Evidence establishes what professionals have written; the owner of the product voice may still choose otherwise, and the ledger must say which kind of decision each term is ([406](../4-terminology/406-evidence-and-attestation.md)).

The same update localized FontLab's feature names playfully: *Pełna krasa* for True Fill, *superholowanie* for Power Nudge, *swat*, the Polish word for a matchmaker, for Matchmaker, *kuzynostwo* for Cousins. The shared principles used to list Cousins, Power Brush and True Fill among the names to keep in English; issue 147 turned the Polish decisions into the general rule, so the principles now ask every language for the same playfulness and keep only brands, trademarks and operations with a fixed technical meaning in English. Some names stay English in Polish too: Genius, Fusion, Oblique and Flex.

The mechanical facts are few but unforgiving. Polish Windows keeps English key names (*Shift*, *Ctrl*, *Enter*). Quotation marks are „…” with «…» inside. The one-letter words *w*, *z*, *i*, *o*, *u*, *a* take a no-break space to the next word in prose; in a compact label width matters more. The diacritic capitals *Ą*, *Ę* and *Ż* clip at tight line heights. And the draft itself has defects no reviewer has yet seen: on 29 September 2026 its top-level menu bar had two mnemonic collisions ([504](504-mnemonics-shortcuts-and-keys.md)).

The first Polish catalog, 10,474 messages, was generated by a language model with the core memory as glossary and a Polish style sheet, and passed every placeholder, markup and plural check. The Polish guide calls it what it is: a draft awaiting a native editorial pass. A catalog that passes structural checks is ready for a reviewer, not for release.

## What the portraits share

The four languages differ in where they put space, how they count and how they build words. The review found the same failures in all of them: detail added to compact labels, a term rendered two ways, a string assembled from fragments that no longer agreed, a key name taken from memory instead of the platform. The language guides exist to record the answers once, with their reasons, so that the next catalog, and the next reviewer, starts from the decision rather than from the problem.

## Sources

- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 10: text)
- `issues/133.md` and `issues/146.md` in the fl10n repository
- `data-fontlab-cpp/i18n/review/2026-09-28-issue133-de.json`, `-es.json` and `-fr.json` in the fl10n repository
- `data-fontlab-cpp/i18n-repo/fontlab_de.ts`, `fontlab_es.ts`, `fontlab_fr.ts` and `fontlab_pl.ts` in the fl10n repository
- [localization/de](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/de/), [localization/es](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/es/), [localization/fr](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/fr/), [localization/pl](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/pl/), [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/) and [localization/ui-strings](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/ui-strings/) in the vexy-fontlab-writing-styleguide repository
