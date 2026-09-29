---
this_file: src_docs/md/4-terminology/402-terminology-work.md
---

# 402. Terminology work: concepts, terms, definitions and why one meaning gets one word

Terminology work starts before anyone translates a word and continues after the last string ships. Its object is not the word. Esselink (2000) puts it in the vocabulary of classical terminology: terminology management defines concepts in a source language and finds their equivalents in the target language, and "a concept is a unit of thought or knowledge made up of a unique set of characteristics". A term is the name given to that unit. A definition says which characteristics make it that unit and not its neighbour.

The distinction sounds academic until you watch a catalog go wrong. This chapter shows how to find the concepts in a product, why each concept gets exactly one translation, why one English word may need several, and how to set the terms early enough that the rest of the translation can rely on them.

## Concepts first, words second

A software interface is written by developers who reuse short English words for different things. The translator sees the word; the user sees the thing. When the two diverge, the translation fails in a way that reads well and behaves badly.

FontLab's word *width* is the standard example. The same five letters name four concepts, and German has a different professional term for each:

| Concept | Where it appears | German |
|---|---|---|
| The advance width of a glyph, the space it occupies in a line | Metrics panel, Font Info | *Dickte* |
| The geometric width of a box or selection | Transform dialogs | *Breite* |
| The width axis of a variable font | Axes, instances | *Weite* |
| Tracking, uniform spacing of a text | Preview, text tools | *Laufweite* |

A translator who renders *width* as *Breite* everywhere writes fluent German that confuses a type designer in three places out of four. The fix is not a better dictionary. It is a concept list that says which *width* each string means, so that the translator translates the concept.

The same holds in the other direction: several English words may name one concept. FontLab's *references* and *element references* are the same objects, elements linked between glyphs or masters like hard links in a file system. They are never glyphs, although a German draft rendered *Also references* as *Auch referenzierende Glyphen*, "also referencing glyphs". The founder's correction in issue 133 fixed the word and the concept at once: *Auch Referenzen*. A concept list that recorded "reference: an element, not a glyph" would have prevented the draft.

## Why one meaning gets one word

Once a concept is identified, it gets one translation in every string, every help page and every manual. The reason is not tidiness. A user who reads *Metrikausschluss* in one dialog and *ohne Metrikeinfluss* in another has every reason to believe these are two different settings. The German FontLab catalog had exactly that: *nonspacing* rendered two ways. Issue 133 picked the shorter and more elegant form, *Metrikausschluss*, with the adjective *metrikausgeschlossen* where the grammar needs one, and required it everywhere. *Fractional coordinates* had the same problem, *nicht ganzzahlige Koordinaten* and *Koordinaten mit Nachkommastellen*, and became *Dezimalkoordinaten* throughout.

The rule that came out of those corrections is in the FontLab localization principles: when one concept has two renderings, keep the shorter and more elegant one everywhere, and search the whole catalog for the concept, not for the string. A second rendering usually hides in a preference description or an undo history entry, where nobody reads it until a user does.

Roturier (2015) describes the cost of not doing this as three kinds of failure:

- **Inconsistent** translations: one term, several renderings, typically when several translators work without coordinating.
- **Inaccurate** translations: a rendering that is wrong for the concept, often because the translator lacked context, or a name that should have stayed in the source language.
- **Inappropriate** translations: a rendering that is correct but not what the audience expects, such as a native coinage where users say the English loan.

Roturier also notes one situation where inconsistency helps: a user searching help text with their own word may find a page only because the page used that word once. That argument applies to searchable prose. It does not apply to labels, which a user matches against other labels on screen.

## One word, several concepts: the collision

Some English nouns name different concepts in different products of the same company. FontLab and its sister applications from Vexy share ten nouns that collide: layers, masks, groups, fills, brush, knife, transform, pencil, eraser and scissors. A FontLab mask is a glyph layer that holds a reference drawing and conceals nothing; a Vexy Lines mask is a stencil that decides where a layer's fills can draw. The glossary records both meanings and tells the writer to name the application whenever a reader could take one for the other ([chapter 403](403-a-glossary-schema.md) shows the field).

For a translator, a collision is a warning that the same English word may need different target words depending on the product. It is also a reason to translate what the English says and no more. The FontLab principles insist that *mask* is translated as *mask* even though a FontLab mask is technically a layer: *Wenn Maske aktiv*, not *Wenn die Maskenebene aktiv ist*. The concept list tells the translator what a mask is. It does not license writing the definition into the label ([chapter 503](../5-interface/503-no-added-detail.md) develops this).

## Where the terms come from

Esselink (2000) lists the practical sources for an initial term list, and they have not changed much:

- the glossary in the product's own help or manual, which comes with definitions;
- the help index and the tables of contents, which show what the writers considered a topic;
- the technical writers' internal term list, if one exists;
- a term extraction run over the documentation;
- product names, manual titles and the names of features;
- the user interface itself: menu items and dialog options.

Esselink warns that an index or a help glossary will not contain every term a translator needs. Roturier (2015) adds a warning about automatic extraction. A statistical extractor proposes frequent word sequences, including noise such as *Before*, and it cannot tell whether *Application Platform* inside *Enterprise Application Platform* is a term of its own. Roturier's advice is to keep the longer candidate when in doubt, because the translations of term A and term B cannot always be glued together to produce the translation of term AB. The FontLab memory guidance says the same thing for a translator: record a multiword term as its own entry, because the translations of *kerning* and *class* do not compose into the translation of *kerning class* (Polish *klasa kernowa*, German *Kerning-Klasse*).

Jiménez-Crespo (2024) stresses the source that makes software terminology hard: neologisms. Products invent concepts faster than dictionaries record them: *double tap*, *unfollow*, *swipe left*. A font editor invents its own: Power Nudge, Smart Corner, True Fill, Cousins. For those, there is no equivalent to look up. The translator has to coin one, and the glossary has to record the coinage before variants spread. [Chapter 407](407-house-voice-across-languages.md) shows how.

## Setting terms early

The single most useful piece of advice in all three books is about timing. Esselink (2000) wants the proposed equivalents validated by the publisher before the translation cycle begins. Roturier (2015) says that defining the translation of a new, frequent term early is often the only way to avoid resolving inconsistencies later. The FontLab guidance puts a number on the cost: fixing a term after its variants have spread costs a second review.

Early does not mean final. A term can be proposed, used and then changed by a later decision; several Polish FontLab terms changed twice in 2026, once after an evidence review and once by the founder's decision. What early means is that there is always exactly one current answer, recorded in one place, and that the change from one answer to the next is itself recorded ([chapter 410](410-ledgers-and-decisions.md)).

## A worked example: resolving a split term

Suppose a reviewer notices that the German catalog renders *nonspacing* two ways. The procedure that FontLab followed generalizes to any split term.

1. **Identify the concept.** A nonspacing component or mark takes no space of its own: it does not change the advance width of the glyph it sits on. Check that every candidate string really means that. A Unicode category name that contains *nonspacing* may refer to a different classification and needs its own decision.
2. **Collect the renderings.** Search the catalog, the help and the manual for every rendering of the concept, including inflected forms and compounds: *Metrikausschluss*, *ohne Metrikeinfluss*, *Komponenten ohne Metrikeinfluss*.
3. **Choose one.** Prefer the shorter, more elegant form that a professional would recognize. Decide the related forms at the same time: the adjective *metrikausgeschlossen*, the phrase *Metrikausgeschlossene Komponenten*.
4. **Record the decision.** Put the term into the core memory with a note that names the rejected form, so the next translator and the next engine do not bring it back.
5. **Apply and log.** Change every string, and write each change into the review ledger with the text before and after.

The procedure is deliberately boring. The judgment happens in step 3; the rest exists so that step 3 happens once.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 12: introduction, terminology setup, reference materials)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (sections 5.4.1 to 5.4.3)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 3: terminology and localization)
- `issues/133.md` in the fl10n repository
- [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/), [localization/memories](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/memories/), `glossary/terms/layers.yaml` and `glossary/terms/masks.yaml` in the vexy-fontlab-writing-styleguide repository
