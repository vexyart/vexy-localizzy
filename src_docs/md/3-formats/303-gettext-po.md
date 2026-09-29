---
this_file: src_docs/md/3-formats/303-gettext-po.md
---

# 303. Gettext PO: msgctxt, plural headers, fuzzy and the tooling around it

The Portable Object format comes from the GNU gettext project, and it is the oldest format in this part that is still in wide daily use. Roturier (2015) describes PO files as catalogs: text files, one per target language, each holding entries that pair an original string with its translation. An application localized into ten languages keeps ten PO files, plus a template, the POT file, that holds the source strings with empty translations.

PO outlived most of its contemporaries for three reasons. It is plain text, so a person can read it and a version control system can diff it. It carries context, comments and plural forms in one simple syntax. And a large family of tools reads it, from the gettext command-line utilities to the Translate Toolkit, Poedit and most translation management systems. When two tools need a common language and neither speaks the other's native format, PO is often the one they share.

The design of PO makes more sense against what came before it. O'Donnell (1994) describes the X/Open messaging system that most UNIX systems used at the time: a program called `catopen()` to open the catalog for the current locale, `catgets()` to fetch a message by its number, and `catclose()` to close it. The environment variable `NLSPATH` told `catopen()` where to look. Messages were identified by number, and the text lived only in the catalogs.

Gettext keys a message by its source text instead. The English string in code is both the default and the lookup key, so an untranslated message still shows readable text, and a translator sees the English directly in the catalog. The cost is the one Qt also pays: a change to the English text is a change to the key. Chapter [310](310-identity-and-upgrade.md) returns to that cost.

## The anatomy of an entry

This French catalog is a test fixture in the vexy-localizzy repository. It is short, and it contains most of what a real catalog contains:

```po
msgid ""
msgstr ""
"Language: fr_FR\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Plural-Forms: nplurals=2; plural=(n > 1);\n"

msgctxt "menu"
msgid "Open"
msgstr "Ouvrir le menu"

#, fuzzy
msgid "Maybe"
msgstr "Peut-être"

msgid "Untranslated"
msgstr ""

msgid "One file"
msgid_plural "%d files"
msgstr[0] "Un fichier"
msgstr[1] "%d fichiers"

#~ msgid "Obsolete"
#~ msgstr "Obsolète"
```

The first entry, with an empty `msgid`, is the header. Its `msgstr` holds metadata lines: the language, the character encoding and, for any catalog with plurals, the `Plural-Forms` rule. Every following entry is one message. The parts an entry can have:

| Line | Meaning |
|---|---|
| `# text` | A translator comment |
| `#. text` | A comment extracted from the source code for the translator |
| `#: file:line` | A reference to where the string occurs |
| `#, flags` | Flags such as `fuzzy`, `c-format`, `python-brace-format` or `qt-format` |
| `#\| msgid "..."` | The previous source text, kept after a source change |
| `msgctxt` | The context that separates two messages with the same source |
| `msgid`, `msgid_plural` | The source text, singular and plural |
| `msgstr`, `msgstr[n]` | The translation, or one translation per plural index |
| `#~` | An obsolete entry, kept in the file but no longer used |

`msgctxt` is the PO equivalent of Qt's context and disambiguation. Without it, two English strings that are spelled the same are one message with one translation. With it, *Open* in a menu and *Open* as a state can carry different French. When a Qt catalog is converted to PO, the Qt class name goes into `msgctxt`, and the fl10n format notes warn that removing it breaks the round trip back to `.ts`.

## Plural headers are rules, not counts

A plural entry in PO is indexed. `msgstr[0]`, `msgstr[1]` and so on are filled in the order that the header's `plural` expression selects. The expression is a small C-like formula of `n`; `nplurals` says how many indices exist. For French, the fixture and the fl10n plural code both use `nplurals=2; plural=(n > 1);`, which puts 0 and 1 in the singular form. For German and English the rule is `nplurals=2; plural=(n != 1);`, which puts 0 in the plural.

The header is where the sources disagree most visibly. The fl10n format page (`docs/formats/po.md`) lists a three-form French rule and a Russian rule with `nplurals=4`. The fl10n code that writes PO headers (`src/fl10n/cldr.py`) uses two forms for French and three for Russian, and the research synthesis shows the same three-form expression for the Slavic languages. The code's own comment says that `nplurals` matches the number of CLDR categories, which its French and Russian values contradict, since CLDR lists three categories for French and four for Russian. The page and the code cannot both be right for the same catalog, and the comment is wrong about the code beneath it. The practical conclusion is to treat the header as part of the data, check it against the rule your runtime and your other catalogs use, and never let a converter guess it.

Converters do get it wrong. The fl10n research and the fl10n format notes both say that Qt's `lconvert` does not fill in the `Plural-Forms` header when it converts a `.ts` file to PO, and fl10n writes the header itself. A test for this chapter found the behavior narrower than that: `lconvert` from Qt 5.15.19 and from Qt tools 6.11 wrote a header for a `.ts` file whose root declared `language="de_DE"` or `language="pl_PL"`, and wrote none when the `language` attribute was missing. `lupdate` output often lacks that attribute, so the warning holds in practice, but the fix is to set the target language on the `.ts` file, not only to patch the PO. vexy-localizzy goes one step further in the other direction: when it writes a new plural PO file, it requires an explicit rule and checks that every active plural entry has exactly the declared indices, and it refuses to change an existing rule unless the caller acknowledges the change.

## Fuzzy entries and placeholder flags

The `fuzzy` flag marks a translation that a tool proposed and a person has not confirmed. `msgmerge` produces such entries: when an old translation has no exact match in the new template, it uses fuzzy matching to carry the nearest one over, and with `--previous` it keeps the old source in a `#|` line so the translator can compare. A fuzzy entry is a draft, and gettext treats it as one: `msgfmt` leaves fuzzy entries out of the compiled catalog unless you pass `--use-fuzzy`. Other tools should follow the same rule. A fuzzy entry should never count as reviewed and never feed a memory as if it were; the vexy-localizzy memory extractor leaves fuzzy entries out unless you pass `--fuzzy`, and it always leaves out obsolete and untranslated ones.

The format flags tell a checker which placeholder syntax to expect. vexy-localizzy's QA gate follows gettext's own behavior here: an entry flagged `c-format` is checked with `msgfmt --check-format`, `python-brace-format` compares `{name}` fields, `qt-format` checks Qt's `%1` and `%n`, and an entry with no flag gets no placeholder check at all, as with `msgfmt`. That last rule is worth remembering when a PO file comes from a Qt project. The fl10n notes recommend running `pofilter` with `--gnome` on PO derived from Qt sources, because Qt placeholders are not printf specifiers and an unflagged catalog otherwise passes unchecked.

## The tools around PO

| Tool | What it does |
|---|---|
| `xgettext` | Extracts marked strings from source code into a POT template |
| `msginit` | Creates a new catalog and fills its header from the user's environment |
| `msgmerge` | Merges an existing catalog with a new template, using fuzzy matching where no exact match exists |
| `msgfmt` | Compiles a catalog to a binary message catalog; `--check-format` checks format strings |
| `msgcat`, `msgattrib` | Concatenate and merge catalogs; filter entries by attribute such as fuzzy or obsolete |
| Translate Toolkit `pofilter` | Runs more than 40 quality checks over PO files |
| Translate Toolkit `pot2po` | Initializes a catalog from a template with fuzzy matching, replacing `msgmerge` |
| `polib` | A Python library for reading and writing PO files |

The Translate Toolkit converts many other formats into PO so that `pofilter` can check them; [chapter 308](308-conversion-tools.md) discusses when that detour helps and when it loses data.

## Worked example: PO as a projection of a Qt catalog

The FontLab project stores its catalogs as `.ts` files and uses PO only as a projection. The fl10n notes spell out why: PO does not preserve all the fields the project cares about, such as the source hash, the richer state values, the length budget and the separate Qt disambiguation. PO is written for `pofilter` checks and for exchange with tools that want it, and the `.ts` file stays the store.

A projection is safe when it is checked on the way out and on the way back. For a Qt catalog, that means four checks:

1. Every Qt context and disambiguation lands in `msgctxt`, and two messages with the same source and different contexts stay two entries.
2. The header carries the right `Plural-Forms` rule for the target, checked by your tool, not assumed from `lconvert`.
3. Every entry that contains Qt placeholders carries the `qt-format` flag, or the checker is told to expect Qt syntax.
4. On the way back, fuzzy entries return as unfinished, never as finished.

vexy-localizzy adds a stronger guarantee for PO files that are edited rather than projected. Its adapter preserves context, comments, previous text, flags, obsolete entries, encoding and positional plurals, and an unchanged round trip from PO to canonical JSON and back restores the original bytes. The fl10n work log records that all eleven consuming PO catalogs, 53,075 messages, round-tripped byte for byte. That property is what makes a PO file safe to edit by program: nothing the program did not intend to change can change.

## Sources

- Sandra Martin O'Donnell, *Programming for the World: A Guide to Internationalization*, 1994 (chapter 9)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 2.5.1)
- A local test of `lconvert` (Qt 5.15.19 and Qt tools 6.11.2) on `tests/fixtures/legacy_golden/inputs/ts/app_de.ts` from the vexy-localizzy repository
- GNU gettext command help: `msgmerge --help`, `msgfmt --help`, `msginit --help`, `msgattrib --help`, `msgcat --help`
- `research/05-format-conversion-cicd-and-continuous-localization.md` in the fl10n repository
- `docs/formats/po.md`, `docs/formats/ts.md` and `src/fl10n/cldr.py` in the fl10n repository
- [docs/formats.md](../8-toolkit/formats.md), [docs/memories.md](../8-toolkit/memories.md), [docs/extraction.md](../8-toolkit/extraction.md), `WORK.md` and `tests/fixtures/legacy_golden/inputs/po/fr.po` in the vexy-localizzy repository
