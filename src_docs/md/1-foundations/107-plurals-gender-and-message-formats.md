---
this_file: src_docs/md/1-foundations/107-plurals-gender-and-message-formats.md
---

# 107. Plurals, gender and message formats: CLDR categories, ICU MessageFormat, Qt %n

English gets away with `%n file(s)`. Almost no other language does. A German reader can tolerate *Datei(en)*, a Polish reader faces three different endings that no bracket can hold, and an Arabic reader needs up to six forms. The same is true of gender: English *new* stays *new* whatever it describes, while Spanish, French, Russian and Greek adjectives change with the noun. This chapter explains how software lets translators write correct grammar for every count and every gender without knowing the value in advance. It covers the Unicode categories behind plural selection, the two message systems a desktop and web team meets most often, and the tests that prove a plural works.

## Why a sentence cannot be assembled

Jiménez-Crespo (2024) uses a small string to show the problem: `New %s`, where the program inserts *file*, *font* or *users* at run time. Spanish needs *Nuevo*, *Nueva*, *Nuevos* or *Nuevas* depending on the noun; French needs *Nouveau*, *Nouvelle*, *Nouveaux* or *Nouvelles*; Russian and Greek add a neuter and have, by Jiménez-Crespo's count, six forms before grammatical case enters. A translator who sees only `New %s` cannot choose. Writing all four forms with slashes makes the label longer and uglier. The only real fix is upstream, in how the program asks for the message.

The research corpus puts the rule plainly: never implement plural selection with hand-written conditions in application code, because such code "invariably fails globally". A condition such as `n == 1 ? "file" : "files"` encodes English grammar into the program. The alternative is to hand the whole sentence, with all its variants, to the translator, and let a library choose the variant at run time from the locale's rules.

## CLDR plural categories

Those rules live in CLDR (chapter [105](105-locales-and-cldr.md)). CLDR names up to six plural categories: `zero`, `one`, `two`, `few`, `many` and `other`. Only `other` is required. The names are labels, not numbers, and this is the first thing a translator has to unlearn. `one` in French covers 0 and 1.5 as well as 1; `few` in Polish covers 22 but not 12.

The table below lists the categories each language uses and the category chosen for sample values, as reported by `Intl.PluralRules` in Node.js 26:

| Language | Categories | 0 | 1 | 2 | 5 | 12 | 22 | 1.5 |
|---|---|---|---|---|---|---|---|---|
| English | one, other | other | one | other | other | other | other | other |
| French | one, many, other | one | one | other | other | other | other | one |
| Polish | one, few, many, other | many | one | few | many | many | few | other |
| Russian | one, few, many, other | many | one | few | many | many | few | other |
| Arabic | zero, one, two, few, many, other | zero | one | two | few | many | many | other |
| Japanese | other | other | other | other | other | other | other | other |

The published sources count these differently, and the differences are instructive rather than contradictory:

- **Polish.** The research corpus lists Polish as three or four forms, and explains that the discrepancy is whether `other` is counted separately from `many`. The FontLab Polish guide in the writing styleguide resolves it: `other` exists for fractions, which take the genitive singular (*1,5 pliku*, not *1,5 plików*).
- **Russian.** The research corpus gives three forms; Baldurs (2025) gives four. Both are right: three for integers, a fourth category for fractions.
- **French.** The research corpus gives two forms. Current locale data adds a third category, `many`, which Node assigns to large round numbers such as one million, where French grammar inserts *de* (*un million de fichiers*).
- **Arabic.** Every source agrees on six.

Count categories from the locale data your runtime ships, not from a table in a book, including this one.

The research corpus also records a remark from CLDR itself: in Russian and Arabic, the categories `many` and `other` "should have been swapped when they were defined", but it was too late to change them. A translator filling in Russian `other` is filling in the fraction form, not the ordinary plural.

## Two message systems

**ICU MessageFormat** keeps the whole choice inside one string that the translator edits. The research corpus calls it the dominant cross-platform syntax for over a decade, now retroactively named MF1:

```
{count, plural,
  =0 {No files}
  one {# file}
  other {# files}
}

{gender, select, female {She} male {He} other {They}} replied
```

`#` stands for the formatted number. `=0` matches exactly zero and is independent of whether the language has a `zero` category; the message-contracts page in the styleguide warns against confusing the two. Translators add the categories their language needs: a Polish translator writes `one`, `few`, `many` and `other`.

Its successor, **MessageFormat 2.0** (MF2), comes from the Unicode CLDR Technical Committee. It separates declarations, a `.match` block and explicit variants, and uses `*` as the fallback variant instead of `other`. The research corpus dates its Final Candidate status to early or mid 2025, citing both March 2025 and LDML 46.1, and reports that it was specified but barely adopted: a proposed `Intl.MessageFormat` stood at TC39 Stage 2.7 awaiting production use, while the MF1 adapter for i18next was growing. Its recommendation is to author in MF1 today and treat MF2 as a later migration.

**Qt** takes a different route. The developer passes the count as the third argument of `tr()`, and `%n` in the source text receives it:

```cpp
label->setText(tr("%n message(s) saved", "", n));
```

The translation file then holds one *numerus form* per Qt plural rule for the target language, and the research corpus describes the rules as compiled into the `.qm` file and executed at run time. Qt's forms are not CLDR's categories. The FontLab interface-strings guide gives the Polish case: Qt has three forms (1; 2 to 4 except 12 to 14; the rest), CLDR has four, and Qt has no fraction form because `%n` is an integer. Qt also has no `select` for gender. When a string needs one, the guide's advice is to recast it, choose a verb that does not agree, or ask the developer for one string per case.

One Qt trap concerns the source language itself. If the English `%n file(s)` has no English translation, English users see the literal *file(s)*. The research corpus recommends generating an English catalog that holds only the plural messages; Qt 6 names it with the `PLURALS_TS_FILE` option.

## Gender, ordinals and agreement

Plural rules solve number. Gender and other agreement need either `select` in ICU or separate strings. Jiménez-Crespo describes how the Facebook Translate app handled a message such as `{page-name} has {The number of new posts} new posts`: translators could request variations of each placeholder by gender and by number and write a sentence for each. That is the same idea as `select`, offered as an interface.

Ordinals are a separate rule set. English needs four ordinal forms (*1st*, *2nd*, *3rd*, *4th*), and `Intl.PluralRules` with the option `type: "ordinal"` selects among them. The message-contracts page states the principle: ordinal messages need their own cases.

Three rules from that page belong on every translator's desk:

1. Write full sentences inside each branch, so that agreement and word order can be controlled per case. ICU recommends this.
2. Choose test values from the real input domain. An exported-file count takes whole numbers; a measurement may take fractions.
3. Check the whole rendered message, not just the branch. The right category with a wrong verb is still wrong.

## A worked example: exported glyphs in Polish

The export report from chapter [106](106-numbers-dates-and-units.md) ended with *glyphs* and no plural. The developer changes the code:

```cpp
label->setText(tr("Exported %n glyph(s)", "", count));
```

and adds the message to the English plurals catalog. The Polish translator now fills three numerus forms. The first choice is grammatical: a Polish past-tense verb agrees with its subject, and the subject changes with the count. The impersonal form *wyeksportowano* (it was exported) does not agree with anything, so it removes one variable:

```xml
<message numerus="yes">
    <source>Exported %n glyph(s)</source>
    <translation>
        <numerusform>Wyeksportowano %n glif</numerusform>
        <numerusform>Wyeksportowano %n glify</numerusform>
        <numerusform>Wyeksportowano %n glifów</numerusform>
    </translation>
</message>
```

A web version of the same message in ICU syntax adds the fraction category, which Qt does not need because its count is an integer:

```
{count, plural,
  one {Wyeksportowano # glif}
  few {Wyeksportowano # glify}
  many {Wyeksportowano # glifów}
  other {Wyeksportowano # glifu}
}
```

The FontLab Polish guide lists the values to test in every numerus string, and the Polish rows of the table above predict the result:

| Count | Qt form | CLDR category | Rendered |
|---|---|---|---|
| 0 | third | many | Wyeksportowano 0 glifów |
| 1 | first | one | Wyeksportowano 1 glif |
| 2 | second | few | Wyeksportowano 2 glify |
| 5 | third | many | Wyeksportowano 5 glifów |
| 12 | third | many | Wyeksportowano 12 glifów |
| 22 | second | few | Wyeksportowano 22 glify |
| 25 | third | many | Wyeksportowano 25 glifów |
| 102 | second | few | Wyeksportowano 102 glify |

Twelve is the value that catches most mistakes: it ends in 2 but takes the *many* form. The guide adds one more check for other languages: reject a `one` branch that prints a literal *1* where `one` covers other values, as it does in French. vexy-localizzy enforces the shape of such messages when it reuses them from memory: its memory documentation says a numerus message needs exactly as many forms as Qt defines for the target language, and reports any other count as a finding. Part [5](../5-interface/505-plurals-in-practice.md) returns to plurals as a daily reviewing task.

## Sources

- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 8: placeholders, variables and pluralizations)
- Baldurs L., *TypeScript Internationalization (i18n) and Localization (L10n)*, 2025 (chapter 2: message formatting and pluralization; chapter 6: the complexity of pluralization)
- `research/01-foundations-of-software-localization.md` in the fl10n repository (sections 1.3.2 and 1.4)
- `research/02-localizing-qt-cpp-applications.md` in the fl10n repository (plurals with `%n`, source-language plural catalogs)
- `src_docs/md/localization/message-contracts.md`, `ui-strings.md` and `pl.md` in the vexy-fontlab-writing-styleguide repository
- `docs/memories.md` in the vexy-localizzy repository
- Output of `Intl.PluralRules` in Node.js 26.8.2, run for this chapter
