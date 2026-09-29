---
this_file: src_docs/md/2-engineering/209-rendering-and-opentype.md
---

# 209. Rendering text: OpenType features, fallback fonts and complex scripts

A translated string is not finished when it is correct in the catalog. It still has to become shapes on a screen, and between the characters and the shapes lie font selection, fallback, shaping, positioning and line breaking. For Latin text most of that is invisible. For Arabic, Devanagari, Thai or Korean it decides whether the text is readable at all. This chapter explains what a program must leave to the text engine, what it must not assume about fonts, and how to recognize a rendering defect when you see one. The script-level facts it builds on are in [104](../1-foundations/104-characters-and-encodings.md) and [108](../1-foundations/108-scripts-direction-and-fonts.md).

## Four units that are not the same

O'Donnell (1994) separated two ideas that software of her time often confused: a code set is how a program represents characters internally, and a font is how it shows them. A glyph is a character's shape in a particular font. The FontLab writing guide sharpens the distinction into four units, and most rendering bugs come from treating one as another:

| Unit | What it is | What depends on it |
|---|---|---|
| Code point | A numbered position in Unicode | Storage, encoding, comparison after normalization |
| Grapheme cluster | What a reader perceives as one character; may be several code points | Cursor movement, selection, deletion, truncation |
| Glyph | A shape in a font, chosen and positioned by the shaper | Display, width, line height |
| Shaping cluster | The group of source characters that maps to a group of glyphs | Hit testing, caret placement inside ligatures |

The guide adds that a shaping cluster need not coincide with a grapheme cluster, so cursor movement, selection and deletion have to be checked separately. Dr International (2002) gives the ratios that make this concrete: simple Latin text maps one character to one glyph, a ligature maps several characters to one glyph, and Indic scripts map several characters to several glyphs in a different order, with no alignment inside the cluster. It mentions Hindi, where four characters can become one glyph, and Tamil, where two characters can become three.

## Shaping: from characters to positioned glyphs

Dr International calls a script complex when its characters are not laid out in a simple left-to-right sequence, and lists the traits: bidirectional ordering, contextual shaping, combining characters, word breaking without spaces, and special justification. Arabic letters take isolated, initial, medial and final forms with one code point for all four, so the glyph is chosen at run time from the font's tables. Thai and Khmer put no spaces between words, so line breaking needs a dictionary. Arabic is justified by lengthening the joining strokes, called kashidas, because inserting spaces would break the joins.

The book describes the Windows engine of its time, Uniscribe, as a pipeline that is still the shape of every modern text engine: divide the text into items of one script and direction, shape each item into clusters and glyphs, place the glyphs, then draw them. The application keeps the text in logical order and never changes its stored characters as a result of layout. In Qt the research corpus names HarfBuzz as the shaping engine, and Thai line breaking in Qt 6 as handled by an ICU dictionary engine. The application's duty is the same as in 2002, and Dr International states it as three requirements for complex-script output:

1. **Draw whole runs.** Drawing character by character loses the context that shaping and reordering need.
2. **Measure shaped text.** A shaped string can be shorter or longer than the sum of its characters' widths; ask the text engine for the width of the run.
3. **Set the direction.** Right-to-left runs need right-to-left reading order and alignment ([208](208-mirroring-and-rtl.md)).

Here is the worked example, from the book's chapter on OpenType. In Devanagari, the consonant Ra (U+0930) followed by the virama (U+094D), which cancels the consonant's inherent vowel, at the start of a syllable is written as a reduced form, the reph, placed above a later letter of the cluster. The font carries a substitution lookup that replaces the two glyphs with one reph glyph; the shaping engine first reorders the characters, then applies the lookup. Suppose a label contains a Hindi word with a reph. A program that measures the label by adding the advance widths of its characters counts a full Ra and a visible virama; the shaped run contains neither, only the reph mark on another letter. The measured box is wrong, the text is misaligned, and a truncation routine that cuts by character count can cut between the Ra and the virama and produce a broken cluster. Measuring the shaped run and truncating at grapheme boundaries avoids both errors.

## OpenType layout

OpenType, which Microsoft and Adobe first released in 1997 as an extension of TrueType, carries the rules that shaping applies. Dr International lists five layout tables:

| Table | Purpose |
|---|---|
| `GSUB` | Glyph substitution: single, alternate, ligature, one-to-many and contextual |
| `GPOS` | Glyph positioning: single and pair adjustment, cursive attachment, mark attachment, contextual positioning |
| `GDEF` | Glyph classes: base, ligature, mark |
| `BASE` | Baseline offsets for lines that mix scripts |
| `JSTF` | Justification, including white space and kashidas |

Inside `GSUB` and `GPOS`, data is organized from script to language system to feature to lookup, and scripts, language systems and features are identified by four-character tags. A feature is a named set of rules; some are required for a script to be readable at all, like the reph above, and others are typographic choices a user may switch on. The engine applies them in a fixed order:

> "If a glyph string needs to be both substituted and positioned, substitution is always done prior to any positioning operation." (Dr International 2002)

Two consequences matter to localization engineers. First, the tags are identifiers. An interface that lists OpenType features, as a font editor does, may translate the description of a feature but must keep the tag exact; the FontLab guide puts OpenType tags on its list of strings that are not text. Second, font coverage does not guarantee behavior: a font can contain every Devanagari code point and still lack the lookups that form conjuncts, and the guide warns against inferring script support from one screenshot.

## Fonts, fallback and what not to assume

Dr International gives four rules for font selection that have aged well: do not hard-code a face name, do not assume a font is installed, do not assume a font covers the script, and do not hard-code the size, because scripts need different pixel grids to be legible. Its figures for bitmap-era screens were about 5 by 7 pixels for English, at least 16 by 16 for Japanese and 24 by 24 for Chinese. The research corpus repeats the first rule for today's toolkits and suggests broad-coverage fallback families, such as Noto, Source Han Sans for Chinese, Japanese and Korean, and Noto Naskh or Amiri for Arabic, with a budget of 1 to 20 MB per script for a full-coverage embedded font.

When the chosen font lacks a character, the text engine falls back to another font, and Windows 2000 added font linking, which attaches extra fonts to a base font. Both prevent empty boxes; neither chooses well. Dr International warns that fonts of the same nominal point size can differ widely in real letter size, and draws the conclusion:

> "Font fallback and font linking are no substitutes for choosing the right font in the first place." (Dr International 2002)

The FontLab runtime review describes the same risk in modern terms: fallback may remove an empty box while introducing a different baseline, weight or language form, so inspect the fonts that actually supply the glyphs at the shipped size and display scale. The same code points can also need different glyphs in different languages, so text should carry language metadata, such as the HTML `lang` attribute, wherever the platform supports it. On the web, Dr International's advice to keep fonts in one stylesheet class per script, instead of inline styles scattered through pages, is the same idea as a font stack defined once per language.

Line height is a font decision with a localization symptom. Latin capitals with marks above, such as the Polish *Ż*, the French *É* or the German *Ä*, rise above the English capitals a layout was designed around, and the ogonek of the Polish *Ą* and *Ę* hangs below the baseline. The runtime review lists a capital with a clipped diacritic among the symptoms to check first, against line height, the actual font's metrics and the clipping area.

## Recognizing rendering defects

A symptom on screen points to a place to investigate, not to a cause. Combining the symptom lists of the FontLab runtime review and Dr International's world-readiness chapter with the shaping requirements above gives a short diagnostic table:

| On screen | Check first |
|---|---|
| `????` in place of letters | The original data and each encoding conversion; a character was lost |
| Accented junk such as `Ã¤` | The bytes and the encoding used to decode them |
| Empty boxes | Glyph coverage of the selected font, and fallback |
| Letters present but unjoined, or marks misplaced | Shaping: whole-run drawing, the font's layout tables, the engine |
| A clipped accent on a capital | Line height, font metrics and the clipping rectangle |
| Words broken in the wrong place in Thai or Japanese | Segmentation and line-breaking rules, not the translation |

Check the unit, not only the picture. The FontLab guide asks reviewers to test caret movement, selection, Backspace and Delete separately, with a combining mark, a supplementary character and a ligature, because a glyph count is not a character count. A defect in any of these is an engineering defect, and correcting the translation will not fix it.

## Sources

- Dr International, *Developing International Software*, second edition, 2002 (chapter 5, complex scripts, displaying text and fonts; chapter 11, recognizing problems; chapter 20, OpenType fonts)
- Sandra Martin O'Donnell, *Programming for the World: A Guide to Internationalization*, 1994 (chapter 7, fonts and display)
- `research/01-foundations-of-software-localization.md` and `research/02-localizing-qt-cpp-applications.md` in the fl10n repository
- `src_docs/md/global/scripts-and-typography.md`, `src_docs/md/localization/runtime-review.md` and `src_docs/md/localization/ui-strings.md` in the vexy-fontlab-writing-styleguide repository
