---
this_file: src_docs/md/5-interface/505-plurals-in-practice.md
---

# 505. Plurals in practice: three Qt forms, four CLDR categories, fractions and zero

Chapter [107](../1-foundations/107-plurals-gender-and-message-formats.md) explains plural rules in principle: CLDR's categories, ICU's `plural` argument and Qt's `%n`. This chapter is about the moment a translator opens a numerus message in a Qt catalog and has to fill in two, three or more forms. The theory is settled. The practice still goes wrong, for three reasons: the categories of CLDR and the forms of Qt do not line up one to one, a count controls more words than the noun beside it, and a message often contains a second number that the plural machinery ignores.

## Two systems that count differently

CLDR defines up to six plural categories (`zero`, `one`, `two`, `few`, `many`, `other`), and only `other` is mandatory. The category names are selectors defined per language, not numeric ranges: French `one` covers 0 and 1, Polish `few` covers 22 but not 12. Qt numerus messages instead carry a fixed list of forms per language, chosen by Qt's own plural rules from the integer passed as `n`. The two systems agree for most languages and most numbers. They disagree exactly where translators are least likely to look.

| Language | CLDR categories | Qt forms | Numbers to test |
|---|---|---|---|
| German | one, other | 2 | 0, 1, 2, 21 |
| Spanish | one, many, other | 2 | 0, 1, 2, 21 |
| French | one, many, other | 2 | 0, 1, 1.5, 2, 21 |
| Polish | one, few, many, other | 3 | 0, 1, 2, 5, 12, 22, 25, 102 |

The Polish row is the instructive one. Qt's three Polish forms are: exactly one; numbers ending in 2, 3 or 4 except 12, 13 and 14; everything else. CLDR adds a fourth category, `other`, for fractions, which take the genitive singular: *1,5 pliku* (1.5 files), not *1,5 plików*. Qt has no form for it because `%n` is an integer. The FontLab research synthesis records that sources cite Polish as having three forms or four, and traces the disagreement to whether the fraction category is counted. Both counts are right about different systems.

Spanish and French have a CLDR `many` category for exact millions and larger round numbers, which take *de*: *1 millón de glifos*. Qt gives both languages two forms, so a Qt catalog cannot express this distinction at all; if the product can show a count of a million, the wording must work with the ordinary plural. For French, CLDR places 0 in `one`, so *0 glyphe sélectionné* is correct French. Which Qt form the French build selects for zero is a question for the build, not for the catalog: compile the catalog with the native tool and look.

vexy-localizzy encodes this separation. Its catalog check requires the caller to supply the exact native plural positions for the target locale and never substitutes CLDR categories for Qt's integer positions; a missing plural rule is reported as a finding rather than guessed.

## What changed since 2000

Esselink (2000) describes run-time plurals as they were then built: a string such as *Copying %d file%s* in which the program inserted an *s* when the count was two or more. German *Datei* becomes *Dateien*, *Ordner* stays *Ordner*, and no appended letter can express both. His advice was to delete the `%s` and choose a wording that covers singular and plural. Uren, Howard and Perinotti (1993) had already told developers to keep two strings, one singular and one plural, rather than adding *s*.

Both recommendations are historical. Numerus forms in Qt, and plural arguments in ICU MessageFormat, give each language as many forms as its grammar needs. What remains of the old problem sits on the English side. A Qt source string reads *%n glyph(s)*, and without an English catalog that supplies *%n glyph* and *%n glyphs*, English users see the parenthesis. FontLab ships `fontlab_en.ts`, which supplies exactly those two forms, and the research synthesis gives the same advice for every Qt project: generate a source-language catalog when source strings use plurals.

## What a count governs

A numerus message is not a noun with an ending. The count agrees with the noun, the noun may govern an adjective, and in many languages the count also decides the form of the verb. Polish shows all of it in one message from the FontLab component dialog:

```xml
<message numerus="yes">
    <source>&lt;b&gt;%n glyph(s) will be deleted:&lt;/b&gt; %1</source>
    <translation>
        <numerusform>&lt;b&gt;%n glif zostanie usunięty:&lt;/b&gt; %1</numerusform>
        <numerusform>&lt;b&gt;%n glify zostaną usunięte:&lt;/b&gt; %1</numerusform>
        <numerusform>&lt;b&gt;%n glifów zostanie usuniętych:&lt;/b&gt; %1</numerusform>
    </translation>
</message>
```

The noun changes (*glif*, *glify*, *glifów*), and so does the verb: singular *zostanie* with one glyph, plural *zostaną* with two to four, and singular again with five or more, because a Polish numeral from five up takes a genitive plural noun and a singular neuter verb. The participle follows its own pattern (*usunięty*, *usunięte*, *usuniętych*). A translator who inflects only the noun produces two wrong forms out of three.

A governing word changes the picture again. *%n glyph(s) are missing* becomes *Brakuje %n glifu*, *Brakuje %n glifów*, *Brakuje %n glifów*: the verb *brakować* requires the genitive, so the second and third forms coincide. In *One node in %n contour(s)* the preposition *w* takes the locative, and the translation reads *w %n konturze*, *w %n konturach*, *w %n konturach*. Identical forms in a numerus message are not a mistake to be flagged; they are what the grammar produces after a verb or preposition that fixes the case. German shows the milder version: *%n Glyphe fehlt*, *%n Glyphen fehlen*, with the verb in both.

Some numerus strings have no visible number. *Offset node(s)* is a history entry whose wording depends on how many nodes were selected. English needs two forms; German writes *Knoten versetzen* in both, because *Knoten* has the same plural; Polish writes *Przesuń węzeł*, *Przesuń węzły*, *Przesuń węzły*. The form still follows the count the program passes.

## Two numbers, one plural

Qt chooses the form from `%n` alone. Any other number in the message is ordinary text, and the translation must read correctly whatever its value. The FontLab review met three versions of this problem, and the catalogs record how each was handled.

**Make the phrase agree with nothing.** The glyph deletion dialog once passed the number of glyphs to delete as `%1` and the size of the selection as `%n`, so the plural followed the wrong count. The reviewed German read *Glyphen zum Löschen (%1 von %n):*, glyphs to delete, %1 of %n, and the Spanish *Glifos que se eliminarán (%1 de %n)*. Both kept a plural noun that is correct for any count and put the numbers in parentheses where no agreement is needed. A verb agreeing with the total would have been wrong whenever one glyph was deleted from a larger selection.

**Ask for `%n` where the grammar needs it.** That workaround was a translation's answer to a source defect, and the source has since been changed. The current English reads *%n glyph(s) will be deleted (out of %1): %2*, with the deleted count in `%n`. The translations now agree with the right number: German *%n Glyphe wird gelöscht (von %1)*, Spanish *Se eliminará %n glifo (de %1)*, Polish *Zostanie usunięty %n glif (z %1)* with its three verb forms. The same happened to a class label that once gave its glyph count as `%1`, for which the German guide had recommended *Glyphen in Klasse „%2“: %1* so that the number 1 would not produce *1 Glyphen*; the source is now the numerus message *%n glyph(s) in class "%1"*. The label-and-value form is the right workaround while a source fix is pending, and the fix is the right end state ([508](508-source-text-as-evidence.md)).

**Recast as label and value when the second number stays.** *%1 nodes in %n contour(s).* keeps a node count in `%1` that the plural does not see. German and French write *%1 Knoten in %n Kontur* and *%1 nœuds dans %n contour*, which read correctly only if `%1` is never 1. The catalog has a separate message, *One node in %n contour(s).*, which suggests the program never passes 1 here, but the translation cannot see the code. The Polish translation removes the question: *Węzłów: %1 w %n konturze.* The genitive plural *węzłów* before a colon is correct for any number, and the plural machinery handles only the contours. When a message contract does not state the range of a second number, the label-and-value form is the safe choice.

Zero and fractions each need a decision of their own. An explicit zero message (*No glyphs selected*) is a separate branch from a language's plural category, and the writing guide's message-contract page warns against confusing the two: a special message for exactly zero is not evidence that the language has a `zero` category. Fractions cannot pass through `%n`, which is an integer; a measurement such as a stem width of 1.5 units belongs in a message whose number is formatted by the locale and whose noun works for any value, for example as a label and value.

## Testing a plural string

The FontLab review settled on a fixed list of test values per language, shown in the table above, and on four rules for reading numerus messages.

1. Every form contains `%n` if the source does. The FontLab quality specification lists this among the automated checks, and vexy-localizzy's default Qt policy checks exact `%n` and `%Ln` multiplicity in every form.
2. The number of forms matches the target language, and no form is empty. A Polish message with two forms is incomplete however good the wording.
3. No `one` form prints a literal *1* in a language where `one` covers other values. French `one` includes 0 in CLDR; the interface-strings page asks reviewers to reject such a branch.
4. The whole sentence agrees for each test value: noun, adjective, verb and participle. Read the rendered message for 0, 1, 2, 5, 12, 22 and 25 rather than the forms in isolation.

The first two rules are structural and belong to a script. vexy-localizzy's catalog check visits every native plural form of every active message and fails on missing or extra forms and empty targets. Its browser reviewer asks for the plural positions of each catalog and shows every form for editing. The last two rules need a reader who knows the language. The final check belongs to the native compiler: after `lrelease` has built the binary catalog, a build of the application run with the test values shows which form each number selects.

Qt catalogs are not the only format with this problem; gettext and ICU messages handle plurals in their own ways ([303](../3-formats/303-gettext-po.md), [107](../1-foundations/107-plurals-gender-and-message-formats.md)). The habits of this chapter transfer unchanged. Know which system selects the form, test the numbers where the language changes its mind, and read the whole sentence.

## Sources

- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (section 4.4.1)
- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 3: variables)
- `research/01-foundations-of-software-localization.md` (section 1.4) in the fl10n repository
- `data-fontlab-cpp/i18n-repo/fontlab_en.ts`, `fontlab_de.ts`, `fontlab_es.ts`, `fontlab_fr.ts` and `fontlab_pl.ts` in the fl10n repository
- `data-fontlab-cpp/i18n/review/2026-09-28-de-glyph-dialogs.json` and `2026-09-28-de-panels.json` in the fl10n repository
- `src_docs/md/localization/ui-strings.md`, `message-contracts.md`, `quality.md`, `de.md`, `es.md`, `fr.md` and `pl.md` in the vexy-fontlab-writing-styleguide repository
- `docs/quality.md` and `docs/review.md` in the vexy-localizzy repository
