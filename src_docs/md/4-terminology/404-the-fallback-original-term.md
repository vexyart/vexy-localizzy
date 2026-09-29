---
this_file: src_docs/md/4-terminology/404-the-fallback-original-term.md
---

# 404. The fallback original term: a plain English rendering for when the term will not travel

Some English terms carry their meaning in a metaphor that other languages do not share. *Overshoot* names, in a font editor, the few units by which an *o* rises above the x-height so that it looks as tall as an *x*; the word itself says only that something went past a line. *Stem* is a word from plants. *Advance* says that something moved forward, not how far a glyph box is. A translator who meets such a term has three bad options: borrow the English word, which a reader may not know; translate the metaphor literally, which produces a calque nobody uses; or explain the concept, which produces a phrase too long for a label.

The fallback original term is a fourth option. Beside the English term, the glossary stores a short, plain English rendering of the same concept, chosen so that translating it literally gives a defensible target term. The translator can translate that instead. This chapter explains what a fallback is and what it is not, when to write one, how a translator uses it and where it lives in the data.

## The case that produced the idea

The Polish FontLab interface first rendered *overshoot* as *wydłużenie optyczne*, "optical lengthening". The phrase is accurate and describes the effect, but it is long, it says lengthening where the shape also extends downward below the baseline, and it gives no adjective or compound to build on. In issue 146 the founder replaced it with *naddatek*, the ordinary Polish word for an allowance or surplus, glossed in the same line as an optical surplus, and added: "we should also use this principle in other languages if we're unsure".

That remark names the principle. What the founder translated was not *overshoot* but a plainer English description of the concept, *optical surplus*, keeping only the noun; in a font editor the optical context goes without saying. The Polish core memory records the decision with the note *naddatek optyczny; ta zasada może służyć także innym językom*: the principle may serve other languages too. The English glossary now stores *optical surplus* as the fallback of *overshoot*, so that the next translator into any language starts where the founder finished. (Issue 147 phrased the same example as *architectural surplus*; the glossary kept the wording of issue 146.)

*Stem* followed the same path. Its glossary definition calls a stem the main stroke of a letter, and its fallback is *main stroke*. After an evidence review of Polish type literature, the Polish interface used *kreska główna*, which is exactly the literal translation of that fallback, until the founder settled on *trzon*, the shaft or trunk, which yields the compounds the interface needs: *trzon standardowy* for standard stem, *łącze trzonu* for stem link. The interim term shows what a fallback is for: it gives a language a correct, understandable term until a better one is chosen.

## What a fallback is, and what it is not

A fallback is a second source text for one concept. It is not a synonym to vary prose with, and it is not a definition.

| | Fallback original term | Definition | Synonym (`also`) |
|---|---|---|---|
| Length | At most six words | Up to 100 words | One term |
| Form | A noun phrase or verb phrase, like the term | Full sentences | A variant spelling or alternative name |
| Purpose | To be translated literally when the term will not travel | To explain the concept for checking | To be recognized and mapped back to the term |
| Appears in the English product | No | In glossary pages and help | Sometimes, as a variant |

The test for a good fallback is the literal translation. Translate it word for word into a few languages. If the result is a plausible term in each, one a professional would accept in a label, the fallback works. If the result is an explanation, the fallback is a definition in disguise and should be shortened. *Optical surplus* passes: *naddatek optyczny*, *optischer Überschuss*, *excedente óptico*. *The extra height a round letter needs to look aligned* fails: it is a definition.

A fallback also avoids the source of the difficulty. *Main stroke* removes the botany from *stem*. *Glyph box width*, the fallback of *advance width*, removes the typewriter. *Layout subroutine*, the fallback of *lookup*, removes the programmer's jargon and says what the thing is in an OpenType font.

## When to write one, and when not to

Write a fallback when all three conditions hold:

1. **The term is translatable.** It names a concept, not a brand.
2. **The English word depends on a metaphor, an etymology or a jargon habit** that a target language may not share. A term the professions share, such as *kerning*, may still carry one for the many languages that lack the loan; the FontLab glossary errs on that side, which is why most of its entries have a fallback.
3. **A plain rendering exists** that is short enough to be a term and precise enough to name only this concept.

Do not write one for brands, trademarks, product names or file format identifiers. They are not translated, so a second source text makes no sense; the FontLab checker refuses a fallback on any term that is marked non-translatable or belongs to the brand category. *FontLab*, *FontAudit* and *Vexy* have none.

Do not write one that repeats the term. The checker refuses that too, along with any fallback of more than six words or containing a dash.

Do write one for coined feature names when they are translatable. The FontLab glossary gives *Sketchboard* the fallback *scratch canvas*, *Matchmaker* the fallback *master matcher*, *Power Guide* *linked guideline*, *Genius node* *self-balancing node*. These tell a translator what the name refers to in the most direct words available, which is what a translator needs before deciding whether to translate the name playfully ([chapter 407](407-house-voice-across-languages.md)).

## How a translator uses it

The fallback does not replace research. It is what a translator reaches for when research comes up empty or produces something unusable.

1. **Look for an attested equivalent first** ([chapter 406](406-evidence-and-attestation.md)). German type designers say *Dickte* for advance width and *Überstand* for overshoot; French says *fût* for stem. Where the profession has a word, use it, and the fallback plays no part.
2. **If there is none, or only a calque or an explanatory phrase, translate the fallback literally** and treat the result as a candidate term.
3. **Test the candidate.** Does it name the concept and nothing else? Does it fit the tightest label that uses it? Can the language derive the forms it needs: the plural, the adjective, the compound ([chapter 408](408-word-formation-and-derivation.md))?
4. **Shorten where context allows.** *Naddatek optyczny* became *naddatek*, because in a font editor the optics go without saying.
5. **Record the result** in the core memory with a note saying that it came from the fallback, so a reviewer can see the route.

The Polish FontLab terms of issue 146 show how often the literal route works. Several read as direct translations of the fallback:

| English term | Fallback | Polish | Literal sense of the Polish |
|---|---|---|---|
| overshoot | optical surplus | *naddatek* | surplus, allowance |
| advance width | glyph box width | *szerokość pola* | width of the field |
| vertical advance | glyph box height | *wysokość pola* | height of the field |
| lookup | layout subroutine | *podprogram zecerski* | typesetter's subroutine |
| stem (interim) | main stroke | *kreska główna* | main stroke |

Not every Polish decision follows the fallback, and it does not have to. *Nudge* has the fallback *push move*, and an earlier Polish rendering, *pchnięcie*, was close to it. The founder chose *holowanie*, towing, which is funnier and gives *superholowanie* for Power Nudge. The fallback is a floor, not a ceiling: it guarantees a correct term, and a better idea may still win.

## Where the fallback lives

The fallback is English data, so it lives with the English term. In the glossary it is an optional field:

```yaml
id: stem
term: stem
category: type-design
status: approved
definition: |
  A stem is a main stroke of a letter, usually the vertical one: ...
fallback: main stroke
translatable: true
```

Every core memory copies it as a property of the translation unit, beside the term id and status, so that a tool that reads only the memory still sees it:

```xml
<tu tuid="term:overshoot">
 <prop type="x-term-id">overshoot</prop>
 <prop type="x-category">type-design</prop>
 <prop type="x-translatable">yes</prop>
 <prop type="x-fallback">optical surplus</prop>
 <prop type="x-status">approved</prop>
 <note>Overshoot is the extension of a rounded or pointed shape ...</note>
 <tuv xml:lang="en"><seg>overshoot</seg></tuv>
 <tuv xml:lang="pl">
  <note>Naddatek optyczny; ta zasada może służyć także innym językom.</note>
  <seg>naddatek</seg>
 </tuv>
</tu>
```

TMX 1.4 reserves the `x-` prefix for user-defined property types, so the file stays valid for any tool that reads TMX ([chapter 306](../3-formats/306-tmx-and-tbx.md)). The styleguide's `coretm.py` writes the property from the glossary, and `check_terms.py` fails when a memory's `x-fallback` disagrees with the glossary's `fallback`, so the two cannot drift apart.

A translation pipeline can use the property too. When a target language has no approved rendering of a term, the batch sent to an engine can carry the fallback beside the English term, with an instruction to translate the fallback as a term. Whether a pipeline does this is a design decision for the glossary enforcement step described in [chapter 605](../6-machine-translation/605-glossary-enforcement.md); the data is there either way.

## Traps

- **Definition creep.** A fallback that grows into a clause has become a definition. Keep it at six words or fewer, and prefer two or three.
- **Jargon for jargon.** *Pair spacing correction* for *kerning* helps; *GPOS adjustment* would not. The fallback must be plainer than the term.
- **Leaking into English.** The fallback is not an alternative for English writers. The English interface and manual keep the term; the fallback exists for translators.
- **Mistaking it for approval.** A literal translation of a fallback is a candidate. It still needs a reviewer, a status and, if it is chosen, a ledger entry.

## Sources

- `issues/146.md` and `issues/147.md` in the fl10n repository
- [glossary/schema.md](https://github.com/Fontlab/vexy-fontlab-writing-styleguide/blob/main/glossary/schema.md), `glossary/terms/overshoot.yaml`, `glossary/terms/stem.yaml`, `scripts/check_terms.py`, `scripts/coretm.py` and `localization/tm/pl-core.tmx` in the vexy-fontlab-writing-styleguide repository
- [localization/pl](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/pl/) and [localization/de](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/de/) in the vexy-fontlab-writing-styleguide repository
- `data-fontlab-cpp/i18n/review/2026-09-29-issue-146.json` in the fl10n repository
