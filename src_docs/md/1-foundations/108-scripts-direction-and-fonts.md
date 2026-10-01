---
this_file: src_docs/md/1-foundations/108-scripts-direction-and-fonts.md
---

# 108. Scripts, text direction and fonts: bidi, shaping and rendering

Chapter [104](104-characters-and-encodings.md) ended at the code point. A reader never sees code points. Between the stored string and the pixels on screen, software decides the order in which characters appear, which shape each one takes, where lines break and which font supplies each glyph. For Latin, Greek and Cyrillic text most of these decisions are trivial, so an English-speaking team can ship for years without noticing they exist. For Arabic, Hebrew, the Indic scripts, Thai and the East Asian scripts, each decision can break a translation that is linguistically perfect. This chapter explains the concepts a localization team needs to plan for those scripts. The engineering is in Part 2: chapter [208](../2-engineering/208-mirroring-and-rtl.md) covers mirrored interfaces and chapter [209](../2-engineering/209-rendering-and-opentype.md) covers OpenType rendering.

## Writing systems differ in more than letters

O'Donnell (1994) surveys the world's scripts and the properties that matter to software. Some are alphabets, like Latin and Cyrillic. Arabic and Hebrew write mainly consonants. Japanese mixes two syllabaries with Chinese ideographs, and Dr International (2002) defines a *script* in exactly this sense: one script can serve many languages, and one language can need several scripts.

The same survey shows how direction varies:

| Direction | Scripts and languages | Note from the sources |
|---|---|---|
| Horizontal, left to right | Latin, Cyrillic, Greek, most Indic scripts | The default most software assumes |
| Horizontal, right to left | Arabic, Hebrew | Digits inside still run left to right |
| Vertical, right to left columns | Chinese, Japanese | Horizontal is the norm in the PRC and for technical text in Japan (O'Donnell, 1994) |

That last row corrects a common simplification. Baldurs (2025) sketches a direction manager that sets Chinese, Japanese and Korean to vertical layout by default. O'Donnell's account points the other way: horizontal writing had become the norm in mainland China, and Japanese technical text is almost always horizontal, with vertical text kept for newspapers, novels and similar material. An application interface is technical text. Vertical layout is a feature to offer where users need it, not a default to derive from a language code.

The same sketch derives direction from the language subtag alone. Direction belongs to the script. Punjabi, listed by Jiménez-Crespo (2024) as both `pa-Guru-IN` and `pa-Arab-PK`, runs left to right in Gurmukhi and right to left in Arabic script. A lookup keyed on `pa` gets one of them wrong.

## Bidirectional text

Right-to-left scripts are really bidirectional. O'Donnell gives the Hebrew case: letters run right to left, numbers left to right, so a sentence about *Casablanca* released in 1942 must not display 2491. Arabic numbers appear left to right as well. Any interface in these languages also contains left-to-right material: file names, product names, URLs, code.

Dr International (2002) explains the consequence for software. The *logical order*, in which text is stored and typed, differs from the *visual order* in which it is shown. The Unicode bidirectional algorithm computes the visual order in the absence of other information, and the book summarizes its assumptions: runs of opposite direction are laid out according to the paragraph's base direction; digits run left to right; commas and periods between digits belong to the number; punctuation between runs of opposite direction sits between those runs; punctuation at the start or end of a paragraph follows the paragraph direction. The book calls the algorithm a "surprisingly successful stab" at ambiguous text, sufficient for forms and databases, while word processors give users more control.

Two practical rules follow for localized interfaces.

1. **Set the base direction from the interface language.** The research corpus names the switches: `dir="rtl"` on the HTML root element with CSS logical properties such as `margin-inline-start`, and `QGuiApplication::setLayoutDirection(Qt::RightToLeft)` in Qt, which also flips layouts, scroll bars and header order. Qt's text engine applies the bidirectional algorithm automatically.
2. **Isolate inserted values.** When a program inserts a left-to-right file name into a right-to-left sentence, the neutral characters at its edges, such as a closing parenthesis or a trailing period, can attach to the wrong run and appear on the wrong side. The research corpus notes that bidirectional isolation, which prevents an inserted value from reordering the sentence around it, is built into MessageFormat 2.0 and into well-designed formatters. Unicode provides control characters for the purpose, such as U+2068 FIRST STRONG ISOLATE and U+2069 POP DIRECTIONAL ISOLATE, which wrap a value and keep its direction to itself.

## Shaping, clusters and line breaks

Several scripts change a character's shape according to its neighbors. O'Donnell (1994) notes that most Arabic letters have four forms, isolated, initial, medial and final, while only five Hebrew consonants have a second, final form. O'Donnell adds that Latin case is the same idea driven by grammar instead of position. Dr International (2002) draws the engineering conclusion: there is one code point per letter, and the rendering system must choose the glyph at run time from the font's tables. A program that stores or measures glyph shapes instead of characters, or splits a word between two styled runs, breaks the joining.

In Indic scripts several characters can combine into one glyph, and the reverse happens too. Dr International gives examples: four Hindi characters become one indivisible cluster with one glyph; two Tamil characters become a cluster of three glyphs; two Arabic characters become one glyph that can still be divided. The cursor must jump over an indivisible cluster, and deletion must remove it as a unit. Code-point counts from chapter [104](104-characters-and-encodings.md) do not predict any of this.

Line breaking and justification differ as well. Thai and Khmer write words without spaces, so line breaking needs grammatical analysis and dictionaries; the research corpus notes that Qt 6 breaks Thai lines with an ICU dictionary engine. Arabic justification cannot stretch spaces between letters without destroying the joins; it inserts connecting strokes called *kashidas* instead (Dr International, 2002).

All of this is the job of a shaping engine, not of the application. The research corpus identifies HarfBuzz as the engine inside Qt; in 2002 Dr International described Microsoft's Uniscribe in the same role. The application's duty is to hand whole strings to the text system and not to second-guess it.

## Fonts: coverage, fallback and metrics

"Fonts are the final form in which multilingual data is displayed to the user," Dr International (2002) observes, and the observation carries three planning problems.

**Coverage.** Few fonts cover many scripts. In 2002 even Arial Unicode MS, one of the most complete Windows fonts, did not contain all of Unicode, and the core OpenType fonts left out East Asian scripts because thousands of ideographs would make them several times larger. The research corpus gives the modern planning figure for an embedded full-coverage font:

**1 to 20 MB per script.**

It also recommends broad families such as Noto Sans, Source Han Sans for East Asian text, and Noto Naskh or Amiri for Arabic.

**Fallback.** When the chosen font lacks a script, the system substitutes another. Dr International describes both mechanisms Windows used: *fallback*, in which the text system switches internally to a predefined font, and *linking*, in which extra fonts are attached to a base font. Its example: Tahoma covers Latin and Hebrew, so Telugu typed in Tahoma is drawn in Gautami. Fallback prevents empty boxes; it does not guarantee a good result.

**Metrics.** A substituted font keeps the point size of the original, and the book notes that three nominally 8-point fonts can differ widely in the actual size of their letters. Line heights set for one script clip another. The FontLab Polish guide in the writing styleguide records a small instance of the same problem: the accented capitals *Ą*, *Ę* and *Ż* clip at tight line heights and must be checked at every interface size.

The research corpus's rule for all three is short: do not hard-code font families in the interface, and let the platform's fallback chain work with fonts chosen for coverage.

## A worked example: adding Arabic and Polish to a Latin interface

A desktop tool ships in English and German. Its interface uses a custom Latin font chosen by the brand designer, set at a fixed line height. The product team adds Polish and Arabic. Before any translator starts, walk the rendering path for each language.

1. **Coverage.** Polish needs *ą ć ę ł ń ó ś ź ż* and their capitals. Check that the brand font contains them; if not, every Polish label will mix two fonts. Arabic needs a font with Arabic glyphs and joining tables; the brand font almost certainly has none, so name an Arabic companion font rather than relying on whatever the system falls back to.
2. **Metrics.** Arabic letters and Polish accented capitals both extend beyond the Latin font's usual vertical space. Replace the fixed line height with one derived from the fonts in use, or test the tallest glyphs at the smallest interface size.
3. **Direction.** Arabic switches the application's base direction to right to left. The layout mirrors, which is engineering work described in chapter [208](../2-engineering/208-mirroring-and-rtl.md). Check that direction is chosen from the interface language's script, not from a list of language codes.
4. **Inserted values.** Every message that inserts a file name, a glyph name or a number into an Arabic sentence needs isolation. Search the catalog for placeholders and list the messages; the list is the Arabic reviewer's first test plan.
5. **Shaping.** Confirm that no code draws labels character by character, truncates strings by glyph count, or applies letter spacing to Arabic text. Each of these breaks joining that the shaping engine would otherwise get right.
6. **Review.** Look at every Arabic and Polish screen in the running application. The research corpus adds one easily missed surface: accessible names read by screen readers must be localized too, or the user hears mixed languages.

None of these steps involves a translation choice. Together they decide whether a translation can be read at all, which is why they belong at the start of the project rather than at its end.

## Sources

- Sandra Martin O'Donnell, *Programming for the World*, 1994 (chapter 2: scripts, context dependency, text direction)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 1 glossary; chapter 5: complex scripts, bidirectionality, shaping, clusters, line breaking, fonts, fallback and linking)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 2, box 2.1: locales with scripts)
- Baldurs L., *TypeScript Internationalization (i18n) and Localization (L10n)*, 2025 (chapter 2: text direction and layout)
- [localization/pl](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/pl/) in the vexy-fontlab-writing-styleguide repository
