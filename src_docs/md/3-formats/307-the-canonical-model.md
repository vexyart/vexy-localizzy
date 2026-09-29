---
this_file: src_docs/md/3-formats/307-the-canonical-model.md
---

# 307. The canonical model: one typed representation and the loss every conversion accepts

Chapters 302 to 306 described six formats that answer the same questions differently. A team that uses more than one of them faces a choice. It can convert each pair of formats directly, which means writing and testing a converter for every pair and discovering each pair's losses separately. Or it can define one representation in the middle, read every format into it and write every format out of it. The research synthesis recommends the second design, and the fl10n specification adopts it: preserve the source format's meaning as long as possible, normalize into one typed bilingual model with explicit fields, and apply the target runtime's conventions only at the boundary, accepting and testing the loss that the boundary causes.

The phrase "accepting the loss" is the important part. A canonical model does not make conversion lossless. It makes the loss visible, because every field the target cannot hold is a named field that the converter can compare before and after. This chapter describes what such a model must contain, the decisions that shaped the one in vexy-localizzy, and how loss is reported.

## The fields a message needs

The fl10n specification defines the model as immutable Pydantic records. vexy-localizzy kept the design and extended it. Its message record, abridged:

```python
class Unit(Record):
    key: str
    context: str
    source: str
    source_plural: str | None = None
    target: str | None = None
    disambiguation: str | None = None
    notes: list[str] = []
    plural: PluralForms | None = None
    placeholders: list[Placeholder] = []
    max_length: int | None = None
    locations: list[str] = []
    state: UnitState = "untranslated"
    source_hash: str = ""
    record_id: str | None = None
    variants: list[str] | None = None
```

Each field exists because at least one format carries it and at least one other format drops it:

| Field | Carried by | Lost in |
|---|---|---|
| `context` | TS context, PO `msgctxt`, TMX property | flat JSON keyed by source |
| `disambiguation` | TS `<comment>` | most formats, unless folded into context |
| `notes` | TS extra comment, PO `#.`, XLIFF `<note>` | JSON, Android |
| `plural` | TS numerus, PO `msgstr[n]`, Android and i18next categories | any format that holds one string per key |
| `placeholders` | inline codes in XLIFF, `<xliff:g>` in Android | plain text formats, where only syntax marks them |
| `max_length` | XLIFF, as a custom attribute that CAT tools may strip | PO, i18next JSON |
| `state` | TS type, PO fuzzy, XLIFF state | Android, JSON |
| `variants` | TS `<lengthvariant>` | PO, which keeps only the first |

Placeholders deserve their own field even though every format stores them inside the text. The specification's reason is practical: when the placeholder inventory is parsed once, on the way in, the placeholder protocol for machine translation and the quality checks can compare inventories instead of running a regular expression over strings every time they need to know what `%1` is. The model records each placeholder's token, its syntax and its kind. The syntax values are `qt`, `printf`, `python_brace`, `icu`, `i18next` and `html`, and the kinds are argument, tag, accelerator and numerus. A Qt `&` accelerator is a placeholder of kind accelerator, so a check can treat a lost mnemonic the way it treats a lost `%1`. [Chapter 606](../6-machine-translation/606-the-placeholder-protocol.md) shows the inventory at work.

The record's configuration forbids unknown fields. A serialized catalog with a field the model does not know fails to load instead of dropping the field quietly. That rule is small and it matters: a model that ignores what it does not understand becomes one more lossy format.

## Four design decisions

### Decision one: how to store plurals

The specification and the toolkit disagree about plurals, and the disagreement is the center of this chapter.

The fl10n specification canonicalizes plurals to ICU with CLDR categories. Qt's positional numerus forms and PO's indexed forms are parsed into named categories on the way in and re-emitted in the target convention on the way out. The goal is sound: a model that stores `one`, `few` and `many` explicitly cannot silently collapse a six-form Arabic message.

vexy-localizzy stores positions as positions. Its `PluralForms` record has an `indexing` field: `cldr` for formats that name categories, such as Android and i18next, and `index` for Qt and gettext, whose forms are keyed `"0"`, `"1"`, `"2"`. The record's documentation states the rule: positions "are never inferred to be CLDR categories". Converting from named categories to positions requires the caller to supply `plural_order`, listing every source category exactly once.

ICU messages add a second case. A string such as `{count, plural, one {# item} other {# items}}` holds its own plural logic, and the model can parse it into forms. Qt does not evaluate ICU syntax, so when such a message is written to TS, vexy-localizzy keeps the complete ICU sentence as a literal string and records in the loss report that the parsed metadata was removed. The sentence reaches the translator intact, and the report says what the TS file can no longer express.

The evidence in this part favors the toolkit's caution. Chapter 302 showed that Qt 5.15 gives French two numerus forms where CLDR has three categories, and Polish three where CLDR has four. Chapter 303 showed two fl10n files disagreeing about the French and Russian gettext rules. A converter that maps position 1 to `few` has to know which rule produced the file, and the file does not say. Storing the position and asking for the order moves that knowledge from a hidden assumption into an explicit argument. The specification's aim, never losing a form, is kept; its method, inferring the category, is not.

### Decision two: identity and the source hash

A canonical model needs a key that every format can use. Qt identifies a message by context, source and disambiguation, which is not a clean hierarchical key. The specification derives one deterministically, `context.slug(source)` plus the disambiguation when present, and keeps the Qt tuple as the authority. vexy-localizzy keeps that convention for messages without explicit ids and adds `record_id`, which binds an edited unit to its place in the original document.

The `source_hash` field is a SHA-256 digest of source, context and disambiguation, and of the plural source when there is one. It answers one question cheaply: has the thing being translated changed? The research names the use: store a hash of the source string, with the model and prompt version, and retranslate when any of them changes. [Chapter 310](310-identity-and-upgrade.md) shows the same question asked across whole catalogs.

### Decision three: states that every format can map

The model's states are `untranslated`, `needs_review`, `translated`, `approved` and `vanished`. No single format has all five, so each adapter maps its own vocabulary and refuses the mappings it cannot make honestly:

| Canonical state | Qt TS | Gettext PO | XLIFF 2.x |
|---|---|---|---|
| untranslated | unfinished | empty, or fuzzy when text exists | `initial` |
| needs_review | unfinished | `fuzzy` | refused |
| translated | finished | translated | `translated` |
| approved | finished | translated | `final` |
| vanished | vanished | obsolete `#~` | refused |

The table shows where approval information dies. Qt and PO cannot distinguish translated from approved, so a catalog that needs a second reviewer's approval has to keep it in canonical JSON. XLIFF 2 has no "needs review" and no "vanished"; the adapter refuses to write them rather than choose a nearby state.

### Decision four: keep the original document

The last decision is the least obvious. vexy-localizzy's catalog carries the complete original document alongside the editable units. A TS catalog converted to canonical JSON contains the TS bytes; converted back without edits, it restores them exactly. The same holds for PO, XLIFF, Android, i18next and TMX. The units are the editable view; the document is the authority for everything the units do not model, such as comments outside messages, attribute order, entity style and unknown extension elements.

The retained document also changes what an edit may do. A unit carries a `record_id` that binds it to its place in the document, so an edit to the German text of one message is applied to that message in the original bytes. An edit the adapter cannot apply safely, such as a structural change the format does not allow, fails before any output is written.

The consequence is a different kind of guarantee. A model that rebuilds files from its fields can only promise that the fields survive. A model that keeps the document can promise that nothing outside an edited message changes. [Chapter 309](309-byte-preserving-edits.md) builds on that promise.

## Worked example: an Android plural into PO

Loss reporting is easiest to understand by watching it. This single-column Android resource holds one string and one plural:

```xml
<resources>
<string name="open">Open</string>
<plurals name="files"><item quantity="one">%d file</item><item quantity="other">%d files</item></plurals>
</resources>
```

Converting it to PO with vexy-localizzy takes three attempts, and each refusal names a decision the tool will not make alone:

```sh
localizzy convert strings.xml po out.po
# ValueError: Supply plural_order with every source category exactly once
localizzy convert strings.xml po out.po --plural_order='[one,other]'
# ValueError: A fresh plural PO requires an explicit Plural-Forms header
localizzy convert strings.xml po out.po --plural_order='[one,other]' \
    --plural_forms='nplurals=2; plural=(n != 1);' --allow_loss=True
```

The third run writes the file and reports seven major findings, one per changed field: the original Android document, the key of each message, the empty target of *Open*, and for the plural its key, plural source, plural forms and state. The resulting PO entry shows why the state finding matters:

```po
#, fuzzy
msgid "%d files"
msgid_plural "%d files"
msgstr[0] "%d file"
msgstr[1] "%d files"
```

The Android file held English values in a single column. PO is bilingual, so the English plural forms landed in the translation slots, and the adapter marked the entry fuzzy because it now has target text that nobody approved. The singular source became the `other` form, because Android stores no separate singular source. None of this is a bug in either format. It is what moving between a monolingual resource and a bilingual catalog means, and the report says so line by line. Without `--allow_loss=True` the tool writes nothing, and the destination keeps its previous content.

## Sources

- `research/05-format-conversion-cicd-and-continuous-localization.md` in the fl10n repository
- `spec/03.md` and `docs/formats/json.md` in the fl10n repository
- `docs/formats.md`, `src/vexy_localizzy/catalog.py`, `src/vexy_localizzy/conversion.py`, `src/vexy_localizzy/formats/po.py` and `src/vexy_localizzy/formats/xliff2.py` in the vexy-localizzy repository
- A local run of `localizzy convert` on a two-message Android resource, recorded for this chapter
