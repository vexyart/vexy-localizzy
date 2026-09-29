---
this_file: src_docs/md/8-toolkit/legacy-sources.md
---
# Legacy source projections

`legacy_pairs.ts_pairs(root)` and `legacy_pairs.po_pairs(po, fuzzy=False)` provide
the explicit selection rules used by existing TMX extraction commands. They
return ordered `(source, target, context, plural)` tuples. They leave duplicate
rows in place so the caller can apply its existing deduplication policy.

Qt input is a parsed ElementTree `TS` root. The projection visits messages within
contexts, strips the context name, and excludes missing/empty sources and targets
marked unfinished, obsolete or vanished. Plurals use the first and last nonempty
`numerusform`; a single form produces one `singular` row. Both use the same source.

Gettext input is a parsed `polib.POFile`. Obsolete, empty-source and untranslated
entries are excluded. Fuzzy entries require `fuzzy=True`. Indexed plural forms
are sorted; the first emits the singular source and the last emits `msgid_plural`.
Empty end forms are omitted independently. Context and text retain their whitespace.

These are compatibility projections, not complete catalog conversions. Middle
plural forms and other native metadata do not appear in the resulting tuples;
Qt byte escapes and length variants are not interpreted by this historical rule.
Use `formats.ts`, `formats.po` and `conversion.convert()` for complete native
catalog handling and explicit loss reporting. Locale normalization, resource
discovery, provenance and destination paths remain caller policy. Feed selected
records to `memory.tmx_write.write_records()` for atomic XML serialization.

The input contracts were checked against the official
[Qt TS schema](https://doc.qt.io/qt-6/linguist-ts-file-format.html) and
[polib API](https://polib.readthedocs.io/en/latest/api.html). Attribution for the
adapted compatibility rules is retained in `NOTICE`.

## Apple resource values

Install `vexy-localizzy[sources]` for `apple_resources.parse_strings_text(bytes)`.
It returns ordered key/value pairs, retaining duplicate keys, whitespace and
comment delimiters inside quoted values. UTF-8 (with optional BOM) and BOM-marked
UTF-16 are supported. Invalid syntax/encoding raises instead of returning partial
or replacement-character text. Comments outside strings are omitted.

`resource_items(bytes)` additionally reads binary/XML property lists, retaining
nested native values and dictionary order. `flatten_value(key, value, device="mac")`
projects nonempty strings, format strings and all plural categories into ordered
pairs with `key|variable|category` identifiers. Device dictionaries prefer the
requested device and then `other`. This is an explicit extraction projection;
keep original bytes for native editing and full device coverage.

These APIs do not discover installed applications, normalize language folders,
choose source-language fallbacks or assign provenance. The caller supplies those
policies and retains the original resource path. The text parser is the published
[OpenStep parser](https://github.com/fonttools/openstep-plist); XML/binary decoding
uses [plistlib](https://docs.python.org/3/library/plistlib.html).

## Fluent resources

With the sources extra, `fluent_resources.parse_ftl(text)` yields ordered
`(key, text)` pairs for messages, terms (prefixed `-`), and `.attribute` values.
Select-expression branches append `[key]`, except default branches, which have
no suffix. Nested suffixes and multiple selectors preserve historical expansion
order. Whitespace is collapsed, while variable/function/reference expressions
remain serialized Fluent syntax. Repeated IDs remain available to the caller's
duplicate policy; comments are omitted. Keep the original resource for editing.

Malformed entries raise `ValueError` before the first resource pair is emitted.
`flatten_pattern(pattern, max_variants=10000)` and `parse_ftl` accept a positive
integer per-pattern limit. Expansion exceeding it raises before that Cartesian
product is allocated; no variants from the failing pattern are yielded. Earlier
valid patterns may already have been yielded, so callers must finish iteration
before publishing output. Directory discovery, source/target joining and locale
fallback remain caller policy.

## Properties resources

With the sources extra, `properties_resources.parse_properties(text)` returns all
ordered key/value pairs, including duplicate keys and empty values. The caller
decodes bytes and chooses a duplicate policy. The published Java-style parser
handles escaped separators, whitespace, Unicode surrogate pairs and odd/even
backslash continuation rules. It preserves trailing value whitespace and rejects
malformed Unicode escapes before returning any pairs. This API implements Java
properties syntax; Mozilla-specific properties/DTD extraction uses the API below.

## Mozilla properties and DTD

`mozilla_resources.parse_mozilla(text, kind)` accepts `properties` or `dtd` and
returns ordered key/value pairs from published moz.l10n. It keeps duplicate and
empty values for caller policy. Properties escapes and continuations are decoded;
valid UTF-16 surrogate pairs become Unicode characters, while isolated surrogates
raise. Unknown escapes follow Mozilla syntax, which differs from strict Java
properties (for example, `\uNOPE` becomes `uNOPE`).

DTD reference spelling stays literal (`&amp;`, numeric references and references
to other entries). Commented-out declarations are omitted. DTD include declarations
are not translation entries and are never fetched; retain the original source
files to preserve their metadata. Unsupported/unparsed content raises before any
pairs return. This is a localization DTD projection, not a general DTD processor:
moz.l10n 0.14.2 also rejects comment delimiters inside quoted entity values.
Resource discovery, locale aliases and source pairing remain caller policy.
