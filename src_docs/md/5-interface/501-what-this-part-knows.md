---
this_file: src_docs/md/5-interface/501-what-this-part-knows.md
---

# 501. What this part knows

The first four parts of this book prepare a catalog: the concepts behind a locale, the engineering that keeps text out of code, the file formats that carry it and the terminology that fixes what each concept is called. This part is about the moment a translator meets one interface string and has to decide what to write. It covers the strings people read while they work: menu commands, buttons, check boxes, field labels, tooltips, status messages, errors, and the help text that quotes them.

Interface translation is its own discipline because the strings are short, reused and assembled. A label of two words carries no sentence around it to disambiguate a noun from a verb. The same English word can appear in forty contexts. A message can be half a sentence, completed at run time by a file name or a count. The translator often works from a list, and the application shows the result in a control whose width was set for English. Esselink put the difficulty plainly in 2000: when translators work on software strings they "very often have to guess if, how, and where a particular string may be displayed." Tooling has reduced the guessing since then; it has not removed it.

## What the chapters cover

The chapters move from the shape of a single label, through its mechanics, to the running application.

- [502. Headline style](502-headline-style.md) explains why a compact English label is already compressed and how to carry that compression into languages that could spell everything out.
- [503. No added detail](503-no-added-detail.md) covers the opposite reflex: turning *pair* into *kerning pair*, or dropping a distinction the English keeps.
- [504. Mnemonics, shortcuts and key names](504-mnemonics-shortcuts-and-keys.md) separates what a translator may change in a label (the mnemonic letter, the key name) from what belongs to engineering (the key binding).
- [505. Plurals in practice](505-plurals-in-practice.md) applies the plural theory of [107](../1-foundations/107-plurals-gender-and-message-formats.md) to real Qt catalogs, where Polish has three forms, CLDR has four categories and a count can govern the case of the words around it.
- [506. Placeholders and agreement](506-placeholders-and-agreement.md) treats the sentence that the application finishes: numbered arguments, gender that the string cannot know, and the label-and-value recast that rescues most of them.
- [507. Registers of the interface](507-registers-of-the-interface.md) distinguishes the voice of a button from the voice of a tooltip, a help article, a manual and a store page, and shows how a term drifts when those registers are translated at different times.
- [508. Source text as evidence](508-source-text-as-evidence.md) deals with English strings that are wrong, and with what a translation owes the behavior of the control rather than its label.
- [509. Four language portraits](509-language-portraits.md) applies the rules to German, Spanish, French and Polish, the four languages of the FontLab 9 localization in 2026.
- [510. Review in the running application](510-review-in-the-running-app.md) closes the part where every interface translation must close: on screen, at the shipped size, with the real fonts.

## Why it matters

A wrong term in a help article costs a reader a minute. A wrong label on a button costs every user every day, because people learn a program by recognizing its commands, and a command that changes its name between the menu, the dialog and the help teaches them nothing. Most of the rules in this part come down to three habits: keep the meaning of the source exactly, keep its length and its form where the control demands it, and verify both in the application rather than in the catalog.

The part also draws a line that the older literature drew less sharply. Some defects are translation defects and some are not. A clipped label that the translator could not see is a layout defect. An English string that describes the wrong operation is a source defect. A mnemonic that collides with an item the program inserts at run time is an engineering defect.

## How the examples work

The worked examples come mostly from the FontLab 9 review of 2026: catalogs of about 10,500 messages per language, the German reviewed in full, the Spanish in part and the French in targeted passes, with disputed strings checked against the application's source code, and a first Polish catalog generated as a machine draft awaiting native review. The founder's review remarks (fl10n issues 133 and 146) supplied many of the rules, and the exact before-and-after ledgers record how they were applied. The examples are there because they are concrete and checkable, not because the rules belong to one product. Every chapter states the general problem first, from the published literature, and then shows one case.

Where vexy-localizzy helps, with structural checks or its browser preview of Qt forms, the chapters say so briefly. Neither replaces a reviewer who knows the language.

## What this part assumes

The reader knows what a catalog, a context and a placeholder are ([Part 2](../2-engineering/201-what-this-part-knows.md) and [Part 3](../3-formats/301-what-this-part-knows.md)) and how terms are chosen and recorded ([Part 4](../4-terminology/401-what-this-part-knows.md)). Machine drafts and their checks belong to [Part 6](../6-machine-translation/601-what-this-part-knows.md); the release process, formal quality assurance and pseudo-localization belong to [Part 7](../7-process/701-what-this-part-knows.md). This part stays with the string and the screen.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 3)
- `issues/133.md` and `issues/146.md` in the fl10n repository
- [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/), [localization/ui-strings](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/ui-strings/), [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/) and [localization/pl](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/pl/) in the vexy-fontlab-writing-styleguide repository
- [docs/quality.md](../8-toolkit/quality.md) and [docs/review.md](../8-toolkit/review.md) in the vexy-localizzy repository
