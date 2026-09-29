---
this_file: src_docs/md/2-engineering/204-placeholders-and-grammar.md
---

# 204. Placeholders and grammar: variables, ordering, agreement and the no-concatenation rule

Most messages contain something the program knows only at run time: a file name, a count, a font family, a date. How the program combines that value with translated text decides whether a translator can write a grammatical sentence at all. The rule is old and nearly universal: never build a sentence from translated fragments; translate the whole sentence and mark where each value goes. This chapter explains why the rule exists, how placeholders make it work, what a placeholder does to grammar, and where the rule is still broken in code that looks correct.

## Why fragments fail

Every source on this subject has its own example, and they fail in the same way. Dr International (2002) quotes a deletion prompt built in three parts:

```c
"Are you sure you want to delete the " + szDelObject + "?"
```

The translator sees "Are you sure you want to delete the" and nothing else. French needs *le* or *la*, German one of three genders, and the choice depends on the noun in `szDelObject`, which arrives later and in English grammar. The same book's second example is a string meant to save storage, "The [flood gate/control rods/exit door] cannot be [closed/open/reset]", which covers nine sentences with one template and gets verb forms wrong for every noun of a different gender or number. O'Donnell (1994) shows "No rights to" joined to "open", "delete" or "file %s", where "to" is an infinitive marker in two uses and a preposition in the third. Roturier (2015) shows a web page heading assembled from "Your latest", "NBA" and "headlines": the gender of "Your latest" cannot be chosen without the noun, and French wants the order *titres NBA*, not *NBA titres*.

The Qt research gives the word-order case in its plainest form. English says "5 of 10 files copied"; Norwegian says, in effect, "of a total of 10 files, 5 are copied". A program that builds the English from pieces cannot produce the Norwegian at all.

Fragments also defeat the tools. Dr International notes that the parts of a split sentence are rarely adjacent in the resource table, so a translator translates them word by word, and translation memory cannot match them against earlier whole sentences. Its German back-translation of a split check-box label, "When this controlbox checked is, -plays...", shows the result.

## Mark where the value goes

The fix has two parts: keep the sentence whole, and let each value have an identity so that the translator can move it. Anonymous placeholders solve only the first part. Dr International's Finnish example makes the point: the English "Not enough memory to %s the file %s." needs the verb after the file name in Finnish, and with two identical `%s` markers the translator cannot say which is which. Numbered markers fix it: "%1 the file %2" becomes "...tiedoston %2 %1."

C gained the same ability in the 1990s. O'Donnell describes the X/Open extension of `printf` and `scanf` with positional parameters such as `%1$s` and `%2$d`, required in catalog entries with more than one value, so that translators can reorder the values in the catalog without touching the code. Roturier's advice goes one step further: prefer named markers, because a name tells the translator what the value is.

> "Relying on identical substitution markers (such as three %s on lines 4 and 12) is useless because it is not possible to express the fact that one %s should be moved to a different location in the final string." (Roturier 2015)

| System | Marker | Reorderable? | Notes |
|---|---|---|---|
| C `printf` | `%s`, `%d` | No | Positional `%1$s` exists in X/Open and gettext |
| Python | `%(name)s`, `{name}` | Yes | Named markers carry meaning |
| Qt | `%1` to `%99`, `%L1`, `%n` | Yes | `%n` is the plural count; `%L1` formats a number for the locale |
| .NET | `{0}`, `{1:N2}` | Yes | Index plus optional format |
| ICU MessageFormat | `{name}`, `{count, plural, ...}` | Yes | Selection logic lives inside the message |
| i18next | `{{name}}` | Yes | Escaped by default |

A placeholder moves grammar out of the code only if the translator knows what it stands for. Dr International asks developers to document every possible value of a variable. The FontLab writing guide gives the reason in one example: "%1 to %2" may be a date range, a copy destination or a numeric span, and each needs a different preposition in German or Polish. Which value fills `%1` is fixed by the code; the translator can move it but cannot swap two values because the target reads better.

Some values should never be placeholders in prose. Dr International quotes a message template `"%d:%d%s on %s, %s %d, %d"`, a time and date assembled from seven variables that the programmer then had to explain to translators, who still could not translate "on". The fix is to keep the date as a date and hand it to a locale-aware formatter, which knows the order, separators and names for each language ([106](../1-foundations/106-numbers-dates-and-units.md)). The same applies to numbers: in Qt, `%L1` asks for the locale's grouping and decimal separator, so `tr("Total: %L1").arg(4321.56)` prints `4,321.56` for American English and `4.321,56` for German.

## What a placeholder does to agreement

A placeholder that stands for a noun breaks agreement with everything around it. The FontLab guide's examples are "This is not a valid %1" and "%1 already exists. Replace it?": the adjective *valid* and the pronoun *it* depend on the gender, and sometimes the case, of a noun the message never sees. German, French, Spanish and Polish all inflect for it. There are four honest remedies, in order of preference:

1. **Recast as label and value.** "%1: invalid value" or "Invalid value: %1" keeps the noun out of the sentence's grammar.
2. **Choose words that do not agree.** A verb phrase often avoids the adjective entirely.
3. **Ask for one message per case.** If the program knows the kind of object, it can select a complete sentence: ICU's `select` argument exists for this ([107](../1-foundations/107-plurals-gender-and-message-formats.md)).
4. **Report the source string.** When none of these fits, the defect is in the code, and a guessed gender will be wrong for some values.

Counts are the special case of the same problem. Never add "s" in code, and never choose between two strings with `if (n == 1)`: most languages have more categories than English, and the category boundaries differ. In Qt, pass the count as the third argument of `tr()` and use `%n`; in ICU, use a `plural` argument. [505](../5-interface/505-plurals-in-practice.md) and [506](../5-interface/506-placeholders-and-agreement.md) take both problems through the translator's side.

Controls embedded in sentences are agreement in disguise. Dr International shows an edit box placed in the middle of an English sentence, which the German localizer had to reposition because German puts the words around it in a different order; the book's advice is to redesign the dialog so that the control sits outside the sentence. A drop-down list inside a sentence adds gender and case to the word-order problem.

## Assembly that still happens

The rule is widely known and still broken, usually in code that joins a translated prefix to a translated or untranslated value. The FontLab guide lists the signs a reviewer sees in the catalog: a trailing space, a string that is plainly the first half of a sentence, a label that ends without its object. German, which puts the verb last, and Polish, which marks case on the noun, cannot survive that assembly. When the prefix cannot be reordered, a colon rescues the grammar, as in the German *Widerrufen: Ausschneiden* for an Undo item followed by the command name, and the source review records the fragment for the developers. Code may also append punctuation, so a reviewer who adds a final period in the translation can produce two.

Qt adds a trap of its own. A chain of `.arg()` calls substitutes one placeholder at a time:

```cpp
// Vulnerable: if fileName contains the text "%2", the second .arg() replaces it too.
label->setText(tr("Copying %1 to %2").arg(fileName).arg(folderName));

// Correct: the multi-argument overload substitutes all placeholders at once.
label->setText(tr("Copying %1 to %2").arg(fileName, folderName));
```

The research corpus documents the bug: when the first value contains a literal `%2`, the second call replaces both the real and the injected marker. The multi-argument overload resolves the placeholders in one pass and avoids temporary strings. The fl10n source audit reports the chained form as a minor finding (`FL-ARG-006`) and concatenated translatable fragments as another (`FL-CONCAT-007`); both are described with the other detectors in [205](205-qt-instrumentation.md). Note the order of substitution when a plural is involved: `tr()` replaces `%n` first, then `.arg()` fills `%1`, so `tr("%n of %1 file(s) copied", "", done).arg(total)` is correct.

Markup inside a message is the web version of the same problem. Storing raw HTML in translation files invites cross-site scripting and assumes translators write correct markup. The research corpus recommends component interpolation with numbered tags, as in react-i18next's `<Trans>`, where the catalog holds `"I agree to the <1>Terms</1>."` and the component supplies the link ([207](207-web-and-typescript.md)).

## Checking placeholders automatically

Because placeholders are syntax, they can be checked without reading the language. The deterministic check compares the placeholders in source and target: the same identifiers, the same number of occurrences, nothing mutated. Localizzy's default Qt policy checks exact multiplicity of `%1`, `%L1`, `%n` and `%Ln` and lets numbered arguments move; C `printf` formats are checked by GNU `msgfmt`, including positional parameters. The FontLab guide adds the limit of any such check: a parser that counts braces or tags cannot prove that a message with nested choices is valid. Use the target platform's own parser for that, and remember that a syntactically perfect placeholder can still sit in an ungrammatical sentence.

## Sources

- Sandra Martin O'Donnell, *Programming for the World: A Guide to Internationalization*, 1994 (chapter 9, variable parameter order and message fragments)
- Dr International, *Developing International Software*, second edition, 2002 (chapter 2, programmers' tricks; chapter 7, string handling and UI controls in sentences)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (chapter 2, concatenation; chapter 3, avoiding concatenation)
- `research/01-foundations-of-software-localization.md`, `research/02-localizing-qt-cpp-applications.md` and `research/03-localizing-web-javascript-applications.md` in the fl10n repository
- `spec/02.md` in the fl10n repository
- [localization/ui-strings](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/ui-strings/) and [localization/message-contracts](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/message-contracts/) in the vexy-fontlab-writing-styleguide repository
- [docs/quality.md](../8-toolkit/quality.md) in the vexy-localizzy repository
