---
this_file: src_docs/md/4-terminology/403-a-glossary-schema.md
---

# 403. A glossary schema: term, definition, status, collision, translatable, sources

A glossary is a set of records, and the quality of the glossary is mostly the quality of its record design. A record with too few fields forces people to put decisions into free text where no tool can find them. A record with too many fields becomes a second style guide that nobody maintains. This chapter walks through the fields a software glossary needs, shows the schema FontLab uses, and gives the reason for each field, so that you can adapt the design rather than copy it.

## What published termbases record

The published practice converges on a small core. Esselink (2000) lists the fields of an entry in a client termbase: subject field, source term, a context sentence, a definition, synonyms or acronyms, target terms and their synonyms, the source of the term or of the definition, and product, version or project identifiers. The book adds two rules that still matter: nouns are entered in the singular and verbs in the infinitive, and a single person should validate new entries, because merging lists that disagree in spelling and form is close to impossible.

Jiménez-Crespo (2024) describes the Microsoft Terminology Collection, distributed in the TBX format, with six data points per entry: concept identifier, definition, source term, source language, target term and target language. Citing Bowker (2020), Jiménez-Crespo notes that localization termbases often go further, with part of speech, alternative terms and synonyms, product line, context, screenshots of the interface and usage notes.

Two ideas stand out. The entry is about a concept, which is why it has an identifier independent of the word. And the entry carries its evidence, which is why sources and context are fields, not comments.

## One term, one file

The FontLab writing styleguide stores each English term as one YAML file under `glossary/terms/<id>.yaml`. The translations do not live in that file. They live in one core translation memory per language (TMX 1.4), with one translation unit per term ([chapter 405](405-core-and-project-memories.md)). Splitting the two keeps the English definition in one place and lets each language move at its own pace.

```yaml
# this_file: glossary/terms/overshoot.yaml
id: overshoot
term: overshoot
category: type-design
products: [fontlab, fontographer]
status: approved
definition: |
  Overshoot is the extension of a rounded or pointed shape beyond an alignment
  line so that it appears as tall as a flat shape. For example, an o may
  extend above the x-height and below the baseline. Its amount depends on the
  design and intended size. PostScript alignment zones can describe these
  overshoot regions for hinting; there is no universal percentage to apply.
usage:
  do: "You give the o an overshoot so it matches the x in height."
  dont: "Set overshoot to two percent of UPM in every typeface."
collision: null
see_also: [alignment-zone, x-height, baseline, bowl]
sources:
  - products/fontlab-app/.../hinting-02-01-zones-and-stems-concepts-and-overview.md
fallback: optical surplus
translatable: true
```

### The fields and their reasons

| Field | What it holds | Why it exists |
|---|---|---|
| `id` | A lowercase slug, unique, never changed | The term text changes; references to it must not |
| `term` | The term as written in English prose, in house capitalization | So the glossary shows the form writers use |
| `also` | Accepted synonyms and variant spellings | A terminology check has to catch the wrong spelling, so it has to know it |
| `category` | One of a fixed set, such as `type-design` or `interface` | A flat list of several hundred terms is not a page anyone reads |
| `products` | The products the term applies to | A translator working on one product should not read another's terms |
| `status` | `approved`, `draft` or `deprecated` | The glossary can carry an unsettled name without pretending it is settled |
| `definition` | At most 100 words, starting with what the thing is | The concept, in words a translator can check the target against |
| `usage.do`, `usage.dont` | One copyable sentence and one counterexample | A rule someone can copy gets followed |
| `collision` | Null, or both meanings when products share the word | Shared nouns mean different things in different applications |
| `see_also` | Up to five related ids | Terms are learned in clusters |
| `sources` | Where the term is attested in the product corpus | So a claim can be checked |
| `fallback` | Optional plain English rendering, at most six words | So a translator has a second source text when the term will not travel ([chapter 404](404-the-fallback-original-term.md)) |
| `translatable` | `false` for product names, services, domains, format identifiers | The fastest way to break a localized manual is to translate a product name |

The schema documents its own reasons in the repository, and the reasons are the part worth copying. The 100-word cap on definitions, for example, exists because "the risk this glossary runs is becoming a second style guide". Advice about how to use a term belongs in the language guides; the glossary says what the term is.

## Status is a decision state

The English glossary and the per-language memories need different status values, because they record different decisions.

In the English file, `status` says whether the English term itself is settled. A feature name that has shipped but may still change is `draft`. A term that should no longer be written, except in historical references, is `deprecated`.

In a core memory, each translation carries its own status:

- **`approved`**: reviewed and usable;
- **`proposed`**: a suggestion waiting for a native reviewer;
- **`do-not-translate`**: the English form is the target form, and the target segment repeats it so a vendor sees what to ship.

The FontLab schema defines a coverage figure from these values. A term counts as covered when its translation is approved or marked do-not-translate, because both are decisions. A proposed translation does not count until someone approves it. A language with no memory at all reports zero, which is the honest answer. [Chapter 409](409-do-not-translate-with-restraint.md) returns to a side effect of this rule: because do-not-translate counts as covered, an overused do-not-translate list makes a language look better covered than it is.

## Collision, translatable and sources

Three fields protect against the errors that cost the most.

**Collision** is for nouns that one company uses with different meanings in different products. The FontLab schema requires a collision note on all ten nouns shared with the Vexy applications, and its checker fails the build if one is missing. The note for *layers* names three meanings: a glyph layer in FontLab, a transparent sheet of fills in Vexy Lines, and an Illustrator-style stacking level in Vexy Vextra.

**Translatable** is a boolean on purpose. A product name is either protected or not. The field decides whether a term may have a fallback original term and whether a translator may render it; it does not decide how the protected name behaves in a sentence, which is a grammar question ([chapter 409](409-do-not-translate-with-restraint.md)).

**Sources** point at the product documentation where the term is attested. They are required for approved terms and are kept out of the published page, because they are research paths. The rule against inventing a precise path when the evidence is a whole directory is written into the schema.

## Checks that keep the glossary honest

A schema is only as good as the program that enforces it. The styleguide's `check_terms.py` refuses to generate the glossary pages when:

- a `see_also` id does not resolve to a term file;
- a shared noun lacks its collision note;
- a core memory contains a unit whose `x-term-id` has no term file, which would be a translation of a term that no longer exists;
- a fallback original term is longer than six words, contains a dash, repeats the term, or sits on a brand or non-translatable term;
- a core memory's copy of the fallback differs from the glossary's.

A second script, `check_tm.py`, keeps the core memory and the project memories apart: it fails when a core source segment reappears in a project memory ([chapter 405](405-core-and-project-memories.md)).

None of these checks judges the quality of a definition. They make the structure impossible to break quietly, which leaves the reviewers free to read the content.

## A worked example: writing an entry

Take the *Tunni line*: a line that joins the two handles of a curve segment, with a control that moves both handles in proportion, named after the type designer Eduardo Tunni. FontLab and Vexy Vextra both have it. Write the entry in this order.

1. **Choose the id and term.** `tunni-line`, `Tunni line`: the capital stays because it is a surname.
2. **Write the definition.** Start with what it is, then what it does and where it appears. Stay under 100 words. Check it against the product.
3. **Write the usage pair.** The `do` sentence uses the term correctly in the house register. The `dont` sentence shows a specific error, such as treating the line as a guide the user draws.
4. **Decide collision and translatability.** No other product uses the word, so `collision: null`. It is a descriptive name, not a brand, so `translatable: true`.
5. **Consider a fallback.** Would a translator without a native equivalent be helped by a plain rendering? The FontLab glossary gives *curve tension line*.
6. **Add sources.** The manual article where the feature is described; the styleguide entry cites the Vextra article on Tunni lines.

Then the languages follow in their own memories. German wrote *Tunni-Linie*, Spanish *línea de Tunni*, French *ligne de Tunni* and Polish *linia Tunniego*, with the surname declined in the genitive ([chapter 408](408-word-formation-and-derivation.md)).

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 12: reference materials, multilingual client terminology database, standards)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 3: terminology and localization, note 17)
- [glossary/schema.md](https://github.com/Fontlab/vexy-fontlab-writing-styleguide/blob/main/glossary/schema.md), `glossary/terms/overshoot.yaml`, `glossary/terms/layers.yaml`, `glossary/terms/tunni-line.yaml`, `scripts/check_terms.py` and `localization/tm/*-core.tmx` in the vexy-fontlab-writing-styleguide repository
- The founder's update of 29 September 2026, in the FontLab localization project
