---
this_file: src_docs/md/3-formats/306-tmx-and-tbx.md
---

# 306. TMX and TBX: exchanging memories and terminology

A translation memory stores pairs of source and target segments so that a translation made once can be reused. A termbase stores concepts and the terms that name them. Both are databases, and every tool that keeps them has its own storage. TMX and TBX exist so that the contents can leave one tool and enter another. Esselink (2000) records the origin: a special interest group called OSCAR, formed in 1997 by the Localisation Industry Standards Association (LISA), developed TMX to let tools and vendors exchange memory data. TBX, the TermBase eXchange format, was a later OSCAR project; Esselink describes it in the future tense, as a standard exchange format for terminology still being prepared.

Both outlived their sponsor. Roturier (2015) notes that LISA stopped its activity while the TBX specifications stayed available and supported, and Jiménez-Crespo (2024) says that both standards are now maintained by different organizations. TMX in particular became more than an exchange format between CAT tools: Jiménez-Crespo points out that it is the usual container for the bilingual parallel corpora used to train machine translation, such as the OPUS collection.

This chapter describes the files. How a team organizes its memories and glossaries, what goes into a core memory and what into a project memory, is the subject of [chapter 405](../4-terminology/405-core-and-project-memories.md).

## The shape of a TMX file

A TMX document has a `<header>` and a `<body>`. The header describes the whole file: the tool that wrote it, the segmentation level, the administrative and source languages, the data type and the original memory format. The body holds translation units, `<tu>`, and each unit holds one translation unit variant, `<tuv>`, per language, identified by `xml:lang`, with the text in `<seg>`. Units and variants can carry `<prop>` elements with a `type` attribute and `<note>` elements. This one-unit memory is a test fixture in the vexy-localizzy repository:

```xml
<tmx version="1.4">
 <header creationtool="po2tmx" creationtoolversion="1.0" segtype="block"
         adminlang="en" srclang="en" datatype="plaintext" o-tmf="gettext"/>
 <body>
  <tu tuid="1">
   <prop type="x-origin">translations/app_de.ts</prop>
   <prop type="x-context">Main</prop>
   <tuv xml:lang="en"><seg>Open</seg></tuv>
   <tuv xml:lang="de"><seg>Öffnen</seg></tuv>
  </tu>
 </body>
</tmx>
```

Roturier walks through a unit of the same shape: `tuid` identifies it, the variants differ by language, and properties such as the name of the source file are metadata. The header's `segtype` matters for software. Esselink describes memory tools that segment documentation at sentence ends, paragraph marks and table cells; a software string is usually one unit whatever its length, and `segtype="block"` says so.

A unit is multilingual by design. One `<tu>` may hold English, German and French variants at once, which makes a TMX file a good archive and an awkward editing surface: a tool that edits one language pair must choose which variants it is looking at and leave the others alone.

## What properties carry, and what other tools see

TMX fixes very little metadata. Anything beyond the text goes into properties, and properties whose type starts with `x-` are private conventions. That is both the format's flexibility and its main interoperability risk: a tool that does not know a convention keeps the text and ignores the meaning.

The FontLab memories show how much meaning a project can put into properties. Its project memory, built by vexy-localizzy from reviewed Qt catalogs, uses the tuid `Context|Source[:form]` and the properties `x-context`, `x-comment`, `x-numerus-form` and, when a message has one, `x-message-id`. Every plural form gets its own unit, even in a one-form language. With those properties, a lookup can tell a match in the same Qt context from a match elsewhere, and it can refuse a plural whose forms do not cover the target language:

| Match class | Condition | Written as |
|---|---|---|
| `id` | `x-message-id` equals the message id | finished |
| `context` | same context and comment | finished |
| `source` | every context gives the same target | unfinished |

A memory tool that ignores the properties sees only English and German text, and it cannot draw any of these distinctions. The same limit applies in the other direction. When vexy-localizzy writes a whole catalog into TMX, it stores the catalog fields in a documented property, `x-localizzy-catalog-v1`, and puts one representative value in the native segment: the `other` plural form or the first positional form. Its documentation says plainly that other TMX tools can ignore the property and will see only that representative value. Canonical JSON remains its portable full catalog.

A memory also ages. Esselink lists the disadvantages of translation memory alongside its benefits, and one of them still describes the most common failure: last-minute language changes are often made in the final translated files after conversion, not in the memory, so the memory falls behind the product. The FontLab guide turns the observation into a procedure. Feed late fixes into the reviewed catalog, then regenerate the project memory from it; a correction made only in an exported file disappears at the next regeneration. For older translations that were never stored in a memory, Esselink describes alignment, matching source and target documents to build one after the fact, which is fast when the translation was segment by segment and slow when a translator moved sentences around.

Two practical rules follow. Keep the metadata when you export a memory: the FontLab guide lists creation date, translator, reviewer and use count as the fields that let someone prune a memory later without rereading it. And write down every `x-` property your project relies on, because the file itself will not explain them to the next tool.

## Language tags inside memories

Memories outlive catalogs, and their language tags rarely match. A FontLab catalog is tagged `de_DE` or `es_MX`; the memories are tagged `de` and `es-419`. vexy-localizzy resolves the difference with a closest-variant rule and refuses the matches that would be wrong: `zh-Hans` never answers `zh_TW`, `pt-BR` never answers `pt_PT`, and `en` does not answer `en_GB` without an explicit choice. The legacy file-naming policy that shortens `de-DE.tmx` to `de.tmx` is documented as a naming convention only, "not a claim that regional translations are interchangeable". A memory's tag is data about whose language it is; treat a mismatch as a question, not as a formatting nuisance.

## TBX: concepts rather than segments

TBX is organized around concepts, not strings. Esselink describes it as an XML format built on a LISA subset of ISO 12620, a list of terminological data categories, with a declared structure meant for "blind" interchange, in which the receiving tool needs no side agreement to understand the file. Roturier and Jiménez-Crespo both use the Microsoft terminology exports as the example of TBX in practice. Each entry carries six fields:

1. a concept identifier;
2. a definition;
3. the source term;
4. the source language identifier;
5. the target term;
6. the target language identifier.

Jiménez-Crespo adds that XLIFF includes a glossary module interoperable with TBX, so a termbase can travel with the strings it governs.

The sources used for this book do not include the TBX specification or a TBX file, so this chapter shows no TBX markup. The field list above is what the books document. A team that must exchange terminology with a vendor's termbase should validate its export against the current specification and against the importing tool, not against an example from memory.

## Worked example: a glossary carried as TMX

The FontLab project does not use TBX. It keeps its terminology in TMX files, one core memory per language, and the design shows what a concept-oriented glossary needs from any format. One unit per glossary term, with the term's stable id in the tuid:

```xml
<tu tuid="term:kerning-class">
 <prop type="x-term-id">kerning-class</prop>
 <prop type="x-category">font-engineering</prop>
 <prop type="x-translatable">yes</prop>
 <prop type="x-status">approved</prop>
 <note>A kerning class groups glyphs that share the same kerning behavior…</note>
 <tuv xml:lang="en"><seg>kerning class</seg></tuv>
 <tuv xml:lang="de">
  <note>Loanword compound, so hyphenated. Plural Kerning-Klassen.</note>
  <seg>Kerning-Klasse</seg>
 </tuv>
</tu>
```

Set this against the Microsoft field list. The concept identifier is `x-term-id`, and the English definition is the unit note. Source and target terms and their languages are the two variants. FontLab adds what the six fields lack: a status (`approved`, `proposed` or `do-not-translate`), a category, a translatability flag and a translator note on the target side. The schema requires a `do-not-translate` unit to repeat the English term in the target segment, so that a vendor sees what to ship rather than an empty field.

The choice has a cost and a benefit. The benefit is one file format for both memories, which the toolkit already reads, writes and checks; the translation engine receives the core memory as a glossary and the project memory as a cache of whole strings. The cost is that the concept structure lives in private properties, so a CAT tool that imports the core memory would see a small memory of short segments, not a termbase. In the FontLab practice that cost has not been paid yet: the terms reach translators through generated term tables and through the engine prompt, and no CAT tool's term recognition sits in the loop. A project whose vendors work in a CAT tool would need a TBX export, and the mapping above is where it would start.

The numbers from the first real load of these memories give a sense of scale:

| Measurement | Value |
|---|---|
| German and Spanish UI memory units loaded | 10,373 of 10,373 each |
| Context hits for the German catalog | 10,309 of 10,587 messages |
| Glossary terms used | 206: 147 approved, 59 do-not-translate |
| Proposed terms left out by default | 2 |

The 278 misses were mostly core terms, which by design live only in the glossary, plus eight messages whose leading or trailing spaces the memory builder had trimmed away. Verbatim lookup is strict on purpose, and a miss of that kind is the lookup working.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapters 11 and 12)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 2.5.2 and the terminology section of chapter 5)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 3)
- [docs/formats.md](../8-toolkit/formats.md), [docs/memories.md](../8-toolkit/memories.md), `WORK.md` and `tests/fixtures/legacy_golden/oss2tmx/synth-ts/de.tmx` in the vexy-localizzy repository
- [glossary/schema.md](https://github.com/Fontlab/vexy-fontlab-writing-styleguide/blob/main/glossary/schema.md), [localization/memories](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/memories/), [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/) and `localization/tm/de-core.tmx` in the vexy-fontlab-writing-styleguide repository
