---
this_file: src_docs/md/8-toolkit/formats.md
---
# Catalog formats

`vexy_localizzy.formats` reads and writes TS, PO, XLIFF, Android, i18next, TMX and
canonical JSON. Every adapter keeps the original bytes: an unchanged round trip
through canonical JSON restores the input exactly. Unsupported structural edits
fail before the output is replaced.

## Converting

```sh
localizzy convert input.po json catalog.json
localizzy convert catalog.json po restored.po
```

`conversion.convert()` supports TS, TMX, PO, XLIFF, Android, i18next and
canonical JSON. It prepares and parses the output before replacing the
destination, and reports changed or dropped fields. Lossy conversions require
`allow_loss=True` (CLI `--allow_loss=True`), and changed PO plural rules require
the same acknowledgement. CLDR categories need an explicit `plural_order` when
converting to positional forms. `conversion.convert_catalog()` applies the same
checks to an in-memory catalog.

Complete ICU message strings stay literal when exported to TS, because Qt does
not evaluate ICU syntax. The loss report records the removal of parsed ICU
metadata. The optional [Node structural checker](https://github.com/vexyart/vexy-localizzy/tree/main/icu) and its
Python cache-validation bridge check complete ICU strings, separately from
brace-format checks.

## Qt TS

`formats.ts.load()` keeps the original XML alongside the editable catalog units.
`formats.json_io.dump()` saves versioned, self-contained JSON; an unchanged
TS→JSON→TS round trip restores exact bytes. Translation edits preserve message
IDs, locations, unknown metadata, byte escapes and positional plural or length
variants. Qt's finished state maps to `translated`; both `untranslated` and
`needs_review` are written as unfinished. Keep canonical JSON when you need
richer approval states.

`translate` and `upgrade` write edited TS catalogs through `formats.ts_splice`,
which replaces only the changed `<message>` spans. Every other byte of the
file, including quoting style and self-closing tags, stays as it was.
`formats.qt_numerus` holds Qt's own numerus-form counts, which differ from CLDR
for some languages (French has 2 in Qt, 3 in CLDR).

## gettext PO

`formats.po` preserves gettext context, comments, previous text, flags, obsolete
entries, encoding and positional plurals. An unchanged PO→JSON→PO round trip
restores exact bytes. New plural output requires an explicit `plural_forms`
rule that matches every active entry's indices. Incomplete retained plurals stay
untranslated; unchanged input bytes can still be archived. Source-locale edits
update `X-Source-Language`.

## Plural form counts

Qt numerus forms and gettext `msgstr[n]` are positional and unlabelled; their
count comes from the format's own rule table, which is not CLDR's. A catalog
written with CLDR's count for French or Russian is wrong for both formats:

| Language | Qt numerus | gettext `nplurals` | CLDR cardinal categories |
|---|---|---|---|
| German | 2 | 2 | one, other |
| French | 2 | 2 | one, many, other |
| Russian, Polish | 3 | 3 | one, few, many, other |
| Japanese | 1 | 1 | other |
| Arabic | 6 | 6 | zero, one, two, few, many, other |

French gettext uses `plural=(n > 1)`, so zero takes the singular. CLDR's
`many` for French covers large round numbers in compact notation, and its
`other` for Russian and Polish covers fractions; neither has a slot of its own
in Qt or gettext. Never reorder or drop forms in a round trip. `qa
--plural-forms auto` derives the expected count from these tables, and
`localizzy convert` requires an explicit `--plural_forms` rule for new PO
plural output rather than guessing one.

## XLIFF

`formats.xliff` writes fresh XLIFF 1.2 and preserves existing 1.2, 2.0, 2.1 and
2.2 documents. It keeps every file section, group, segment, inline code,
original code data and extension metadata. Unchanged XLIFF→JSON→XLIFF restores
exact bytes. Inline content is exposed as XML fragments, and translation edits
must keep the code identities. XLIFF 2 ignorable content is read-only.
Unsupported state changes fail explicitly: `vanished` has no retained XLIFF
representation, and XLIFF 2 does not represent the catalog's `needs_review`
state. New XLIFF 1.2 plural groups keep explicit category and index identities;
categories are never assigned a guessed locale order.

## Android string resources

`formats.android` preserves string resources, CLDR plurals, arrays, styling,
placeholder markup and unrelated XML. Unchanged Android→JSON→Android restores
exact bytes, including names shared by different resource types. Translation
edits use Android quoting and whitespace rules; non-translatable resources,
references and placeholder identities stay protected. Resource XML holds one
locale column: loading projects its values as source text (default `en`,
overridable), and writing uses a supplied target or the source. Cross-format
loss reports cover bilingual metadata and required resource-name changes. Keep
locale selection in the calling application and directory layout.

## i18next JSON

`formats.i18next` keeps nested objects, arrays, interpolation and v4 cardinal,
ordinal and context plural suffixes. Canonical keys use typed JSON paths:
`["menu","open"]` is nested, `["menu.open"]` is literal and `["choices",0]`
addresses an array element. A colliding scalar and plural base gets a `plural:`
prefix. Fresh output accepts these paths or a simple literal key. Retained edits
replace only the selected string tokens; all other bytes, including non-string
values, stay unchanged. Locale and runtime separators or plugins stay in the
application configuration; v4 grouping uses the default `_` separator and an
existing `_other` member. Legacy or custom suffixes stay literal keys. Null
values stay in the original document and are not turned into editable units.

Application JSON must be selected explicitly:

```sh
localizzy convert en.json json catalog.json --source_format=i18next
localizzy convert catalog.json i18next restored.json
```

## TMX as a document

`formats.tmx` exposes an editable language-pair projection and keeps every
original TUV, property and provenance node. Source selection must be
unambiguous; several target languages require an explicit choice before
editing:

```sh
localizzy convert memory.tmx json catalog.json --source_lang=en --target_lang=fr
localizzy convert catalog.json tmx restored.tmx
```

Unchanged round trips restore exact bytes. Existing and newly filled targets
keep inline codes. Edits to exact-origin corpus exports require a separate
revision and are refused here. This adapter loads the whole file; use `Corpus`
and `memory.tmx_read.read_tmx` to stream large memories.

Fresh TMX carries `x-localizzy-projection-v1` in the header (a JSON source and
target pair) and `x-localizzy-catalog-v1` per TU (`version: 1`, plus
`projections` indexed by JSON-encoded language pairs). Each projection stores
the catalog unit fields except `source`, `source_hash` and `record_id`. Native
segments stay authoritative and must agree with the stored target. Plurals and
length variants keep all values in this property; the native target uses
`other`, the first positional form or the first length variant. Other TMX tools
can ignore these properties and see only that representative value. Canonical
JSON remains the portable full catalog.

## Writing new TMX records

For newly extracted literal text, `memory.tmx_write.write_records()` streams
`TMXRecord` objects into an atomic TMX output. It keeps ordered, repeated
properties and every supplied language variant; callers supply provenance and
selection rules. A failed extraction or an invalid XML value leaves the existing
output intact. Use the document adapter above for retained inline XML and
catalog metadata.

## Legacy TMX file names

With the `sources` extra, `memory.names.plan_folder()` applies the legacy file
name policy: lowercase tags, explicit Chinese scripts and population-based
territory shortening. It only proposes names and reports collisions; it never
renames files. `localizzy tm norm DIR` applies the plan. Territory shortening is
a file-naming convention, not a claim that regional translations are
interchangeable. Historical territory aliases are supplied by the caller.

## English source corrections

`localizzy source-fix` uses Qt Linguist as an English copy editor. It supports
C++ source and headers (`.cpp`, `.cc`, `.cxx`, `.h`, `.hpp`, `.hxx`, `.mm`, `.c`)
and Qt Designer `.ui` files. Other source formats produce a conflict before
writing. It updates active messages by context, exact source, disambiguation,
message ID and plural status, rather than replacing words globally.

```sh
localizzy source-fix prepare i18n/app_en.ts i18n/app_en_tofix.ts --root .
# Open app_en_tofix.ts in Linguist. Edit translation fields, then mark them finished.
localizzy source-fix apply i18n/app_en_tofix.ts i18n/app_en.ts --root . --dry-run
localizzy source-fix apply i18n/app_en_tofix.ts i18n/app_en.ts --root .
```

Preparation refuses to overwrite an existing catalog or its `.ts.json`
snapshot. Both catalogs must share a directory so their relative source paths
keep the same meaning. Ordinary translations start identical to their English
sources and unfinished. Empty, identical and unfinished edits are ignored.
Keep the snapshot beside the editing catalog; it records the English catalog
hash and source file hashes. Source and context fields must remain unchanged.

Apply requires Qt `lupdate` on PATH, or `--lupdate /path/to/lupdate`. Current
extraction verifies message identities and refreshes the source locations used
for matching, since checked-in TS line numbers may already be stale.
C++ parsing handles escapes, raw strings and concatenation; comments and spacing
between concatenated literals remain. XML edits preserve surrounding markup.

The English catalog and every matching active message in sibling `.ts` catalogs
receive the new source and an `oldsource`. Foreign translation text is retained,
marked unfinished for review. The English runtime translation is cleared so it
cannot override the corrected source. Applied mirror translations reset to the
new source and unfinished; unapplied drafts remain. Other prepared mirrors are
excluded because they have independent snapshots. Before any writes, native Qt extraction rebuilds every runtime catalog against
a temporary source overlay. The mirror is then rebuilt from the fresh English
catalog, retaining other drafts, and the snapshot is refreshed. A rebuild can
normalize catalog formatting and update locations throughout the files. It uses
all available source files referenced by the English catalog, including external
libraries as read-only inputs. Entries that cannot be re-extracted remain active
with their existing translations; copy editing never authorizes their removal.
It does not discover newly added files with no
previous catalog references; run the project extractor to add those first. No
`.qm` compilation is performed by this command.

Plural entries retain their existing English forms during preparation. Changed
plural forms are rejected: changing an English plural source and its runtime
forms requires a separate manual review. Length variants are also unsupported.
Placeholder changes, key collisions, shared literals with inconsistent edits,
missing or ambiguous occurrences, and sources outside the supplied root block
the complete batch. Preparation still includes messages referring to missing or
external files and reports their file counts; they cannot be applied here.

If the English catalog or a source file being corrected has changed since
preparation, keep the edited mirror and create a new mirror under a different
name from freshly extracted catalogs, then transfer the intended edits in
Linguist. Do not remove the snapshot to bypass a conflict. Unrelated changes to
foreign translations are read at apply time and preserved.

All outputs, including the rebuilt catalogs, are validated and staged before
replacements begin. File modes are
preserved, intervening edits are detected, and handled write failures roll back
already replaced files. Each individual rename is atomic; the multi-file batch
is not atomic across a process crash or power loss. Run in a Git working tree
and inspect the preview and resulting diff. Repeat application without new edits
writes nothing. Native Qt extraction tests verify resulting text and line
references; rollback and no-write conflict cases have regression tests.

The metadata and relative location handling follow the
[Qt TS format](https://doc.qt.io/qt-6/linguist-ts-file-format.html), and extraction
uses the documented [lupdate interface](https://doc.qt.io/qt-6/linguist-lupdate.html).

Source correction commands print their intent and progress to stderr, including
the current catalog and elapsed time. Slow stages emit a heartbeat every five
seconds. Preview diffs remain on stdout. Ctrl+C exits with status 130 and reports
whether original files were untouched, restored, or already written.
