---
this_file: src_docs/md/4-terminology/406-evidence-and-attestation.md
---

# 406. Evidence and attestation: choosing a translation from professional usage, not by translating the word

The most common terminology error in software is not a wrong word. It is a word that nobody in the profession uses. A translator meets *advance width*, finds *advance* and *width* in a dictionary, and writes a phrase that is grammatical, understandable and absent from every book, every competitor's interface and every forum where the users of the product talk to each other. The FontLab memory guidance states the rule plainly: establish an equivalent by research, not by translating the word. This chapter describes the research: where to look, how to weigh what you find, how to record it, and what to do when a decision overrides the evidence.

## Translating the word is not research

Esselink (2000) described the problem when software terminology was younger than it is now. Software uses the latest technology, so reference material is often missing; many terms are new to English itself; and the translator may have to create an equivalent. Esselink's advice was to search specialized magazines in the target language for articles on the same subject, and to be careful with the web: poorly translated websites "only perpetuate bad source and target language equivalents".

Both halves still hold. The first says where attestation comes from: texts written by professionals in the target language for other professionals. The second says what does not count: text that is itself a translation of unknown quality. A machine-translated help page that uses a calque is not evidence that the calque is right; it is evidence that someone else made the same mistake.

## An order of authority

Not all attestations weigh the same. The FontLab principles set an explicit order for font-editor terminology: take usage from Glyphs and FontForge first, then Adobe, then Apple, and only then Microsoft. The order reflects who writes for type designers: the specialist editors first, the design suites next, the operating systems last.

The order reverses for one class of words. Standard commands such as *Copy*, *Paste*, *Quit*, *Undo* and *Preferences* follow the localized platform, because users expect the operating system's word and Qt's own catalogs already use it. Esselink (2000) gives the same rule for that era: translations of standard menu commands must correspond to those of the operating environment.

Books count too. The FontLab evidence review for Polish checked the core memory against nineteen Polish interface glossaries, FontForge and Scribus first, then InDesign and Illustrator, Apple and Microsoft, with Qt for dialog words, and against Polish editions of Bringhurst, Hochuli, Felici and several other books on type and communication. The French review used the French memories of Haralambous and Frutiger. A translator's note in the French core memory shows why both matter: Frutiger writes *fût* for stem, while Haralambous writes *montant* in the context of hinting; the memory records which one it chose and where the other appears.

## Counting and recording attestations

An attestation is worth recording in a form that someone else can check. The Polish core memory writes the evidence into the translator's note as counts per source:

```text
kerning:      FontForge 65; InDesign 20; CoreText 1; Word 4; Inkscape 4; ...
hinting:      FontForge 46; Bringhurst 13; Felici 5
stroke cap:   "zakończenie kreski": InDesign 3
              "koniec/końcówka linii": FontForge 1; Scribus 3; InDesign 4; Freeform 10; Inkscape 3; Felici 1
              "koniec obrysu" (via "stroke"): InDesign 2; Freeform 1
```

The last entry shows how a decision is made from counts without being made by counts. The literal *zakończenie kreski* had three attestations, all from one suite. *Koniec linii* had the broadest support. The review chose *koniec obrysu*, which fits the term the memory already used for a stroke as a path, *obrys*: the cap is the end of an *obrys*, not of a *linia*. Frequency showed which families of words the profession uses; the system of existing terms picked the member.

The result of the Polish review is itself a set of numbers worth keeping:

| Outcome of the September 2026 Polish evidence review | Units |
|---|---|
| Proposals approved on the evidence | 74 |
| Proposals replaced | 18 |
| Proposals kept as proposed, for want of attestation | 59 |

The third row is the honest one. Fifty-nine terms had no attestation strong enough to approve them, and they stayed proposed rather than being approved to make the coverage look better.

### What counts as independent

Counting is easy to fool. The FontLab memory guidance lists the traps:

- Compare material written for the same professional audience, kind of text and task. A consumer word processor and a font editor may both say *kerning*, but they do not mean the same depth of control.
- Record the origin and date of each source. A later translation of a book may describe an older system.
- Repeated navigation or copied passages make a word look common without adding independent support. Inspect the examples before trusting a count.
- An extracted or statistically aligned term is a candidate. Frequency and alignment scores cannot establish the concept.

The `vexy-localizzy` corpus tools build the independence rule into the data. When memories from several sources are imported, each source belongs to a family with a weight. Repeated occurrences within one family contribute one weighted vote, and identical content cannot receive extra votes by being imported again under another family. The winner of a vote is traceable to every source that supported it. When retrieved examples from such a corpus are shown to a model, the toolkit's documentation is explicit that they are examples, not automatic approval of terminology; a glossary entry remains a separate, explicit decision.

## Evidence informs; the decision is recorded

Evidence narrows the choice. It does not always make it, and a terminology process has to allow a decision that goes against the count, provided the decision is explicit.

The Polish FontLab terms give three instances.

**Advance width.** The evidence review kept *szerokość posuwu*, "width of advance", to keep the concept apart from geometric width, against FontForge's *szerokość znaku*. In the update of 29 September 2026 the founder replaced it with *szerokość pola*, the width of the field or box the glyph occupies, which is also the literal sense of the English fallback *glyph box width* ([chapter 404](404-the-fallback-original-term.md)).

**Stem.** The evidence review approved *kreska główna*, the main stroke. The founder chose *trzon*, which gives the compounds *trzon standardowy* and *łącze trzonu*.

**Master.** Felici's Polish text renders type masters as *wzorzec*, a pattern. The lock on *matryca*, the casting matrix, stands: it sounds like the English and names the right thing, and the founder confirmed it.

In each case the earlier, evidence-based form is recorded in the core memory note as *poprzednio*, previously, beside the new term and the issue number. The next reviewer can see both the evidence and the decision that overrode it, and can argue with either.

The same holds for corporate memories, which are evidence of a kind. The FontLab principles warn that they are often wrong: an *old style* typeface in Polish is *antykwa renesansowa*, not the *stary styl* a general-purpose memory offers.

## Check the meaning, not only the word

A term can be attested and still wrong for the string. The 2026 research corpus gives an example from model translation: typographic *Kern* rendered with the German word for a seed or nut. The word exists; the concept is wrong.

The German FontLab review checked meaning against the program itself. When it reconsidered the label *Descender to UPM*, the ledger entry cites the functions in the FontLab source that set the target height and the lower reference, and derives the wording from the geometric effect. The Spanish guide cites translation units of an Illustrator memory to confirm *manejador de curva* for a curve handle, and records why *controlador* was rejected: it could be confused with a software component.

A published sentence is evidence of what was published. It is not proof that it names the right object.

## A worked example: choosing a term for a new concept

A reviewer has to choose a Polish term for *stroke cap*, the shape at the open end of a stroked path.

1. **State the concept** from the glossary definition, and note its neighbours: *stroke* as a path is *obrys*; the *terminal* of a letter is a different thing.
2. **Search the authorities in order**: FontForge and Scribus, then InDesign and Illustrator, then Apple and Microsoft, then the type books.
3. **Count and record** each candidate with its sources, as in the note above.
4. **Check the system.** A candidate that breaks an existing term family, here *obrys*, loses even with more attestations.
5. **Record the choice** with status approved, the counts in the note and the replaced proposal named.
6. **Keep the distinction.** When the founder later moved the letter's terminal to *zwieńczenie*, the stroke cap kept its own word, so the two concepts stayed apart ([chapter 408](408-word-formation-and-derivation.md)).

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 12: introduction, terminology reference materials, operating environment glossaries)
- [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/), [localization/memories](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/memories/), [localization/pl](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/pl/) and [localization/es](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/es/) in the vexy-fontlab-writing-styleguide repository
- `localization/tm/pl-core.tmx` and `localization/tm/fr-core.tmx` in the vexy-fontlab-writing-styleguide repository
- The German consistency ledger of 28 September 2026 and the founder's update of 29 September 2026, in the FontLab localization project
- [docs/corpus.md](../8-toolkit/corpus.md) and [docs/retrieval.md](../8-toolkit/retrieval.md) in the vexy-localizzy repository
