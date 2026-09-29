---
this_file: src_docs/md/1-foundations/105-locales-and-cldr.md
---

# 105. Locales and CLDR: language tags, regions, scripts and the data behind formats

Chapter [102](102-what-localization-is.md) defined a locale as the bundle of language and conventions a user expects. This chapter turns the definition into engineering. It explains how locales are named, why one user usually has several of them at once, where the data behind them comes from, and how a program picks the best available translation when it has no exact match. The worked example at the end follows one user through those decisions.

## Naming a locale

Locale identifiers are built from standard codes. Jiménez-Crespo (2024) lists the sources: ISO 639 for languages (two letters where they exist, three letters in its later parts), ISO 3166-1 for countries and regions, and a four-letter code for the script where it matters. On the web and in most modern libraries these are combined as a BCP 47 language tag, which Baldurs (2025) describes as the standard for identifying languages, regions and cultural variations. The parts appear in a fixed order, separated by hyphens:

```
language[-Script][-REGION][-variant]

en-US        English as used in the United States
fr-CA        French as used in Canada
de-CH        German as used in Switzerland
sr-Cyrl      Serbian in Cyrillic script
sr-Latn      Serbian in Latin script
zh-Hans-CN   Chinese, Simplified characters, China
zh-Hant-TW   Chinese, Traditional characters, Taiwan
pa-Guru-IN   Punjabi in Gurmukhi script, India
```

Three details trip people up.

- **Separators differ by platform.** BCP 47 uses hyphens. POSIX-style names, which Qt uses for its translation file names, join the parts with `_`: the research corpus shows `pl_PL` from `QLocale::system().name()` and files named `myapp_de_DE.qm`. Converting between the two is trivial; mixing them in one lookup table is a bug.
- **Codes follow the language's own name, not the English one.** Jiménez-Crespo notes that Croatian is `hr` (from *hrvatski*) and German `de` (from *Deutsch*). The language code for Japanese is `ja`, as in Baldurs's `ja-JP`; `jp` is the country code, and even textbook lists confuse the two.
- **A tag can omit the region.** Microsoft called such a locale *neutral*, as Jiménez-Crespo reports: `es` means Spanish without saying where. A neutral locale can hold translations; it cannot hold formats, because number and date conventions belong to regions.

## One user, several locales

The single most useful idea in Dr International's chapter on locales (2002) is that a user's environment contains several independent locale settings. Windows XP exposed them separately:

| Setting | What it controls | Changed by |
|---|---|---|
| UI language | Language of menus, dialogs and help | The user, on systems with language packs |
| User locale ("Standards and formats") | Dates, times, numbers, currency | The user |
| Input locale | Keyboard layout or input method for typing | The user, per application |
| Location | Country for location-based services | The user |
| System locale | Code page for programs that are not Unicode | An administrator |

The book's scenario is worth retelling because it is ordinary. A Chilean woman lives in the United States. Her location is the United States, because she wants local weather and a national internet provider. Her formats are Spanish (Chile). She also runs a Korean word processor, so she sets a Korean system locale and installs a Korean input method. Her husband, on the same computer, sets his interface language to Spanish. Dr International notes that the user locale is presented as a language but is not a language setting: choosing Hebrew as the user locale means Israeli conventions, not the Hebrew language, which is why .NET renamed it *culture*.

The distinction survived every change of platform. The research corpus documents a bug that KDAB described in 2020 and that recurs in Qt applications: loading the translation file named after `QLocale::system().name()`, which is the *formatting* locale, instead of the user's list of interface languages from `QLocale::uiLanguages()`. A Polish engineer who formats numbers the Polish way but prefers an English interface gets Polish menus. On the web the same split appears between the browser's language list, which chooses the translation, and the region used by `Intl` formatters. Two questions, two settings:

1. *Which language should the interface speak?* Answer from the user's ordered list of interface languages.
2. *Which conventions should the data follow?* Answer from the user's formatting locale.

## CLDR: the data behind the formats

Once a program knows the locale, it needs data: the decimal separator, the order of day and month, the currency symbol, the plural rules, the sort order. Nobody should type that data into application code. Dr International (2002) makes the case for the operating system's tables, noting that a great deal of linguistic research went into them and that using them saves "a lot of trips to the library". Windows XP supported over 135 locales at the time.

Today the shared source is the Unicode Common Locale Data Repository (CLDR). The research corpus describes it as the canonical database of how each of more than 700 locales formats numbers, dates and currencies, and which plural categories each language uses. The JavaScript `Intl` API exists so that libraries need not ship CLDR data over the network, Qt's `QLocale` plays the formatting role on the desktop, and the corpus's rule is blunt: rely on the platform's formatter and never ship a custom one. When a tool calls itself "CLDR-correct", it means its behavior comes from this repository.

CLDR covers more than formats, and two operations are easy to overlook because they look like plain string handling.

- **Casing depends on the language.** Dr International gives three cases: German *ß* uppercases to *SS*, Turkish lowercase *i* uppercases to a dotted capital while English *i* takes the dotless one, and Chinese, Japanese, Korean, Arabic, Hebrew and Thai have no case at all. It adds that capitalizing the Russian word for Wednesday turns it into "environment".
- **Sorting depends on the language.** The same book notes that Swedish sorts some accented vowels after *Z* while other European languages sort them beside the unaccented vowel. The Polish guide in the writing styleguide records that *ń* sorts immediately after *n* and that every Polish letter with a diacritic is a letter of its own.

The opposite need exists too. When a program compares internal identifiers, such as preference keys, it must not apply any language's rules. Dr International's example is a Hungarian user locale in which *sc* is a special letter combination, so a case-insensitive comparison of two registry names fails only on Hungarian systems. The fix was an *invariant* locale for internal comparisons. The general rule follows from it: store and compare data in a locale-neutral form and apply a locale only when showing it to a person. Excel's serial numbers for dates are the book's illustration.

## Fallback: choosing the nearest translation

A program rarely ships a catalog for every locale a user might request, so it needs a fallback chain. Qt's `QTranslator::load()` overload that takes a `QLocale` walks the user's interface languages and tries progressively shorter names. The research corpus gives the order for a German user:

```
myapp_de_DE.qm  ->  myapp_de.qm  ->  myapp.qm
```

It also records a version detail: in Qt 5 up to 5.15.2 the search order was buggy (QTBUG-86179), fixed in Qt 6.0.1 and 5.15.3.

Fallback by truncation works for regions, where a German catalog is a reasonable answer for `de-AT`. It is dangerous for scripts. Baldurs (2025) illustrates fallback with a small class whose compatibility test compares the language and, when both tags have one, the region. The test ignores the script. Given `zh-Hans` and `zh-Hant` without regions, it reports them compatible, although a reader of Traditional Chinese given Simplified characters has received the wrong text. A sound chain treats the script as part of the language: a request for `sr-Latn-RS` may fall back to `sr-Latn`, but never to a catalog named plain `sr` that holds Cyrillic text, unless the product has decided which script the plain code means.

Write the chain down as a product decision rather than leaving it to a library default. For each shipped catalog, record which requested locales it may answer, and test that a user who asks for a locale you do not ship lands where you intended.

## A worked example: one user, three answers

A type designer in Zurich runs a desktop application that ships catalogs for English, German, French and Polish. Their system reports:

```
interface languages:  de-CH, en-US
formatting locale:    de-CH
keyboard:             Swiss German
```

The application has to answer three questions, and each answer comes from a different setting.

1. **Interface.** The first interface language is `de-CH`. There is no Swiss German catalog, so the chain tries `de` and finds it. They see the German interface. If a later version adds Swiss spelling changes as `app_de_CH`, the same chain picks it up without code changes.
2. **Formats.** Dates, numbers and currency follow `de-CH` from the platform's locale data, not from the German catalog. A translator in Germany never sees these values, and need not: they are produced at run time by the formatter, as chapter [106](106-numbers-dates-and-units.md) explains.
3. **Keyboard.** Shortcuts and mnemonics must be typeable on their layout. The catalog chose them for German; the review in the running application, on a machine set to their keyboard, confirms they work. Part [5](../5-interface/504-mnemonics-shortcuts-and-keys.md) covers the rules.

Now change one setting. A colleague in the same office prefers English menus but Swiss formats. The colleague's interface list becomes `en-US, de-CH` and the formatting locale stays `de-CH`. An application that derives the catalog from the formatting locale shows German menus: the KDAB bug again. An application that keeps the two questions apart shows English menus with Swiss dates, which is exactly what the settings ask for.

## Sources

- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 4: locale variables, casing, sorting and string comparison)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 2, box 2.1: locales)
- Baldurs L., *TypeScript Internationalization (i18n) and Localization (L10n)*, 2025 (chapter 2: the anatomy of locale identifiers)
- `research/01-foundations-of-software-localization.md` in the fl10n repository (section 1.3: CLDR and `Intl`)
- `research/02-localizing-qt-cpp-applications.md` in the fl10n repository (section 2.3.4: loading the right language)
- `src_docs/md/localization/pl.md` in the vexy-fontlab-writing-styleguide repository
