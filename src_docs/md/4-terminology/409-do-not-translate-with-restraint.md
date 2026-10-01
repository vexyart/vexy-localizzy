---
this_file: src_docs/md/4-terminology/409-do-not-translate-with-restraint.md
---

# 409. Do-not-translate with restraint: brands, trademarks, identifiers, and everything else that may inflect

Every glossary has a do-not-translate list, and every do-not-translate list grows. It is the safe answer: nobody is blamed for leaving an English word alone. The result is a localized interface that says *Unicode codepoint*, *glyph index*, *CVT table* and *feature code* in the middle of German or Polish sentences, as the first Polish FontLab catalog did, because each of those words once looked technical enough to protect. The founder's instruction in the notes on house voice is short: go easy on do-not-translate. Brands and trademarks stay; almost everything else may be translated, and even a protected name sits inside a sentence whose grammar belongs to the target language.

This chapter separates what must stay English from what only looks as if it should, and shows how a protected name and the words around it behave in an inflected language.

## What must stay

Four kinds of text are protected, each for a different reason.

| Kind | Examples | Why it stays |
|---|---|---|
| Brands and trademarks | FontLab, FontAudit, TransType, Vexy, Fontlab Ltd. | Legal protection and recognition; a translated brand is a different brand |
| Identifiers a program reads | the `kern` table tag, `%1`, file extensions, API names, command names | Changing them breaks the program or the reader's ability to type them |
| Service and domain names | the names of online services, web addresses | The user must find them as written |
| File format identifiers | TrueType, OpenType, UFO, TTX | They name a specification, not a concept of the language |

The FontLab glossary marks such terms `translatable: false`, and the core memories give them the status `do-not-translate`, with the English form repeated as the target so a vendor sees what to ship. The schema adds a caution: the status protects a spelling. It does not approve a draft English name or say anything about whether a feature ships.

Roturier (2015) explains the second row with an example that has not aged. Command-line tools have names like `cut` and `paste` that happen to be English words. A translator who renders "you can merge two files with paste" as *coller* has written a command that does not exist. The same applies to interface labels quoted in documentation when the interface itself is not translated: the reader has to find the English label on screen. Roturier also records the opposite pull: some translators feel a brand should be translated to keep its connotations. For trademarks the law settles the question. For everything else, it is a judgment.

## What only looks like a name

The Polish decisions of the founder's update of 29 September 2026 moved a group of English phrases out of the protected list, because on inspection they were ordinary technical nouns:

| English | First Polish catalog | After the 29 September update |
|---|---|---|
| Unicode codepoint | *Unicode codepoint* | *jednostka unikodu* |
| glyph index | *glyph index* | *indeks glifu* |
| CVT table, OS/2 table | *CVT table*, *OS/2 table* | *tablica CVT*, *tablica OS/2* |
| feature code | *feature code* | *kod funkcji zecerskiej* |
| Cousins, Skin, Sketchboard | English names | *kuzynostwo*, *skórka*, *szkicownik* |

In each case the protected part was smaller than the phrase. *CVT* and *OS/2* are table tags and stay exactly as they are; *table* is a common noun and becomes *tablica*. *Unicode* is the name of a standard, but it has long been naturalized in Polish as *unikod*, written in lower case and declined like any noun: *jednostka unikodu*, *jednostki unikodu glifu*, *Dowolna jednostka unikodu*. A Polish reader meets *unikod* in the same way a German reader meets *Unicode-Codepunkt*: as the language's own word for the thing.

The test is simple. Ask what is protected by law or read by a program. Protect exactly that, and translate the rest.

## The brand stays; the grammar moves around it

A protected name is not frozen out of the sentence. It sits inside the target grammar, and the words around it inflect even when it does not.

German treats FontLab as an invariable name. The German core memory says: never inflect the product name; write *in FontLab*, not *im FontLab*. The name takes no article and no ending, and the sentence is built so that it needs neither.

Polish builds the phrase around the name. *FontLab account* became *konto FontLab*, "the FontLab account", with the brand in apposition after the translated noun. The Polish core memory records the reasoning: the brand name FontLab stays; the Polish segment translates only *account*. The unit keeps the status `do-not-translate`, because the part that matters, the brand, is protected. *Vexy coins* follows the same pattern: *żetony Vexy coin*, tokens of the Vexy coin, where the brand name *Vexy coin* stays and Polish adds only the noun *żetony*.

The pattern generalizes to every inflected language. Put the translated common noun first or last, as the language prefers, and let it carry the case, number and gender. Leave the brand untouched.

## Names of operations are a separate question

Some feature names stay English for a reason that has nothing to do with trademarks: they denote one specific operation, and a translation would suggest a general one. The founder's rule in the review of the German, Spanish and French catalogs concerns *Oblique*. FontLab's Oblique applies a particular set of optical corrections; it is not any slant. German therefore keeps *Oblique* for the operation and uses *Geneigt* only for the PANOSE letterform classification of the same name. The German guide treats *Flex* (a kind of hint) and *OT Def* the same way, following that review.

This rule and the down-to-earth rule of [chapter 407](407-house-voice-across-languages.md) can pull in different directions, and the languages have resolved them differently. The FontLab principles used to list Cousins, Genius, Servant and Skin among the names to keep; since the founder's notes on house voice they ask for a plain native word wherever one is attested and keep the English only where none exists, and German, Spanish and French still keep *Cousins* for now. Polish translated *Cousins*, *Servant* and *Skin* in the 29 September update, keeps *Genius* with a translated noun (*węzeł Genius*, still proposed), and Spanish renders Skin as *revestimiento*. The resolution in both directions is the same test: does the translated word name exactly this operation, or does it suggest a broader one? *Kuzynostwo* names the same view that *Cousins* does. A translation of *Oblique* as a generic slant would not.

## The cost of protecting too much

Over-protection has three costs.

**Readers.** An English phrase in a translated sentence is a word the reader has to recognize in a foreign language, often without its grammar. *Wpisz Unicode codepoint* is harder to read than *Wpisz jednostkę unikodu*, and it cannot take the accusative ending the sentence needs.

**Consistency.** A protected English phrase cannot derive. There is no adjective from *glyph index*, no plural of *feature code* that agrees with Polish numerals. The translator writes around it, and every workaround is a new variant ([chapter 408](408-word-formation-and-derivation.md)).

**Measurement.** In the FontLab coverage figure, a `do-not-translate` unit counts as covered, because it is a decision ([chapter 403](403-a-glossary-schema.md)). An over-long list therefore makes a language look better covered than it is. A term marked do-not-translate to avoid the work of finding an equivalent is a gap reported as a decision.

Roturier (2015) notes the opposite risk too. Some professional audiences prefer English terms, and a translator who translates everything can annoy them; the book's example is Russian customers who preferred API documentation in English. The FontLab principles handle this with attestation rather than with the protected list: an established professional loan such as German *Kerning*, *Hinting* or *Master* is correct because the profession uses it ([chapter 406](406-evidence-and-attestation.md)). That loan is a translation decision, recorded with status `approved`, not a do-not-translate entry. It can inflect and derive (*Kerning-Klassen*, Polish *kernowy*), which a protected string cannot.

## A worked example: one term, two languages

The FontLab core memories record *FontLab account* differently in German and Polish, and the difference shows how to decide.

1. **German.** Status `do-not-translate`, target *FontLab account*. The note: a brand term, so it stays English; *FontLab-Konto* is the natural German form and reads well, but service names carry the English name.
2. **Polish.** Status `do-not-translate`, target *konto FontLab*. The note: the brand name stays; the Polish segment translates only *account*.

Both protect the brand. They differ on whether *account* is part of a service name or a common noun. The German note itself calls *FontLab-Konto* natural, which is the argument for translating it; the Polish decision of the 29 September update follows the founder's later instruction to go easy on do-not-translate. A German reviewer revisiting the entry would apply the test of this chapter: is *account* protected by law or read by a program? If the answer is no, *FontLab-Konto* is the candidate, and the change goes into the ledger with its reason ([chapter 410](410-ledgers-and-decisions.md)).

## Sources

- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 5.4.1: why terminology matters)
- The founder's review remarks on the German, Spanish and French catalogs (September 2026), the founder's update of 29 September 2026 and the founder's notes on house voice, in the FontLab localization project
- The Polish FontLab 9 interface catalog (`fontlab_pl.ts`)
- [glossary/schema.md](https://github.com/Fontlab/vexy-fontlab-writing-styleguide/blob/main/glossary/schema.md) and [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/) in the vexy-fontlab-writing-styleguide repository
- `localization/tm/de-core.tmx`, `es-core.tmx`, `fr-core.tmx` and `pl-core.tmx` in the vexy-fontlab-writing-styleguide repository
