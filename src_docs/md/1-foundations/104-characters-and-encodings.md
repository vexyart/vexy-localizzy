---
this_file: src_docs/md/1-foundations/104-characters-and-encodings.md
---

# 104. Characters and encodings: Unicode, normalization and what a string is

A translator rarely thinks about bytes, and a developer rarely thinks about diacritics. Localization breaks at the point where the two meet: a catalog saved in the wrong encoding, a memory lookup that misses because one letter was typed two ways, a length check that counts bytes where a reader counts letters. This chapter explains the few ideas that prevent those failures. It does not teach the Unicode Standard; it teaches what a localization engineer needs to decide about text before any translation happens.

## What a character is

O'Donnell (1994) points out that the question is harder than it looks. Most people see *ö* as one letter, although it is drawn as an *o* and a diacritic, because the diacritic means nothing on its own. In Arabic the base letters are consonants and some of the marks above and beside them are vowels; there the same visual arrangement is usually treated as two characters. Whether something is one unit or several depends on the writing system and on the operation: sorting, cursor movement, deletion and counting can each give a different answer.

Software needs a firmer definition, so it separates three layers.

| Layer | What it is | Example for *ń* |
|---|---|---|
| Code point | A number the Unicode Standard assigns to an abstract character, written U+ and hex digits | U+0144, or U+006E followed by U+0301 |
| Code unit | The fixed-size piece an encoding uses to store code points | one 16-bit unit in UTF-16; two bytes in UTF-8 |
| User-perceived character | What a reader counts as one letter | one *ń*, whichever way it is stored |

A fourth layer, the glyph a font draws, belongs to rendering and is covered in chapter [108](108-scripts-direction-and-fonts.md). Most text bugs in localized software come from code that confuses two of these layers.

## From seven bits to Unicode

The confusion has a history. O'Donnell (1994) recounts how ASCII fixed American English into seven bits, enough for English, Swahili and Hawaiian and for no other language, and how national variants under ISO 646 replaced some ASCII characters with local letters. In the French variant the curly brackets became accented letters, which is awkward in a language such as C that uses curly brackets for every block. Eight-bit code pages followed: each kept ASCII in the lower half and assigned the upper 128 positions differently (chapter [103](103-a-short-history.md) lists the DOS pages). East Asian languages, with thousands of characters, used double-byte and multibyte schemes such as Shift-JIS, GB2312 and Big5, in which some characters take one byte and others two (Roturier, 2015).

Unicode replaced these with one repertoire. Dr International (2002) describes a code space of more than 1.1 million code points divided into 17 planes of 65,536 each. Plane 0, the Basic Multilingual Plane, holds most characters of modern scripts. The standard defines three encoding forms:

| Encoding | Code unit | Characters take | Where it is used |
|---|---|---|---|
| UTF-8 | 8 bits | 1 to 4 bytes; ASCII stays one byte | Files, the web, network protocols |
| UTF-16 | 16 bits | one unit, or two for characters beyond Plane 0 (a *surrogate pair*) | Windows NT internals and .NET in 2002 |
| UTF-32 | 32 bits | one unit | Doubles the data size; Dr International (2002) advises against choosing it only to avoid surrogates |

The advice about which to use has shifted. In 2002 Microsoft recommended UTF-16 as "the fundamental representation of text" in an application and UTF-8 only for exchanging data with other systems, while already calling UTF-8 "the best and safest approach for multilingual Web pages". By 2015 Roturier describes UTF-8 as the preferred encoding for the web. The research corpus of 2026 treats UTF-8 as the default even for C++ sources: its Qt migration plan includes enforcing UTF-8 source files and removing calls to the Qt 5 function `trUtf8()`. The practical rule for localization files is now simple. Store catalogs, memories and glossaries in UTF-8, declare it where the format allows, and treat any other encoding as an import problem to solve once at the boundary.

Two older details still surface. XML processors must accept both UTF-8 and UTF-16 (Dr International, 2002), so an XLIFF or TS file may legally arrive in either. And some editors write a byte-order mark at the start of a file to identify the encoding; the same book notes that Notepad did so. A byte-order mark that a parser does not expect shows up as an invisible character in the first message of a catalog.

## One letter, two spellings: normalization

Unicode encodes many accented letters twice. *à* exists as a single precomposed code point, and it can also be written as *a* followed by a combining grave accent. Dr International (2002) explains why: the precomposed forms exist mainly for compatibility with older character sets, while combining marks allow any letter to take any diacritic without a code point for each combination. The standard defines which sequences are equivalent.

To a reader the two spellings are identical. To a program they are different strings of different lengths, and they compare unequal. Normalization converts text to one agreed form. The form that composes where it can is called NFC, and it is the one localization data should use. The FontLab interface-strings guide in the writing styleguide states the rule directly: type diacritics as precomposed characters (NFC), because decomposed forms and presentation ligatures such as *ﬁ* and *ﬂ* break search, sorting and glyph lookup.

Normalization is also where a toolkit has to be honest about what it compares. vexy-localizzy's memory lookup documents its choice in `docs/memories.md`: sources match verbatim, and only NFC and the conversion of Windows line endings to Unix line endings are applied before comparison, so case, spacing, punctuation, accelerators and placeholders all count. Its fuzzy matcher for catalog upgrades, described in `docs/upgrade.md`, is looser by design and also folds case and whitespace. The difference is deliberate: an exact match may be reused without review, so it must not treat two strings as equal unless a reader would.

## What a string is, and how long

Once the layers are separate, the question "how long is this string?" has several correct answers, and a localization pipeline has to choose the right one for each purpose.

Roturier (2015) gives an example with a five-character Japanese word saved as UTF-8. Read as bytes, it is 15 long; decoded, it is 5. Python confirms the arithmetic:

```python
>>> len("ありがとう")
5
>>> len("ありがとう".encode("utf-8"))
15
```

The same word would be 5 units in UTF-16, because all five characters are in the Basic Multilingual Plane. A character outside that plane, such as an emoji, is one code point but two UTF-16 units, and a user-perceived character built from a base and combining marks is one letter but several code points. JavaScript exposes the last distinction through `Intl.Segmenter`, which splits text into graphemes, words or sentences; the research corpus notes that it reached all major browsers only in April 2024, when Firefox 125 shipped it.

Each count has its use:

- **Bytes** matter for storage limits, network payloads and file formats that declare sizes.
- **Code units** are what most programming languages return from their length function, and what a buffer is sized in.
- **Code points** are what normalization, regular expressions and most text APIs operate on.
- **User-perceived characters** are what a translator is told when a label has a maximum length, and what cursor movement and deletion should respect.

A character limit in a translation brief that does not say which count it means is not a limit. Chapter [109](109-space-and-growth.md) adds the one that matters most for layout: rendered width, which no character count predicts.

## A worked example: a Polish word that will not match

A translator reviewing a Polish catalog corrects the label for a delete command to *Usuń*. The memory already contains *Usuń* as an approved translation, yet the next automated run reports no match, the placeholder check passes, and the string's length is reported as five characters instead of four. Nothing looks wrong on screen.

The cause is the *ń*. The translator's input method produced *n* followed by U+0301 COMBINING ACUTE ACCENT, while the memory holds the precomposed U+0144. The strings differ in every layer except the one a reader sees:

```python
>>> import unicodedata
>>> a = "Usuń"      # precomposed ń
>>> b = "Usuń"     # n + combining acute accent
>>> a == b
False
>>> len(a), len(b)
(4, 5)
>>> len(a.encode("utf-8")), len(b.encode("utf-8"))
(5, 6)
>>> unicodedata.normalize("NFC", b) == a
True
```

Three fixes apply, at three places:

1. **At input.** Normalize every translation to NFC when it enters the catalog or memory. A pipeline that compares after normalizing, as vexy-localizzy's memory lookup does, then finds the match.
2. **At storage.** Keep the stored form NFC, so that search, sorting and the running application see what the reviewer saw. The Polish guide in the styleguide requires this for *ą ę ł ż ś ć ń ó ź*.
3. **At display.** Check that the font renders both forms identically. If the application ever receives decomposed text from a user, a font without the combining mark positioned correctly will show the accent beside the letter instead of above it.

The same word shows the older failure too. Written in UTF-8 and read as Windows-1252, the two bytes of *ń* appear as two unrelated Latin characters, the familiar garbage that translators call mojibake. Roturier's warning applies: when a file is saved in an encoding that differs from the one the localization guidelines specify, the damage appears later in the workflow. Declare the encoding, normalize once, and count what the reader counts.

## Sources

- Sandra Martin O'Donnell, *Programming for the World*, 1994 (chapter 4: encoding characters)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 3: Unicode, encoding forms, surrogate pairs, precomposed characters, byte-order marks)
- Johann Roturier, *Localizing Apps*, 2015 (section 2.3: encodings)
- `research/01-foundations-of-software-localization.md` in the fl10n repository (section 1.3.3 and the staged Qt migration)
- `src_docs/md/localization/ui-strings.md` and `src_docs/md/localization/pl.md` in the vexy-fontlab-writing-styleguide repository
- `docs/memories.md` and `docs/upgrade.md` in the vexy-localizzy repository
