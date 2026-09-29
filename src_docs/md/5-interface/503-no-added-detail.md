---
this_file: src_docs/md/5-interface/503-no-added-detail.md
---

# 503. No added detail: pair not kerning pair, mask not mask layer, and the reverse

Translators add detail for good reasons. They know the product, they want the user not to misunderstand, and their language builds compounds as easily as English builds noun phrases. A German translator or reviewer who sees *Remove pair* in the kerning toolbar knows it is a kerning pair and writes *Kerningpaar entfernen*. Nothing in that translation is false. It is still wrong, and this chapter explains why, when the rule bends, and how to find the cases a catalog has already accumulated.

## Where added detail comes from

The pressure toward explicitness is old. Esselink (2000) encourages software translators to avoid literal renderings, to verify the function of each option and to choose a target word that describes that function accurately. That advice is sound, and it is also the route by which detail enters: once a translator has looked up what a control does, the knowledge wants to appear in the label. Dr International (2002) asks writers to use words with "a precise and confined meaning". A translator who takes that as licence to make every label more precise than its source has confused the author's job with the translator's.

Compounding languages make the step effortless. In German, *Paar* becomes *Kerningpaar* by adding one prefix; *Wolke* (cloud) becomes *Ankerwolke* (anchor cloud) or *Vorschauwolke* (preview cloud). Each addition feels like a clarification. In a catalog of ten thousand strings, the additions accumulate into a vocabulary that is longer than the English and more specific in places where the English chose to be general.

The FontLab quality specification classifies this as an accuracy error, under the MQM family of the same name: *invented specificity*, with *anchor cloud* for *cloud* as its example. It sits beside omission, addition and mistranslation because it is a kind of addition. The user reads a meaning the source did not state.

## The rule, in both directions

The founder's instruction in fl10n issue 133 was short: if the context makes clear that a pair is a kerning pair, translate *pair* as *Paar*, not *Kerningpaar*, and do not add specificity where the original had none, especially in compounds. The principles then stated the other half, which is easy to forget: do not drop a distinction the English keeps either.

| English | Added or lost detail | Reviewed rendering |
|---|---|---|
| Remove pair | Kerningpaar entfernen | Paar entfernen |
| Show in cloud | In Ankerwolke anzeigen | In Wolke anzeigen |
| If mask is active | Wenn die Maskenebene aktiv ist | Wenn Maske aktiv |
| Also references | Auch referenzierende Glyphen | Auch Referenzen |
| Rename glyph in kerning pairs and classes | Glyphe in Kerningpaaren und Kerningklassen umbenennen | Glyphe in Kerning-Paaren und Klassen umbenennen |

The first three rows add detail. The last row removes it: the English says *classes*, and the operation renames the glyph in all classes, not only in kerning classes. Repeating *Kerning* before *Klassen* reads naturally in German and narrows the scope of the command. A user who relies on the label would expect the glyph's other class memberships to keep the old name.

The two failures are the same failure seen from opposite sides. In each case the translation states a different scope from the source. Detail added makes a general label specific; detail dropped makes a specific label general. The source's level of generality is part of its meaning.

## When product knowledge tempts you

A FontLab mask is a layer. The translator knows this, and the German *Maskenebene* (mask layer) is technically accurate. The label says *mask* because the context already establishes what a mask is, and because *mask* is the name users see everywhere else. The principles put it directly: if the English says *mask*, write *mask*, even though in FontLab a mask is a layer.

Product knowledge can also produce detail that is not just redundant but wrong. *Also references* was translated as *Auch referenzierende Glyphen*, also referencing glyphs. In FontLab, a reference is an element linked between glyphs or masters, which the founder compared to hard links in a file system. References are elements, not glyphs. The translator filled the English noun with the object they assumed it meant, and the assumption was wrong. The noun in the source was the safer choice all along.

The opposite temptation affects named operations. FontLab's *Oblique* applies a slant with a specific set of optical corrections. Translating it as German *Schrägstellen* (slanting) replaces a named operation with a generic verb, removing the specificity that the name carried. Issue 133 kept *Oblique* in German for this reason. The rule is the same: the translation must say exactly as much as the source. When the source uses a proper name, the name is the detail.

Two situations do justify a longer target, and neither is added detail.

- **The target grammar needs a head noun.** English *narrower* carries its dimension; German *kleiner* does not, so *if new is narrower than current* becomes *wenn neue Dickte kleiner als aktuelle*. The information was in the source; the translation moves it ([502](502-headline-style.md)).
- **The target term is one word longer.** Where the language's established term for a concept is a compound, the compound is the term, not an addition. German *Dickte* is one word for advance width; French *chasse* likewise. What matters is the concept, not the word count.

## Worked example: one noun across a catalog

The founder's remarks on *reference* in issue 133 amount to a small procedure, and it generalizes to any term that a catalog has inflated.

Start from the concept, not the string. Search the catalog for every translation that contains the target words used for references, including the inflated forms (*Elementreferenz*, *referenzierend*), and read each source. Classify each hit by what the English says:

```text
Also references                          -> Auch Referenzen
FontLab will unlink those references.    -> FontLab trennt diese Referenzen.
Element references                       -> Element-Referenzen
```

Where the source says *references*, the target says *Referenzen*. Where the source says *element references*, the target says *Element-Referenzen*, hyphenated because *Element* is used here as a loaned compound part (the hyphenation rule belongs to [509](509-language-portraits.md)). Before the consistency pass, the second line read *FontLab trennt diese Elementreferenzen*: the source said *references*, and the translation promoted it.

The ledgers show where the long forms came from, and it was not the first translator. The original catalog said *Paar entfernen*, *Auch Referenzen* and *FontLab löst diese Referenzen*. The first review pass of September 2026 changed them to *Kerningpaar entfernen*, *Auch referenzierende Glyphen* and *FontLab trennt diese Elementreferenzen*, each time with a plausible reason: the button removes a pair in the kerning area; *Referenzen* alone would leave open which way the reference points. The consistency pass of issue 133 returned the first two to their original wording and kept only the better verb in the third. A reviewer who knows the product is exactly the person most likely to add detail, and only a ledger that follows a string through every change makes the round trip visible.

Then check the other languages. The French catalog reads *Inclure les références* and *FontLab déliera ces références*, the Spanish *También referencias* and *FontLab desvinculará esas referencias*: all three follow the source's level of detail. Record the decision in the core memory so the next catalog cannot reintroduce the long form ([410](../4-terminology/410-ledgers-and-decisions.md)).

A consistency pass rarely reaches every string. A search of the Spanish catalog on 29 September 2026 still found *Mostrar en nube de anclas* (show in anchor cloud) for *Show in cloud* in the Glyph inspector, while the German had become *In Wolke anzeigen*. The rule was stated for all languages; its application was complete in one. Findings like this are why the check below exists.

## Checking for added detail

Added detail is hard for a generic checker to see, because every word of the translation is correct. Three checks catch most of it.

**Bilingual conditional rules.** A rule of the form "target contains *Kerningpaar* but source does not contain *kerning*" flags exactly the inflated renderings. The FontLab quality page recommends such rules for false friends: forbid a target phrase only when the source contains, or lacks, a given word. Write one for each concept the review has settled (*pair*, *cloud*, *mask*, *references*) and tune it until it is quiet on good strings. A rule that fires on every correct string gets switched off and then catches nothing.

**One concept, one rendering.** The same check that finds two translations for one term ([402](../4-terminology/402-terminology-work.md)) finds a short and a long form of the same term. When *Paar* and *Kerningpaar* both translate *pair* in the same catalog, one of them is carrying detail the other lacks. The principles say to keep the shorter and more elegant rendering, and to search for the concept rather than the string, because the second rendering usually hides in a preference description or a history entry.

**Length against the source.** Added detail makes a target longer than its language's usual ratio. A length check does not identify the cause, but a reviewer reading the flagged strings in order of excess finds inflated compounds quickly.

Machine drafts need these checks more than human ones. A model given a glossary entry for *kerning pair* tends to use it wherever it sees *pair*, because the glossary says the term exists. Part 6 describes how to send terms to a model and verify their use ([605](../6-machine-translation/605-glossary-enforcement.md)); the rule of this chapter adds a converse check, that a glossary term does not appear where its source term is absent.

**What the rule protects.** A user learns an interface by matching words. When the menu says *Paar* and the dialog says *Kerningpaar*, the user wonders whether there are two kinds of pair. When the help says *Maskenebene* and the toolbar says *Maske*, the user wonders whether the mask they see is the mask the help describes. The English writer chose one word per concept and a level of generality per context. The translation keeps both, so that the translated interface teaches the same vocabulary the English one does.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 3: language guidelines)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 9)
- `issues/133.md` in the fl10n repository
- `data-fontlab-cpp/i18n/review/2026-09-28-issue133-de.json`, `-es.json` and `-fr.json` in the fl10n repository
- `data-fontlab-cpp/i18n/review/2026-09-28-de-actions.json`, `2026-09-28-de-runtime-glyphs.json`, `2026-09-28-de-lookups-measurements.json` and `2026-09-28-de-window-properties.json` in the fl10n repository
- `data-fontlab-cpp/i18n-repo/fontlab_de.ts`, `fontlab_es.ts` and `fontlab_fr.ts` in the fl10n repository
- `src_docs/md/localization/principles.md`, `quality.md` and `de.md` in the vexy-fontlab-writing-styleguide repository
