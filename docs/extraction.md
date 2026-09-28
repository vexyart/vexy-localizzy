---
this_file: docs/extraction.md
---
# Extract translation-memory pairs

`localizzy extract INPUT OUTPUT` produces a plain-text TMX from selected bilingual
records. It uses the explicit [legacy source projections](legacy-sources.md).
For native catalog editing and complete metadata preservation, use `convert`.

```sh
localizzy extract translations/de.po memory/de.tmx
localizzy extract translations/de.ts memory/de.tmx
localizzy extract translations/de.po memory/de.tmx --fuzzy
```

TS requires a `TS` root and selects finished translations with first/last plural
forms. PO excludes obsolete, untranslated and (by default) fuzzy entries. Duplicate
source/target/context triples collapse unless `--dedupe=False` is supplied. PO
encoding is detected by polib rather than forced to UTF-8. Context and plural
labels are retained in TMX properties; text is literal, including markup.

Languages come from TS `sourcelanguage`/`language`, PO `X-Source-Language`/`Language`,
or explicit `--source_lang` and `--target_lang`. Source language defaults to `en`;
a missing target language is an error. Tags are canonicalized without dropping
regions: `de_DE` becomes `de-DE`. No language is inferred from filenames. To match
a consumer that deliberately shortens default regions, pass its chosen language
codes explicitly:

```sh
localizzy extract catalog.ts memory.tmx --source_lang=en --target_lang=de
```

Apple `.strings`/`.stringsdict`, Fluent `.ftl` and Java-style `.properties` files need the sources extra,
a reference source file and an explicit target language:

```sh
localizzy extract de/Localizable.strings memory.tmx --source=en/Localizable.strings --target_lang=de
localizzy extract de/messages.ftl memory.tmx --source=en/messages.ftl --target_lang=de
```

Resources join by key, never row position. Apple duplicate keys use the first
value; Fluent duplicate IDs use the last, matching the existing source adapters.
A Fluent target selector missing in the source may use the source's default
variant. A generated Apple plural category may use `other`; ordinary string keys
are never interpreted as plural categories. Unmatched keys are returned in the
command report. Apple device projections currently prefer `mac`, then `other`.
These are extraction policies, not runtime message evaluation.

The result contains `output`, `units`, `selected_pairs`, `source_lang`,
`target_lang` and `unmatched_keys`. `selected_pairs` is counted before duplicate
removal. Each TU records `x-origin`; paired resources also record `x-source-origin`.
Paths retain caller paths after tilde expansion. Use project-relative input paths
for compact portable provenance, and keep the source files with their manifest.

Input format normally comes from the extension; `--source_format=po` (or `ts`,
`strings`, `stringsdict`, `loctable`, `json`, `ftl`, `properties`, `mozilla-properties`, `dtd`) overrides it explicitly. Fuzzy selection applies
only to PO. Bilingual catalogs do not accept a separate reference source.

The output path is required. Output aliases of either input—including symbolic
and hard links—are rejected. Extraction and XML serialization finish before an
atomic output replacement; parsing failures or forbidden XML characters preserve
an existing output. Invalid text is rejected rather than silently sanitized.
The command handles one catalog pair at a time. Application discovery, language
folder aliases and recursive output planning remain consumer policy.

Properties files are decoded as strict UTF-8 with an optional BOM. Escaped keys,
Unicode surrogate pairs and continued lines follow Java properties syntax; trailing
value whitespace is retained. The last occurrence of a key wins, including empty
values. Empty source/target pairs are omitted. There is no plural fallback for
properties keys. For other encodings, decode explicitly and use
`properties_resources.parse_properties(text)`; it returns all ordered pairs.

```sh
localizzy extract de/messages.properties memory.tmx --source=en/messages.properties --target_lang=de
```

Mozilla DTD files are recognized by `.dtd`; Mozilla properties syntax requires
`--source_format=mozilla-properties`, because `.properties` defaults to Java syntax.
Both use strict UTF-8 with an optional BOM, exact key joining, last-key selection
and no plural fallback. They require a reference source file and target language.
DTD reference spelling stays literal; includes are omitted from translation
entries without reading external resources. See [parser limits](legacy-sources.md#mozilla-properties-and-dtd).

```sh
localizzy extract de/dialog.dtd memory.tmx --source=en/dialog.dtd --target_lang=de
localizzy extract de/messages.properties memory.tmx --source=en/messages.properties --target_lang=de --source_format=mozilla-properties
```

Apple `.loctable` files contain multiple language tables in one binary or XML
plist. Select a pair explicitly; a separate `--source` file is not accepted:

```sh
localizzy extract Localizable.loctable memory.tmx --source_lang=en --target_lang=de
localizzy extract Localizable.loctable memory.tmx --source_key=Base --target_key=German --source_lang=en-US --target_lang=de-DE
```

Table names are exact raw keys, defaulting to the supplied language codes (`en`
for the source). `--source_key` and `--target_key` select tables independently of
the output language tags. No Base fallback or language-name alias is guessed.
`LocProvenance` and non-dictionary metadata are omitted. Apple plural/device
projection and unmatched-key reporting follow the same rules as paired resources;
both origin properties identify the one input file. The Python helper
`apple_resources.loctable_tables(data)` exposes ordered raw tables to consumers
that need their own locale policy.

Keyed `.json` resources require a reference source and explicit target language:

```sh
localizzy extract de/strings.json memory.tmx --source=en/strings.json --target_lang=de
```

Extraction uses strict UTF-8 with an optional BOM. Object and array roots are
supported. String leaves join by typed JSON path, so `["a.b"]`, `["a","b"]`,
`["items",0]` and `["items","0"]` are distinct. Paths appear in `x-context`
and unmatched-key reports. Non-string leaves and empty pairs are omitted; values
retain whitespace. There are no UI-text filters or plural-suffix fallbacks.
Duplicate object keys, malformed JSON and unpaired Unicode surrogates are refused.
For explicit alternate decoding or application-specific filtering, use
`json_resources.string_pairs(text)`, which returns all ordered string leaves,
including empty values, paired with tuples of string keys and integer indices.
It uses the [standard JSON decoder](https://docs.python.org/3/library/json.html)
with the same strict object/constant hooks as native i18next editing. `convert`
continues to use canonical JSON for full catalog interchange; `extract` reads
ordinary keyed resources.
