---
this_file: src_docs/md/1-foundations/109-space-and-growth.md
---

# 109. Space and growth: expansion, truncation, wrapping and layout that survives translation

Every localization guide warns that translations grow. The warning is right, and it is also the most misapplied piece of advice in the field. Teams read "allow 30 percent" as a rule, give every button 30 percent more room, and then discover that *OK* became *Aceptar*, that German menu names doubled, and that Chinese labels shrank so far the layout looks empty. This chapter explains where growth comes from, what the published figures actually say and where they disagree, how the FontLab catalogs of 2026 measured up, and how to design a layout that does not depend on any single figure.

## What the sources say

The figures have been repeated for a quarter of a century, and they are not the same figure.

| Source | Recommendation |
|---|---|
| Esselink (2000) | Add about 30% extra space to each control; German *Bearbeiten* (Edit) and *Wiedergabe* (View) grow by 100% |
| Dr International (2002) | Leave about 30% extra room, but for strings under 10 characters leave at least 400% |
| Research corpus (2026) | Most European languages expand 30 to 50% from English; German, Russian and Finnish are at the extreme |
| FontLab principles (2026) | Plan about a third for sentences and up to double for single words; in dense panels, no growth at all |

The disagreement is mostly about string length. Short strings grow proportionally more, because a single long word replaces a single short one and there is no sentence to absorb the difference. Dr International's example is the *OK* button: Spanish uses *aceptar*, which the book calls 250 percent bigger, so a 30 percent allowance leaves room for one extra letter. Esselink's menu examples make the same point from the other side: a 30 percent rule and a 100 percent observation sit on the same page of Esselink's book. The FontLab principles state the reconciliation outright: a budget "tells a developer how much room to leave; it never approves a control". Only looking at the translated control does that.

Growth is not universal either. Roturier (2015) notes that French and German tend to expand from English while some Asian languages, such as Chinese, tend to be more compact, so a single layout for every language is often a compromise in both directions. And growth depends on the translator. A translator who writes full sentences where the English wrote a clipped label can double any string; one who keeps the English compression can hold growth close to zero.

## What the FontLab catalogs measured

The FontLab localization project holds four catalogs of the FontLab interface, each with 10,418 translated singular messages. The Polish one is a machine draft that, according to the Polish guide, awaits a native editorial pass. Counting characters, with mnemonic ampersands removed, gives the ratio of translation length to English length:

| Language | Whole catalog | Strings of 1 to 10 characters: median, 90th percentile | 11 to 20 | 21 to 50 | Over 50 |
|---|---|---|---|---|---|
| German | 1.18 | 1.14, 1.90 | 1.20, 1.59 | 1.17, 1.48 | 1.11, 1.35 |
| Spanish | 1.17 | 1.17, 2.00 | 1.21, 1.64 | 1.15, 1.47 | 1.06, 1.30 |
| French | 1.26 | 1.17, 1.90 | 1.31, 1.75 | 1.29, 1.58 | 1.17, 1.38 |
| Polish | 1.14 | 1.14, 1.80 | 1.14, 1.55 | 1.12, 1.42 | 1.07, 1.24 |

Three readings matter more than the averages.

- **The tail, not the median, breaks layouts.** A median short string grows by about 15 percent, but one in ten grows by 80 to 100 percent. A button sized for the median fails on those.
- **Long strings grow least.** Sentences over 50 characters grow by 6 to 17 percent at the median, well inside the classic 30 percent.
- **Editing policy shows in the numbers.** The German catalog was reviewed under a rule that compact labels keep the compression of the English, in headline style, without articles or a copula (*Wenn Maske aktiv*, not *Wenn die Maskenebene aktiv ist*). The Polish guide expected Polish growth to be comparable to German; the measured totals agree. French grows most.

These are character counts. A character count is not a width, which is the next problem.

## Characters are not pixels

A string that fits on paper can still fail on screen, for reasons no ratio captures.

1. **Proportional fonts.** *Illegal* and *Wimmelbild* have similar lengths and very different widths. A width limit must be checked in the shipped font at the shipped size.
2. **Scripts and fallback.** Text drawn in a fallback font has different widths and a different line height (chapter [108](108-scripts-direction-and-fonts.md)). The FontLab runtime-review page lists the symptom: accented capitals such as *Ą*, *Ę*, *Ż*, *É* and *Ä* clipped at the top, which points to line height and font metrics rather than to the translation.
3. **Inserted values.** Dr International (2002) advises adding a line of room for each variable in a text box, because the length of the inserted text is unknown. Its example, *Welcome to the %s Registration wizard*, needs the whole first line before the variable is filled.
4. **System settings.** The same book notes that users can scale system fonts and resize dialogs. A layout tested at one scale is tested at one scale.

A translation brief that states a limit must say which unit it uses: bytes, characters, or rendered width in a named font. Chapter [104](104-characters-and-encodings.md) explains why the first two already differ.

## Layout that absorbs growth

The durable answer is a layout that grows, wraps or scrolls, so that translators are not asked to fit text into a fixed box. Dr International's recommendations for Win32 dialogs, and the ten "HTML AutoLayout" rules Microsoft used internally for web interfaces, still read as a checklist for any toolkit:

- **Put labels above fields where possible.** A label beside a field competes with the field for width.
- **Let check boxes and radio buttons wrap.** Otherwise the translator's only option is to leave out information.
- **Never use absolute positions**, and avoid fixed widths; let containers use the available width and height.
- **Keep controls out of the middle of sentences.** An edit box inside a sentence fixes the word order of every language to the English one; the German version in the book's example had to move the box.
- **Do not hide controls behind others.** Localizers may never see them, and sizing problems with them appear only in testing.
- **Put button text on the button.** Text pulled from a shared string variable at run time leaves localizers no way to know which string lands on which button.

When a layout cannot grow, three options remain, in order of preference. Shorten the English, which helps every language at once. Use a shorter translation that keeps the meaning; the FontLab principles give examples such as *Reset to default* becoming *Zurücksetzen*, and German *Pinsel zu Konturen* dropping the verb the reader supplies. Or, as a last resort, use a per-language layout, which Roturier (2015) notes dedicated localization tools made popular and which costs a resize for every release. Truncation with an ellipsis is not an option for labels a user must read to act; it turns a translation problem into a usability defect.

Some panels legitimately allow no growth. The FontLab principles name the Measurements panel: no translation may be longer than the English, the English abbreviations (*UC*, *lc*) are kept, and the target language's standard short forms are used. Where a fixed professional term is one character longer, such as German *Oberlänge* for *Ascender*, the term wins and the exception is recorded.

## A worked example: catching growth before translation

A team preparing its first German, French and Polish release wants to find layout failures before paying for translation. Pseudo-localization does this. The research corpus describes the method: on every build, replace each English string with an expanded, accented version wrapped in visible markers, so that clipped text, untranslated strings and missing glyphs show up at once. Its sample function expands by 40 percent:

```python
def pseudo_localize(text, expansion=0.4):
    """Expand string by ~40% and wrap in visual markers."""
    char_map = str.maketrans('abcdefghijklmnopqrstuvwxyz',
                              'αβčδēƒğħīĵķłмņōρqřšţůvŵχŷž')
    base = text.translate(char_map)
    pad_len = int(len(text) * expansion)
    return f"⟦{base}{'ē' * pad_len}⟧"
```

Two adjustments make it match the evidence above. First, expand by length band rather than by a flat 40 percent: with the FontLab 90th percentiles as a guide, double strings of up to ten characters, add about 60 percent to strings of 11 to 20, and about 40 percent to longer ones. Second, protect message syntax. The sample translates every lowercase letter, so it turns a named placeholder such as `{count}` into garbage and even Qt's `%n` into `%ņ`; only numbered placeholders such as `%1` survive. The FontLab runtime-review page requires a pseudo-localizer that keeps placeholder identifiers, markup and escapes working.

Then walk the application, not the catalog. The runtime-review page lists what to open: every dialog in every state, error paths that produce long assembled messages, context menus with items added at run time, and accessible names that never appear on screen. Record each failure with the build and settings, fix the layout, and rerun the same case. Chapter [706](../7-process/706-pseudo-localization-and-layout.md) covers pseudo-localization as a process, and chapter [510](../5-interface/510-review-in-the-running-app.md) the review of real translations.

The page adds a limit that is easy to forget. Pseudo-localization proves that a layout can hold longer text. It says nothing about natural wording, agreement or terminology, and a label that fits in pseudo-German can still be the wrong German.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 2: user interface)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 7: resizing, the 30 percent rule, HTML AutoLayout, UI controls)
- Johann Roturier, *Localizing Apps*, 2015 (chapter 4: clipped text and custom layouts)
- The FontLab 9 interface catalogs for German, Spanish, French and Polish (`fontlab_de.ts`, `fontlab_es.ts`, `fontlab_fr.ts`, `fontlab_pl.ts`), measured for this chapter
- [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/), [localization/runtime-review](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/runtime-review/) and [localization/pl](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/pl/) in the vexy-fontlab-writing-styleguide repository
