---
this_file: src_docs/md/8-toolkit/extraction.md
---
# Extract translation-memory pairs

`localizzy tm extract INPUT OUTPUT` produces a plain-text TMX from selected bilingual
records. It was `localizzy extract` before the CLI grouped the memory builders under
`tm`; the Python entry point is `vexy_localizzy.extract.single.extract`. It uses the explicit [legacy source projections](legacy-sources.md).
For native catalog editing and complete metadata preservation, use `convert`.

```sh
localizzy tm extract translations/de.po memory/de.tmx
localizzy tm extract translations/de.ts memory/de.tmx
localizzy tm extract translations/de.po memory/de.tmx --fuzzy
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
localizzy tm extract catalog.ts memory.tmx --source_lang=en --target_lang=de
```

Apple `.strings`/`.stringsdict`, Fluent `.ftl` and Java-style `.properties` files need the sources extra,
a reference source file and an explicit target language:

```sh
localizzy tm extract de/Localizable.strings memory.tmx --source=en/Localizable.strings --target_lang=de
localizzy tm extract de/messages.ftl memory.tmx --source=en/messages.ftl --target_lang=de
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

The output path is required. Output aliases of either input, including symbolic
and hard links, are rejected. Extraction and XML serialization finish before an
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
localizzy tm extract de/messages.properties memory.tmx --source=en/messages.properties --target_lang=de
```

Mozilla DTD files are recognized by `.dtd`; Mozilla properties syntax requires
`--source_format=mozilla-properties`, because `.properties` defaults to Java syntax.
Both use strict UTF-8 with an optional BOM, exact key joining, last-key selection
and no plural fallback. They require a reference source file and target language.
DTD reference spelling stays literal; includes are omitted from translation
entries without reading external resources. See [parser limits](legacy-sources.md#mozilla-properties-and-dtd).

```sh
localizzy tm extract de/dialog.dtd memory.tmx --source=en/dialog.dtd --target_lang=de
localizzy tm extract de/messages.properties memory.tmx --source=en/messages.properties --target_lang=de --source_format=mozilla-properties
```

Apple `.loctable` files contain multiple language tables in one binary or XML
plist. Select a pair explicitly; a separate `--source` file is not accepted:

```sh
localizzy tm extract Localizable.loctable memory.tmx --source_lang=en --target_lang=de
localizzy tm extract Localizable.loctable memory.tmx --source_key=Base --target_key=German --source_lang=en-US --target_lang=de-DE
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
localizzy tm extract de/strings.json memory.tmx --source=en/strings.json --target_lang=de
```

Extraction uses strict UTF-8 with an optional BOM. Object and array roots are
supported. String leaves join by typed JSON path, so `["a.b"]`, `["a","b"]`,
`["items",0]` and `["items","0"]` are distinct. Paths appear in `x-context`
and unmatched-key reports. Non-string leaves and empty pairs are omitted; values
retain whitespace. There are no UI-text filters or plural-suffix fallbacks.
Duplicate object keys, malformed JSON and unpaired Unicode surrogates are refused.
For explicit alternate decoding or application-specific filtering, use
`extract.json_resources.string_pairs(text)`, which returns all ordered string leaves,
including empty values, paired with tuples of string keys and integer indices.
It uses the [standard JSON decoder](https://docs.python.org/3/library/json.html)
with the same strict object/constant hooks as native i18next editing. `convert`
continues to use canonical JSON for full catalog interchange; `tm extract` reads
ordinary keyed resources.

## Legacy tree converters

`tm extract` reads one file with a strict policy. The legacy converters moved
from fl10n walk whole trees and keep the old tools' behaviour exactly, including
their language policy: regions are shortened by their own default-region table,
the language falls back to the file name stem and XML-illegal characters are
stripped. Golden parity tests compare them with the old scripts'
output (`tests/fixtures/legacy_golden`).

```sh
localizzy tm ts2tmx translations/ --output tmx/
localizzy tm po2tmx po/ --output tmx/ --fuzzy
localizzy tm lproj2tmx /Applications/App.app tmx/app/ --skip-identical
localizzy tm adobe2tmx "/Applications/Adobe App" tmx/adobe/ --ui-lang en_US
localizzy tm oss2tmx tmx/oss/ --apps inkscape,gimp
localizzy tm norm tmx/ --dry-run
```

`tm norm` renames each `.tmx` to its shortest BCP 47 tag with
`memory.names.plan_folder()`; see [formats](formats.md#legacy-tmx-file-names).
The converters exit 1 when any file failed. `oss2tmx` and `norm` need the
`sources` extra. `oss2tmx` clones the upstream repositories listed in the
packaged `oss_apps.toml` (or `--registry`) into `--cache`, by default
`OUTPUT/_src`, and reuses them unless `--refresh` is given. Run `localizzy tm COMMAND --help` for every flag, or see the
[CLI reference](cli.md).

