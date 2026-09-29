---
this_file: src_docs/md/5-interface/510-review-in-the-running-app.md
---

# 510. Review in the running application: width, wrapping, mixed direction and the screenshot

Every chapter in this part has ended with a check that a script cannot make. This chapter collects them. An interface translation is finished when it has been read on screen, in the running application, at the size and with the fonts the user will see, in every state the program can reach. Uren, Howard and Perinotti wrote in 1993 that "nothing beats testing the actual localized version in a localized environment", and three decades of better tools have not changed the conclusion. They have changed how much of the work can be done before the reviewer opens the application, and how precisely the reviewer can record what was found.

## What a catalog review cannot see

A catalog shows strings one at a time, grouped by context. The application shows them together, at a fixed width, completed at run time, beside controls and strings from other catalogs. Several classes of defect exist only in the second view.

- **Width.** A label that fits in the catalog editor may be clipped in a panel whose column was sized for English.
- **Assembly.** Fragments that read well alone may form a broken sentence when the program joins them ([506](506-placeholders-and-agreement.md)), and code may append a period that the translation already has.
- **Runtime items.** Menus and dialogs completed by code can produce mnemonic collisions and mixed-language screens that no single context contains ([504](504-mnemonics-shortcuts-and-keys.md)).
- **Other catalogs.** Qt's own dialogs and buttons come from the framework catalog; a build that ships without it shows an English *Cancel* beside a translated *Open*.
- **Ambiguity.** A compressed label that could be a noun or a verb is decided by the controls around it ([502](502-headline-style.md)). Roturier (2015) gives the English version of the problem: does *Share drive* mean sharing a drive or a drive containing a share?

The writing guide's runtime-review page adds the cases where the label is right and the task is wrong: a translated field that reads a decimal comma as a thousands separator, a fallback that shows a raw resource key, a language switch that leaves an open dialog in the old language. Review a task from entry to result, not a screen.

## Width: budgets, measurements and the strict case

Every source agrees that translations grow. They disagree on how much, and the disagreement is instructive because the figures describe different things.

| Source | Planning figure |
|---|---|
| Uren, Howard and Perinotti (1993), quoting the Windows SDK | by source length: 200% extra space for 1 to 10 characters, 100% for 11 to 20, 80% for 21 to 30, 60% for 31 to 50, 40% for 51 to 70, 30% above 70 |
| Esselink (2000) | most European languages longer than English, often by as much as 30% |
| Dr International (2002) | allow about 30% additional room |
| fl10n research synthesis (2026) | most European languages 30 to 50%, German, Russian and Finnish at the extreme |
| FontLab principles (2026) | about a third for sentences, up to double for single words |
| FontLab language guides | German a tenth to a third; Spanish a fifth to a quarter; French a sixth to a fifth; Polish comparable to German |

The Windows table and the FontLab principles say the same thing in two resolutions: short strings grow proportionally more than long ones, because a single English word can have a much longer equivalent (*Edit*, *Bearbeiten*) while a long sentence averages out. The flat thirty percent of Esselink and Dr International is a figure for sentences. All of these are planning budgets for developers deciding how much room to leave. The principles say it directly: a budget never approves a control, which only a review of the running interface can do.

The strict case is a panel that allows no growth. The FontLab Measurements panel required every translation to be at most as long as the English ([502](502-headline-style.md)), which makes length a hard constraint the translator can check. Most panels are not so simple: what matters is width in pixels in the actual font, not characters.

**Worked example: measuring preference labels.** In September 2026 the FontLab preference labels were checked by measurement rather than by eye. A script rendered every preference label, choice and the sidebar caption with Qt's own font metrics (`QFontMetricsF` in Qt 5.15.19, offscreen, at the 11-point size the forms declare) and compared each width with a budget inferred from screenshots: 210 logical pixels for a label with an icon, 232 without, 150 for the sidebar caption, with 2 pixels of tolerance. That covered 1,416 cases across four languages.

| Language | Labels changed | Over budget before | Over budget after |
|---|---|---|---|
| English | 15 | 15 | 0 |
| German | 45 | 33 | 0 |
| French | 57 | 51 | 0 |
| Spanish | 46 | 24 | 0 |

Two things in this table deserve attention. English itself had fifteen labels over budget, so the source needed shortening before the translations could be judged. And French, for which its guide plans the smallest growth of the three, a sixth to a fifth, had the most overruns. The report is careful about its limits: the budgets are screening assumptions, not measured allocations in a running window; the report also recorded 13-point widths as a stress check and notes that larger fonts at unchanged column widths can still clip; and no full visual test of the application was performed. Measurement narrows the review. It does not replace it.

## Wrapping, clipping and mixed direction

**Clipped diacritics.** A capital with a diacritic needs vertical room: *Ä*, *É*, *Ą*, *Ę*, *Ż*. At tight line heights the mark is cut off, and the result looks like a typo in the translation. Uren (1993) described the requirement in the terms of the time, fonts with enough internal leading for diacritical marks; the runtime-review page lists the symptom and says to check line height, the actual font metrics and the clipping area before blaming the text.

**Wrapping.** Where a control wraps, check where it wraps. A French colon or question mark that falls alone onto the next line reveals an ordinary space where a no-break space belongs ([509](509-language-portraits.md)).

**Mixed direction.** None of the four FontLab languages is written right to left, but a font editor handles text in every script, and a reviewer of a right-to-left interface meets mixed direction everywhere: Latin glyph names, OpenType tags and file paths inside Arabic or Hebrew labels. The runtime-review page asks for two separate checks: the reading order of the interface, and the direction of inserted values, including the text a user copies, which must keep its logical order. It adds a warning specific to design tools: outline geometry, coordinate signs and commands that move a point have fixed meanings. A mirrored layout must not silently describe a different operation. Mirroring itself is the subject of [208](../2-engineering/208-mirroring-and-rtl.md).

## The screenshot and what it proves

A screenshot is the reviewer's basic evidence and the most overrated one. The quality page states its limit: a screenshot can show missing text; it cannot establish whether the catalog, the resource lookup or the layout caused it. A screenshot of a corrected label does not prove that a numeric or fallback defect is fixed. Record the build, platform, interface language, formatting locale and the starting state with every capture, and record the expected result before looking, so the screenshot answers a question rather than illustrating a guess.

Tools can bring the screen closer to the translator. Roturier (2015) describes in-context localization for the web, in which Mozilla's Pontoon lets a translator edit text directly on the rendered page and see at once when it no longer fits. vexy-localizzy's browser reviewer does the equivalent for Qt forms: it renders `.ui` files with the translated text, with Original and Localized tabs and a scale control, and lets the reviewer click rendered text to select the matching message. The preview is honest about its limits. It renders standard Qt widgets and preserves their geometry, but custom application widgets appear as generic placeholders, external images are not loaded, and no application code runs. It catches clipping in a form; it cannot catch a runtime-inserted menu item or an assembled sentence. It shortens the loop between translation and review, and leaves the final check to the application.

## A review session

The runtime-review page describes a pass that finds most of what the catalog review cannot. In order:

1. Record the application version, platform, interface language, formatting locale, keyboard layout and fallback behavior.
2. Open every dialog in every state, because dynamic dialogs show more than the catalog. Enter invalid data to trigger long and assembled messages.
3. Compare each menu command with the title of the dialog it opens, and count menus, options and commands against the English build.
4. Check tab order, every combo box's full list, and the mnemonics in each menu, including items inserted at run time.
5. Run each plural message with the language's test numbers ([505](505-plurals-in-practice.md)).
6. Trace each English leftover to its resource and its fallback decision.
7. Test on a target-language operating system, so its own words and messages are distinguishable from the application's.
8. Record each case as passed, failed or not checked. An empty failure list does not prove that review happened.

Two findings from 29 September 2026 show what such a session would catch in minutes. The Polish draft's menu bar had *P* marked in both *Plik* and *Pomoc*, and *K* in both *Tekst* and *Kontur*; on Windows, pressing Alt+P on that build would show the collision at once. And the German Help Panel described a *Power-Verschiebung* mode that the interface calls *Power-Schub* ([507](507-registers-of-the-interface.md)); a reviewer following the help article in the application would look for the label and not find it. Both were found by script against the catalogs. Neither had yet been seen on screen, and that is the step this chapter asks for: attach each finding to the surface that owns it, fix it there, and repeat the original case in the corrected build before closing it.

## Sources

- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (sections 4.3.10, 4.3.21 and 4.5)
- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 3: space restrictions)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 7)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (sections 4.2.4 and 4.2.8)
- `research/01-foundations-of-software-localization.md` (section 1.5) in the fl10n repository
- `data-fontlab-cpp/i18n/source-review/preference-label-fit-2026-09-16/REPORT.md` in the fl10n repository
- `data-fontlab-cpp/i18n-repo/fontlab_pl.ts` and `help/helppanel_de.json` in the fl10n repository
- [localization/runtime-review](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/runtime-review/), [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/), [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/), [localization/ui-strings](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/ui-strings/), [localization/de](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/de/), [localization/es](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/es/), [localization/fr](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/fr/) and [localization/pl](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/pl/) in the vexy-fontlab-writing-styleguide repository
- [docs/review.md](../8-toolkit/review.md) in the vexy-localizzy repository
