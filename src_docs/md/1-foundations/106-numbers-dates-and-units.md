---
this_file: src_docs/md/1-foundations/106-numbers-dates-and-units.md
---

# 106. Numbers, dates, currencies and units: display conventions without changing values

A number on screen is two things at once: a value the program computes with, and a string a reader interprets. Localization may change the string. It must never change the value. Most defects in this area come from mixing the two: a date stored as text in one country's order, a price whose currency was guessed from the user's region, a length converted when it should only have been relabelled. This chapter separates value from display for numbers, dates and times, money and units, and shows who does what: the program formats, the locale data decides, and the translator leaves the digits alone.

## Store values, format at the edge

Dr International (2002) states the principle in one sentence: because a world-ready application can never assume the language in which it will display information, all internal data should be stored in a locale-neutral form. Its example is Excel, which stores dates as serial numbers and times as fractions of a day, so that it can compute with them and display them in whatever format the current user has chosen.

Everything else in this chapter follows from that design:

1. Store numbers as numbers, dates as instants or calendar values, money as an amount with a currency code, and measurements in one declared unit.
2. Convert to text only at the moment of display, with a locale-aware formatter.
3. Parse user input with the same locale's rules, and convert it back to the neutral form at once.
4. Keep formatted values out of translation catalogs. A message receives a placeholder; the program fills it with a value formatted for the reader's locale.

The last rule is the one translators notice. Qt marks locale-aware numeric placeholders with an `L`: the research corpus gives `tr("Total: %L1").arg(4321.56)`, which shows `4,321.56` in U.S. English and `4.321,56` in German. The translator writes the words around `%L1` and never the number.

## Numbers

O'Donnell (1994) observed that American software typically hard-codes the comma for thousands and the period for decimals, which fails for most of Europe and South America. Current locale data encodes the differences. The table below was produced by the `Intl.NumberFormat` API in Node.js 26 for the value 1234567.891; other runtimes with other versions of the locale data may differ in detail.

| Locale | Output | Notes |
|---|---|---|
| `en-US` | `1,234,567.891` | comma groups, period decimal |
| `de-DE` | `1.234.567,891` | period groups, comma decimal |
| `fr-FR` | `1 234 567,891` | groups separated by U+202F, a narrow no-break space |
| `pl-PL` | `1 234 567,891` | groups separated by U+00A0, a no-break space |
| `de-CH` | `1'234'567.891` | apostrophe groups, period decimal |
| `en-IN` | `12,34,567.891` | groups of two after the first three |
| `ar-EG` | `١٬٢٣٤٬٥٦٧٫٨٩١` | Arabic-Indic digits and separators |

Three lessons sit in that table. The group separator in French and Polish is a no-break space, so a translator who retypes a number with an ordinary space lets it break across lines. Grouping is not always in threes; Baldurs (2025) lists India's pattern, though its example, `1,23,456`, does not correspond to the value 1,234.56 it claims to illustrate, which shows how easily hand-written examples go wrong. And the digits themselves change: O'Donnell notes that many Middle Eastern countries use digits they call Hindi numbers, and that Thailand has its own.

The per-language guides in the FontLab writing styleguide add the details a formatter's defaults do not settle. The Polish guide records that four-digit numbers are not grouped (`1234`) and that the percent sign follows without a space (`25%`); the French guide records `25 %` with a no-break space and notes that four-digit grouping is common in locale data but often skipped in typographic practice. A reasonable policy, where a guide and a formatter disagree, is to ship the formatter's output and use the guide to tell reviewers which differences to accept.

## Dates and times

Dr International opens its chapter on locales with the date `04/01/02`. In the United States it is April 1, 2002; in the United Kingdom, January 4, 2002; in Hungary, which writes year first, January 2, 2004. Numeric dates are the most ambiguous strings in software, and O'Donnell (1994) lists the other ways dates differ:

- **Names and case.** Month and day names differ by language, and so does capitalization: Danish writes *søndag* and *mandag* in lowercase.
- **Abbreviations.** Taking the first three letters fails for French *juin* and *juillet*, and German abbreviates weekdays to two letters (*So*, *Mo*, *Di*).
- **The first day of the week.** Sunday in the United States, Monday in most of Europe, which changes the layout of every calendar widget.
- **Calendars and eras.** The Islamic calendar has 354 or 355 days and moves against the Gregorian year; the Hebrew calendar adds a thirteenth month in leap years; Japan also counts years by imperial era.
- **Clocks.** Twelve-hour or twenty-four-hour, with different punctuation.
- **Time zones and daylight saving.** Zones differ by thirty or forty-five minutes in some countries, zone abbreviations collide, and the dates of daylight saving differ by country and have changed over time.

O'Donnell's examples of eras stop at Heisei, which began in 1989; Japan has changed era since, which is precisely why era names belong in locale data that is updated, not in application code. The same holds for time zone rules. Store instants in Coordinated Universal Time with the zone they belong to, and let the platform's time zone data decide how to display them.

For display, ask the formatter for a style rather than a pattern. The same date, March 5, 2026, in the `short` and `long` styles of Node.js 26:

| Locale | Short | Long |
|---|---|---|
| `en-US` | `3/5/26` | `March 5, 2026` |
| `de-DE` | `05.03.26` | `5. März 2026` |
| `fr-FR` | `05/03/2026` | `5 mars 2026` |
| `pl-PL` | `5.03.2026` | `5 marca 2026` |

The Polish long form puts the month in the genitive, *marca* rather than the dictionary form *marzec*. A program that assembles a date from a translated month name and a number gets this wrong in every language that inflects; a formatter gets it right because the locale data carries both forms.

## Money and units

A price is an amount and a currency. The reader's locale decides how to write it, not which currency it is. O'Donnell (1994) catalogs the display differences: the symbol before or after the amount (Poland puts it after), different numbers of decimal places (O'Donnell notes that lira and yen amounts were usually written without fractions), and the same `$` sign read as dollars, escudos or cruzados depending on the country. Several of the currencies in that 1994 catalog no longer exist, which makes the point about keeping the code with the amount better than any argument.

Baldurs (2025) shows how easily a program breaks this rule. Its formatter class picks the currency from the user's region with a lookup table, and falls back to U.S. dollars for any region not in the table. A German user sees euros, a Swiss user sees dollars, and in both cases the number has not changed: the price has. The currency code must come from the data, and only the formatting from the locale.

Formatting can also round. Asked to show 1299.5 yen, `Intl.NumberFormat` prints `￥1,300` for `ja-JP`, because the yen has no minor unit. The display is correct; the stored amount was not. Validate amounts against their currency's precision when they are created, not when they are shown.

Units raise a different question: whether to convert at all. O'Donnell (1994) and Dr International (2002) both describe the split between metric units and U.S. customary units, and the paper sizes that follow from it: Letter at 8.5 by 11 inches, A4 at 210 by 297 millimetres. Dr International recalls the Mars probe that went off course in September 1999, partly because of faulty conversions between the two systems, and draws the practical rule: display measurements in the system the user expects, and make clear which system is shown.

Converting a value is a change to data, and it belongs in the program with a stated precision. Relabelling a unit is localization, and it belongs to the translator. Some units do neither. In a font editor, coordinates are in font units relative to the em, and no locale converts them. The FontLab principles page in the writing styleguide translates the *name* of the unit (German *Geviert*, French *cadratin*, Spanish *eme*, Polish *firet*) and leaves every number alone.

## A worked example: an export report

A desktop application ends an export with this message:

```cpp
// formattedDate and formattedFee were produced by the
// locale's date and currency formatters from stored values
tr("Exported %L1 glyphs (%L2 MB) on %3. Licence fee: %4.")
    .arg(glyphCount)
    .arg(sizeMb)
    .arg(formattedDate)
    .arg(formattedFee);
```

A German translation reads:

```
%L1 Glyphen exportiert (%L2 MB) am %3. Lizenzgebühr: %4.
```

Walk through what each party did:

1. **The developer** passed four values, each formatted by the locale at run time. The count and size use `%L`, so a German reader sees `1.234` and `12,5`. The date and price are formatted in code by the locale's formatters and passed as text. The currency comes from the licence record, not from the user's locale.
2. **The translator** moved the placeholders to where German grammar wants them and wrote no digits, no date and no currency sign. A translator who "helpfully" writes `12,5 MB` into the catalog has frozen one value into every export.
3. **The reviewer** checked the running German build with a Swiss formatting locale and saw Swiss number formatting inside German text, which is correct: chapter [105](105-locales-and-cldr.md) explains why the interface language and the formatting locale are separate settings.

One defect remains, and it belongs to the source, not the translation: *glyphs* needs a plural form for one glyph. Chapter [107](107-plurals-gender-and-message-formats.md) takes up that problem.

## Sources

- Sandra Martin O'Donnell, *Programming for the World*, 1994 (chapter 2: numbers, dates, times, money, measurement systems, paper sizes)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 4: locale-neutral storage, date formats, units of measure)
- Baldurs L., *TypeScript Internationalization (i18n) and Localization (L10n)*, 2025 (chapter 2: number, date and currency formatting)
- [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/), [localization/fr](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/fr/) and [localization/pl](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/pl/) in the vexy-fontlab-writing-styleguide repository
- Output of `Intl.NumberFormat` and `Intl.DateTimeFormat` in Node.js 26.8.2, run for this chapter
