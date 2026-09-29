---
this_file: src_docs/md/4-terminology/408-word-formation-and-derivation.md
---

# 408. Word formation and derivation: verbs and adjectives from a noun, native compounds, collective nouns

A glossary entry looks like one word, but in an inflected language it stands for dozens. The Polish noun *trzon* appears in the FontLab catalog as *trzon*, *trzonu*, *trzony*, *trzonów*, *trzonem*, in compounds such as *trzon standardowy* and *łącze trzonu*, and it governs the endings of every adjective that describes it. Choosing a term therefore means choosing a family: the verb, the adjective, the compound, the plural and the case forms that follow from it. This chapter shows how to make those choices consistently, how word formation can solve problems a single word cannot, and what happens to a catalog when a term with a large family is replaced.

## Derive from the chosen noun

Once a language has a noun for a concept, the verb and the adjective should come from that noun, not from the English. The Polish decisions of issue 146 made the rule explicit for two loans:

| Noun | Verb | Adjective | Not |
|---|---|---|---|
| *kerning* | *kernować* | *kernowy*: *klasa kernowa*, *para kernowa*, *wyjątek kernowy* | *kerningować*, *kerningowy* |
| *hinting*, *autohinting* | *hintować* | *hintowy* | *hintingować*, *hintingowy* |

The English *-ing* is a noun ending, and Polish needs its own endings for the verb and the adjective. Building them on the full English noun, *kerning-owy*, doubles the suffix and produces a word that sounds like a machine assembled it. Building them on the root, *kern-owy*, produces a word a Polish type designer can say. The same logic gave *autohinting* rather than *automatyczny hinting*: the profession says the English loan, so the noun stays, and the derived forms follow the root.

German does the same work with a different grammar. The founder's choice of *Metrikausschluss* for *nonspacing* came with its adjective, *metrikausgeschlossen*, so that *nonspacing components* became *metrikausgeschlossene Komponenten* rather than a phrase built on the rejected *ohne Metrikeinfluss*. When a term is chosen, write down its derived forms in the same decision.

The rule holds for the adjectives of the house vocabulary too. *Smart* is an adjective that must agree with every noun it meets: German *schlaue Ecke* but *Schlauer Filter*, Spanish *esquina astuta* but *filtro astuto*, French *coin futé* but *variation futée*, Polish *sprytny narożnik* but *sprytna* with a feminine noun. The core memories record the base form and the language guides record the rule that it inflects; the catalog shows the agreement in every string. A glossary that stored *schlau* as an invariable label would push translators toward ungrammatical German or toward avoiding the word. Record plurals the same way: the German core memory note on *Kerning-Klasse* says, in so many words, that the plural is *Kerning-Klassen*.

## Form native compounds

A compound can be shorter, more natural and easier to derive from than a phrase. Polish *autowarstwa* for *auto layer* replaced *warstwa automatyczna*: one word instead of two, and it inflects as one (*Utwórz autowarstwy*, *przepisy autowarstw*). German made the same move with *Auto-Ebene* instead of *Ebenenautomatik*, and *Dezimalkoordinaten* instead of *Koordinaten mit Nachkommastellen*.

German also shows that compounds need an orthographic rule. The founder's rule in issue 133: native compounds are written closed when they form naturally from native words (*Glyphenfenster*, *Dicktenausdruck*), and compounds whose first part is a thinly loaned English word take a hyphen (*Kerning-Klasse*, *Demo-Modus*, *Master-Dickten*, *Stil-Gruppe*, *Code-Editor*, *Element-Referenz*). The test, as the FontLab principles phrase it for every language: would a native reader see one word, or a borrowed word with a suffix? Other languages apply their own orthography to the same question. Polish writes prefixed forms closed, *autowarstwa*, *superholowanie*; Spanish and French build phrases with *de* rather than compounds.

## Collective nouns and eponyms

### Use a collective noun to dodge an awkward plural

Sometimes the problem is not the word but its plural. FontLab's *Cousins* are glyphs that share a design element with the current glyph, shown beside it for comparison. Polish translated the feature name as *kuzyn* in the singular, but the ordinary plural is trouble: *kuzyni* is the plural for people and *kuzyny* the plural for things, and neither sits right on glyphs. The founder's note in issue 146 compares it to *agenci* and *agenty*, the same split for *agent*.

The solution was a collective noun: *kuzynostwo*, "the cousinhood", grammatically singular. *Ukryj kuzynostwo* (hide the cousins), *glify kuzynostwa* (the cousins' glyphs). The collective noun sidesteps a choice that would have annoyed half the readers either way. The technique generalizes: when a plural forces a grammatical category the concept does not have, look for a collective or a mass noun.

### Decline eponyms

A term named after a person keeps the name, and the name behaves like a name in the target grammar. The Tunni line is named after the type designer Eduardo Tunni. Polish declines the surname in the genitive: *linia Tunniego*, *linie Tunniego*, *Edytuj linie Tunniego*. German builds a hyphenated compound, *Tunni-Linie*; Spanish and French use a prepositional phrase, *línea de Tunni*, *ligne de Tunni*. Leaving the English *Tunni line* in a Polish sentence, as the first Polish catalog did, keeps the surname and loses the grammar.

## Keep distinctions the English keeps, and some it does not

Word formation must not merge concepts. Three Polish decisions of 2026 made distinctions explicit.

**Font tables and interface tables.** An OpenType font is organized in tables: `cmap`, `kern`, `OS/2`, `CVT`. A dialog may also show a table of metrics or names. Polish now uses *tablica* for font tables (*tablica CVT*, *tablica OS/2*, *starsza tablica „kern”*, the *Tablice* panel) and keeps *tabela* for interface tables (*Pokaż tabelę metryk*, *Wczytaj tabelę nazw*). English uses one word for both; Polish gains a distinction a font engineer can use.

**Terminal and stroke end.** The terminal of a letter, the end of a stroke that has no serif, was *zakończenie*, a word that also served for the end of a stroked path. Issue 146 moved the letter's terminal to *zwieńczenie*, a crowning or finish, and left the path's end with its own term, recorded in the core memory as *koniec obrysu*. Two concepts, two words.

**Mark and width.** *Mark* became *diakrytyk*, one noun instead of *znak diakrytyczny*. Its compounds then follow from other decisions: *przyłączanie diakrytyków* for mark attachment and *diakrytyk bez szerokości pola* for nonspacing mark, which reuses *szerokość pola*, the new term for advance width. A good term family reuses its members.

## Changing a term changes every form

The cost of a term with a large family shows when it is replaced. When issue 146 moved *stem* from *kreska główna* to *trzon*, every form of the old phrase had to become the matching form of the new noun, and the two differ in gender: *kreska* is feminine, *trzon* masculine. The adjectives around them change too:

```json
{
  "context": "ActionHeight",
  "source": "Keep horizontal stem at",
  "before": "Zachowaj poziomą kreskę główną na",
  "after": "Zachowaj poziomy trzon na"
}
```

The first automated pass missed the genitive plural. An independent review found twenty catalog strings and four help passages that still read *kresek głównych*, which had to become *trzonów*: *Tolerancja nieregularnych kresek głównych* became *Tolerancja nieregularnych trzonów*. The same review found two other defects that are typical of term replacement in inflected text:

- **A rule that was not idempotent.** The rule that introduced *kod funkcji zecerskiej* for *feature code* also matched its own output, and two strings came out as *kod funkcji zecerskich zecerskich*. A replacement rule must leave its own output unchanged when it runs again.
- **A leftover particle.** *Usuń nakładanie* (remove overlapping) became *usuń nakładki* (remove overlaps), and one string kept the reflexive *się* that had followed the old verbal noun, producing *nakładki się*.

The lessons are practical. Generate the full paradigm of the old term before replacing it, including every case, number and gender form of the phrase and its adjectives. Run the replacement twice and check that the second run changes nothing. Then scan the result for any surviving form of the old term. The FontLab memory guidance states the underlying requirement: glossary lookup and omission checks must understand inflection, or they stay silent in German and Polish. A check that knows only *Kerning-Klasse* reports a missing term whenever the text says *Kerning-Klassen*.

## A worked example: introducing a derived family

A reviewer decides that Polish should say *hintować* and *hintowy*. The procedure:

1. **Record the family** in the core memory note: noun *hinting*, *autohinting*; verb *hintować*; adjective *hintowy*; rejected *hintingować*, *hintingowy*, *automatyczny hinting*.
2. **List the paradigm** of each rejected form: every case of *hintingowy* in three genders and two numbers, every person and tense of *hintingować* the catalog uses.
3. **Replace by message**, not by global substitution, so each change is checked in its sentence and logged with its context.
4. **Run the rule twice** and confirm the second run is empty.
5. **Scan** the catalog, the help and the welcome tips for any surviving rejected stem.
6. **Review in context** a sample of the changed strings in the running application, especially labels near their width limit.

## Sources

- `issues/133.md` and `issues/146.md` in the fl10n repository
- `data-fontlab-cpp/i18n/fontlab_pl.ts` and `data-fontlab-cpp/i18n/review/2026-09-29-issue-146.json` in the fl10n repository
- Commit `1a9825a` in the fl10n repository ("Issue 146: review fixes, genitive plural stems, idempotent feature-code rule")
- `src_docs/md/localization/principles.md`, `src_docs/md/localization/pl.md`, `src_docs/md/localization/memories.md` and `localization/tm/pl-core.tmx` in the vexy-fontlab-writing-styleguide repository
- `localization/tm/de-core.tmx`, `es-core.tmx` and `fr-core.tmx` in the vexy-fontlab-writing-styleguide repository
