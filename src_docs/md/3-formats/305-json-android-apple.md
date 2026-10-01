---
this_file: src_docs/md/3-formats/305-json-android-apple.md
---

# 305. JSON, Android XML and Apple strings: the application formats

The formats in the previous three chapters are catalogs: files designed for translation, with a source and a target side by side. The formats in this chapter are resources. An i18next JSON file, an Android `strings.xml` and an Apple `.strings` file are what the running application loads. Each holds one language. The English file and the German file are separate, and they are joined only by their keys.

That single-column design changes the work. A translator never sees a source and a target in one file unless a tool builds the pair. Context is whatever the key and the file layout say. Review state has nowhere to live, because a runtime has no use for it. And every format carries runtime conventions, such as escaping rules, references to other resources and plural suffixes, that a translation tool must preserve exactly or the application breaks. Jiménez-Crespo (2024) describes the mobile side of this: Android and iOS keep a separate set of resource files per locale, which lets translators share one memory across them, but the strings reach localizers as XML or XLIFF, often without context, and guidelines have to supply length limits for small screens.

## i18next JSON: keys, suffixes and interpolation

i18next is the JSON format the research corpus discusses in most detail, and its file is a plain JSON object whose leaves are strings. Keys can nest. Variables are interpolated with double braces. Plurals are sibling keys that share a base name and end in a CLDR category, a scheme the research describes as the result of the move from i18next v3 to v4, when the old `_plural` suffix gave way to suffixes driven by `Intl.PluralRules`. The vexy-localizzy tests use this resource:

```json
{
  "menu": {"open": "Open {{ user.name }}", "empty": ""},
  "items_one": "{{count}} item",
  "items_other": "{{count}} items",
  "items_zero": "No items",
  "rank_ordinal_one": "{{count}}st", "rank_ordinal_two": "{{count}}nd",
  "friend_male_one": "A friend", "friend_male_other": "Friends"
}
```

Three conventions are packed into the keys. `_one` and `_other` are cardinal plural categories. `_ordinal_one` and `_ordinal_two` are ordinal categories, the ones that give "1st" and "2nd". `_male` is a context, i18next's way of letting one base key carry variants such as a verb and a noun sense. A tool that treats the keys as opaque strings sees six unrelated messages. A tool that parses them sees three messages, one of which has two dimensions.

The FormatJS and Lingui libraries use a different model: one key per message, with the plural logic inside the string as ICU MessageFormat, for example `{count, plural, one {# item} other {# items}}`. The research gives both forms side by side ([chapter 107](../1-foundations/107-plurals-gender-and-message-formats.md) explains the ICU syntax). Converting between them is not a rename; it moves the plural structure from the key into the value.

JSON has no comments and no metadata. The research lists that as its main weakness, and it is why the key has to carry the context. Its comparison of web formats still recommends JSON as the pragmatic default, one file per locale with a flat key namespace per module, and names the alternatives by what they add: YAML allows comments, Mozilla's Fluent `.ftl` gives translators an expressive grammar at the cost of limited tool support, PO fits pipelines that are already gettext-based, and XLIFF belongs in transport to a translation management system, never in the runtime. The same research warns that i18next's own v3 to v4 migration tool handles only keys that use the default `_` separator, which is one reason it recommends converting into i18next late in a pipeline rather than using it for exchange. The research recommends structured keys such as `checkout.button.submit` for any project with more than two languages, more than one translator or a lifetime longer than six months, and it records that its sources disagreed on how strongly to recommend them.

## Android string resources

An Android `strings.xml` is XML with its own rules. This fixture from the vexy-localizzy tests shows most of them:

```xml
<resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2"
           xmlns:tools="http://schemas.android.com/tools">
<string name="quoted">"  Exact   spacing  "</string>
<string name="escape">It\'s \"open\"\nŁ\q</string>
<string name="styled">Hello <b>bold</b>, <xliff:g id="person">%1$s</xliff:g>!</string>
<string name="fixed" translatable="false">Constant</string>
<string name="reference">@string/open</string>
<plurals name="items"><item quantity="one">%d item</item><item quantity="other">%d items</item></plurals>
<string-array name="choices"><item>First</item><item>Second</item></string-array>
</resources>
```

Each line is a trap for a naive tool:

| Construct | What a tool must do |
|---|---|
| Quotes around a value | Keep them: they tell Android to preserve the whitespace inside |
| `\'`, `\"`, `\n`, `Ł` | Keep the escapes; Android decodes them at build time |
| `<b>` | Keep the styling markup as markup |
| `<xliff:g>` | Protect the enclosed token; the translator moves it but does not change it |
| `translatable="false"` | Leave the resource out of translation |
| `@string/open` | Leave the reference alone; it points to another resource |
| `<plurals>` with `quantity` | Keep one `<item>` per CLDR category the target language needs |
| `<string-array>` | Keep the number and order of items; the application reads them as a list |

Positional placeholders such as `%1$s` let a translator reorder arguments. The research adds one runtime quirk that is easy to forget in review: `getQuantityString()` takes the count twice, once to choose the plural category and once to fill the `%d`.

Android plurals use category names, like i18next and unlike Qt or gettext. That makes them safer to convert between CLDR-based formats and harder to convert to positional ones, because a tool must know the target language's category order to place `few` and `many`. [Chapter 307](307-the-canonical-model.md) shows how vexy-localizzy refuses to guess that order.

## Apple strings, stringsdict and string catalogs

Apple platforms have used three generations of resource files. A `.strings` file holds key and value pairs in a quoted text syntax. A `.stringsdict` file is a property list that adds plural and device variants for keys that need them. The research describes the newest, the `.xcstrings` string catalog, as a JSON-based catalog with built-in plural and device variants, an extraction state and annotations for comments. When a project goes to translators, Jiménez-Crespo describes Xcode exporting the strings as XLIFF inside an `.xcloc` localization catalog folder, one per locale, and importing the translated XLIFF back. Interface text also lives in the `.xib` and `.storyboard` files, including the launch screen, and the App Store description and in-app purchase texts need localizing as well.

Plurals in Apple XLIFF follow a convention of their own. According to one research report, Apple encodes the `.stringsdict` structure in the XLIFF unit ids, with a `key:variable:dict` pattern marking the plural variable and nested segments naming the category. A tool that ignores the convention sees each category as a separate string.

vexy-localizzy reads Apple resources for building translation memories, not for editing them. Its documentation is explicit about the policies such reading requires: `.strings` files are read as UTF-8 or as BOM-marked UTF-16, duplicate keys keep the first value, plural categories and device variants are flattened into `key|variable|category` identifiers, and the Mac variant is preferred over the generic one. It calls these extraction policies, not runtime evaluation, and tells callers to keep the original files for editing.

## Pairing single-column files

Because each file holds one language, any bilingual use starts by pairing two files. vexy-localizzy's memory extractor states the rule that makes pairing reliable: resources join by key, never by row position. Keys that exist in only one file are reported, not silently dropped. For JSON, keys are typed paths, so `["a.b"]` (one key containing a dot) and `["a","b"]` (a nested key) are different messages, and `["items",0]` addresses an array element. The same typed paths serve the i18next editor, where a colliding plain key and plural base get a `plural:` prefix to stay distinct.

The discipline matters because the alternative fails quietly. An earlier exporter in the FontLab tooling wrote a flat JSON map keyed by English source text. Its own documentation lists the cost: two Qt messages with the same source and different contexts collapsed into one key, context, state, notes and length limits were dropped, and only the `other` plural form was written. The page tells readers to use that JSON only as read-only output for a web view, never as a backup or an interchange format. That was the right warning for that exporter, and it is the reason the later adapter keeps nesting, arrays and plural suffixes intact.

## Worked example: translating one Android file

Suppose you receive `values/strings.xml` in English and must produce `values-de/strings.xml`. The steps that keep the application working are these:

1. Parse the resources as Android does, not as generic XML text, so that quoting and escapes are decoded into what the user will see.
2. Offer the translator the decoded text with `<xliff:g>` tokens and styling markup shown as protected codes.
3. Skip `translatable="false"` resources and references entirely.
4. For each `<plurals>`, produce the categories German needs, `one` and `other`, not the English count by habit.
5. Encode the translation back with Android's quoting and whitespace rules, and check that every protected token and placeholder identity survived.
6. Compile with the Android tools before merging.

vexy-localizzy implements steps 1 to 5 in its Android adapter and records the limits of what it checked: 24 adapter tests and four comparison cases against native AAPT2 compilation, which its work log calls synthetic validation, not device or full-format coverage. Loading a resource file projects its values as source text, English by default; the locale belongs to the directory layout and the calling application. Step 6 remains yours.

## Sources

- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 11)
- [docs/formats.md](../8-toolkit/formats.md), [docs/extraction.md](../8-toolkit/extraction.md), [docs/legacy-sources.md](../8-toolkit/legacy-sources.md), `WORK.md`, `tests/test_android_formats.py` and `tests/test_i18next_formats.py` in the vexy-localizzy repository
