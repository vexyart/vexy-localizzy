---
this_file: src_docs/md/3-formats/304-xliff.md
---

# 304. XLIFF 1.2 and 2.1: the interchange format and its two dialects

XLIFF, the XML Localization Interchange File Format, was designed for a problem that Roturier (2015) states plainly: a publisher or a language service provider extracts translatable content from code and documentation, a translator somewhere else does the work, and the content has to flow between their systems without losing information. XLIFF is the container for that flow. Jiménez-Crespo (2024) dates its standardization by OASIS to 2002. Unlike TS, PO or Android XML, it belongs to no runtime. No application loads an XLIFF file to display a menu; tools exchange it.

That role explains both its strength and the confusion around it. XLIFF can carry source, target, notes, review state, inline code and tool-specific metadata, so it can represent almost any other format. But "XLIFF" names two formats. Version 1.2 and version 2.0, with its successors 2.1 and 2.2, use different namespaces and different element vocabularies. The research synthesis states it without qualification: XLIFF 1.2 and 2.0 are mutually incompatible. A tool that says it supports XLIFF supports one of them, sometimes both, and the first question in any exchange is which.

## XLIFF 1.2: trans-units in a body

A 1.2 document wraps each source file in a `<file>` element with `source-language`, `target-language`, `original` and `datatype` attributes. Inside it, a `<body>` holds `<trans-unit>` elements, optionally nested in `<group>` elements. This unit comes from the vexy-localizzy test suite:

```xml
<trans-unit id="a" approved="yes">
  <source>Open <g id="b">bold &amp; bright</g> <x id="p"/></source>
  <target state="final">Öffne <g id="b">fett &amp; hell</g> <x id="p"/></target>
  <note>Note</note>
  <alt-trans><source>Alternative</source><target>Earlier</target></alt-trans>
</trans-unit>
```

The pieces map onto familiar ideas. `id` is the unit's identity within the file. `<note>` carries context for the translator; Jiménez-Crespo shows the Firefox for iOS catalogs using notes to say whether a string is something the user taps or swipes, and to separate *Close* the verb from *close* the adjective. `state` on the target and `approved` on the unit record the review state. `<alt-trans>` holds alternative translations, such as an earlier version or a memory match.

Inline codes are the part that matters most for safety. `<g>` wraps a span of formatted text, and `<x/>` stands for a standalone code such as a placeholder or a line break. The translator moves them but must not change their `id` values, because the tool that merges the translation back uses the ids to restore the original markup. Angular's extractor, as Baldurs (2025) shows, writes an interpolation as `<x id="INTERPOLATION" equiv-text="{{username}}"/>`, so the translator sees a readable hint while the tool keeps control of the real code.

Version 1.2 has no plural element. Tools represent plurals by convention, and the conventions differ. `lconvert` and the Translate Toolkit use a `<group restype="x-gettext-plurals">` with one `<trans-unit>` per form, following the XLIFF representation guide for gettext PO. Apple's 1.2 exports encode the plural structure of `.stringsdict` in the unit ids, with a `key:variable:dict` naming scheme, according to one of the research reports. A tool that knows neither convention shows the plural forms as unrelated strings, and the FontLab project's notes advise briefing translators on plural groups for that reason. Context for gettext entries travels in `<context-group>`, which the vexy fixture uses for the Qt context:

```xml
<group restype="x-gettext-plurals" id="n">
  <context-group><context context-type="x-localizzy-context">Count</context></context-group>
  <trans-unit id="n[one]"><source>One item</source><target state="translated">Ein</target></trans-unit>
  <trans-unit id="n[other]"><source>One item</source><target state="translated">Viele</target></trans-unit>
</group>
```

## XLIFF 2.x: units, segments and modules

Version 2.0 reorganized the document. The root carries `srcLang` and `trgLang`. A `<file>` holds `<unit>` elements, and each unit holds one or more `<segment>` elements, each with its own `<source>`, `<target>` and `state`. Notes live in a `<notes>` block on the unit. Inline codes become `<ph>` for a placeholder and `<pc>` for a paired code, and the original native code they stand for is kept separately in `<originalData>`, referenced by `dataRef`. Whitespace or text between segments that must not be translated goes in `<ignorable>`. This test fixture shows most of it:

```xml
<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" version="2.0" srcLang="en" trgLang="de">
 <file id="one">
  <unit id="u" name="Title">
   <notes><note>Keep note</note></notes>
   <originalData><data id="d">native</data></originalData>
   <segment id="first" state="final">
    <source>Open <ph id="1" dataRef="d"/></source>
    <target>Öffne <ph id="1" dataRef="d"/></target>
   </segment>
   <ignorable><source> </source><target> </target></ignorable>
   <segment id="second"><source>Again</source></segment>
  </unit>
 </file>
</xliff>
```

Segments carry one of four states, `initial`, `translated`, `reviewed` and `final`, which are the values the vexy-localizzy adapter reads and writes. Metadata from other vocabularies sits in extension elements under their own namespaces; the toolkit's tests keep a `<m:metadata>` element and a `<skeleton>` reference intact through a round trip. The research synthesis lists the features that make 2.1 attractive as an interchange format: first-class notes, protected inline codes, validation rules and size restrictions. Jiménez-Crespo adds a glossary module that is interoperable with TBX ([chapter 306](306-tmx-and-tbx.md)).

## Which XLIFF, and for what

The sources give XLIFF three different jobs, and the difference is a real disagreement:

| Source | Position |
|---|---|
| Research corpus, chapter 5 | XLIFF 2.1 is the best interchange hub; keep a 1.2 path when Qt is involved |
| Research corpus, chapter 3 | XLIFF is transport to a TMS, never a runtime artifact |
| FontLab project format notes | The `.ts` file is authoritative; XLIFF is for exchange only |
| vexy-localizzy | Writes fresh documents as 1.2; preserves and edits existing 1.2, 2.0, 2.1 and 2.2 |

The positions agree more than they seem to. All four treat XLIFF as something that crosses a boundary, not as the store of record. They differ on which version to emit, and the deciding factor is the tool on the other side. Qt's own converter is the clearest constraint. The FontLab project's notes and the research both say that `lconvert` writes XLIFF 1.1, and the research adds that Qt Linguist supports only 1.1 and 1.2. A test for this chapter disagrees on the first point: `lconvert` from Qt 5.15.19 and from Qt tools 6.11 both wrote documents declaring `version="1.2"` in the 1.2 namespace. The sources and the test agree on what matters: Qt's tools write no 2.x. The FontLab catalogs therefore reach a CAT tool through the older dialect. A team whose vendor accepts 2.x and whose own tools read it gains the richer model; a team with a Qt tool anywhere in the loop keeps a 1.2 path.

## State mapping is where round trips break

Each XLIFF version has its own state vocabulary, and neither matches Qt's or gettext's exactly. vexy-localizzy maps the 2.x states onto its catalog states like this:

| XLIFF 2.x | Catalog state | Written back as |
|---|---|---|
| `initial` | untranslated | `initial` |
| `translated` | translated | `translated` |
| `reviewed` | approved | `final` |
| `final` | approved | `final` |

Two catalog states have no XLIFF 2 counterpart: `needs_review` and `vanished`. The toolkit refuses to write them rather than quietly downgrading them, and it refuses to remove a target without also resetting its approval state. That strictness is deliberate. A round trip that turns "needs review" into "translated" has approved a string that nobody approved.

## Worked example: a Qt catalog through a CAT tool

A common route for a Qt project is `.ts` to XLIFF, into a CAT tool, and back:

```sh
lconvert -if ts -of xlf app_de.ts -o app_de.xlf
# translate app_de.xlf in the CAT tool
lconvert -if xlf -of ts app_de.xlf -o app_de.back.ts
```

Running exactly this on the small German fixture from [chapter 302](302-qt-ts.md), with no CAT tool in between, shows what the trip costs before any translator touches the file. `lconvert` wrapped each Qt context in a `<group restype="x-trolltech-linguist-context">`, turned the unfinished message into a target with `state="needs-review-translation"`, and put plural forms in an `x-gettext-plurals` group. On the way back, the `sourcelanguage` attribute was gone, a duplicate message was dropped with a warning, an obsolete message moved to another position, and a plural message that had one form gained a second, empty one. None of this is wrong by Qt's rules, and all of it shows up in a diff.

Before you trust a file returned from a CAT tool, also check what XLIFF 1.1 and 1.2 could not carry. The FontLab project's notes list three fields that do not survive: the internal source hash, the full state value, which comes back with reduced resolution, and the length budget, which travels as a custom attribute that CAT tools may strip. They add a fourth hazard: unit ids built from context and source text can grow long, and some CAT tools truncate ids at 256 characters, which breaks the merge. Placeholders are a fifth: the research records an open issue in one Node XLIFF converter where `{{name}}` does not survive the round trip as an inline code.

The check after import is therefore concrete:

1. The number of messages, contexts and plural forms matches the file you sent.
2. Every inline code id in each target matches its source.
3. No state is higher than the state the CAT tool actually assigned.
4. Length limits and comments are restored from your own copy, not from the returned XLIFF.

vexy-localizzy's XLIFF adapter was checked against the two XLIFF catalogs the FontLab localization project consumes, 981 messages in 92 file sections: both round-trip byte for byte through canonical JSON, and fresh and edited output validates against the official OASIS 1.2, 2.0 and 2.2 core schemas. Validation against the schema is cheap and catches the structural half of these failures. The semantic half, a state that claims more review than happened, needs the explicit refusals described above.

## Sources

- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 2.5.2)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapters 3 and 6)
- Baldurs L., *TypeScript Internationalization (i18n) and Localization (l10n)*, 2025 (extracting and managing translation files)
- A local test of `lconvert` (Qt 5.15.19 and Qt tools 6.11.2) on `tests/fixtures/legacy_golden/inputs/ts/app_de.ts` from the vexy-localizzy repository
- [docs/formats.md](../8-toolkit/formats.md), `WORK.md`, `src/vexy_localizzy/formats/xliff2.py`, `tests/test_xliff2.py` and `tests/test_xliff_formats.py` in the vexy-localizzy repository
