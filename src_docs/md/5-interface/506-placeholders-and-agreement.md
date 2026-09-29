---
this_file: src_docs/md/5-interface/506-placeholders-and-agreement.md
---

# 506. Placeholders and agreement: label and value, case, gender and runtime assembly

Part 2 explains how an engineer should build a message with variables ([204](../2-engineering/204-placeholders-and-grammar.md)): one complete sentence per string, numbered arguments, no concatenation. This chapter starts where engineering stopped. The translator receives the strings the product actually has, some of them built well and some not, and has to produce text that reads correctly for every value the program may insert. Three questions decide most cases. What does each placeholder stand for? What in the sentence must agree with it? And is the string a whole sentence, or a piece of one?

## What a placeholder promises

A placeholder is a promise that the program will insert something at that point, and the promise has two parts: what the value is, and how it is marked.

The marking matters for reordering. Qt's numbered placeholders (`%1`, `%2`, and the locale-formatted `%L1`) can move anywhere in the translation, because the number identifies the argument. Anonymous C placeholders (`%s`, `%d`) are filled in order, so they cannot move. Esselink (2000) warned that a string such as *Choose %s to copy %s* must not be reordered, or the user might read *To copy Continue, choose SAMPLE.DOC*. Dr International (2002) showed the same trap with Swedish and Finnish, where *open* comes before the file name in one and after it in the other, and showed the Windows answer: numbered inserts, so the Finnish translation can place `%2` before `%1`. The advice against reordering is historical for Qt catalogs and still current for any anonymous format. The FontLab interface-strings page states the modern rule in one line: numbered placeholders may be reordered, anonymous `%s` may not, and the placeholder syntax never changes during a prose edit.

The value is harder, because the string does not say what it is. Esselink's example is *%s to %s.*: at run time it may read *Monday to Friday*, *Copying file.dll to C:\windows\system* or *23 to 54*, and in most languages *to* translates differently in each. Dr International describes a translator who met a string of anonymous variables and the word *on*, and could not know what *on* meant until the programmer listed them: minutes, a.m. or p.m., a weekday, a month, a day, a year. The fix in both books is the same. Find out what each value is, from a comment, a screenshot, the running program or the developer, before translating the words between them. Guessing from how the English reads is how a copy destination gets the preposition of a date range.

## Agreement the string cannot know

English lets a noun stand in a slot without affecting the words around it. Most languages do not. Esselink's pair of examples is still the canonical one: *This is not a valid %s.*, where *valid* must agree with the gender of the inserted noun, and *%1 already exists. Do you want to replace it?*, where *it* must. Dr International gives the Spanish series *primero*, *primera*, *primer*, *primeros*, *primeras* for a single English *first*, and Esselink gives German *Keine* or *Kein* for *None*, depending on a noun the string never mentions. French *Nouveau %1* cannot agree with an unknown noun either.

Case adds a second dimension. Polish nouns change form after prepositions and verbs, but a name inserted into `%1` arrives in whatever form the program holds it, usually the nominative. A sentence that puts `%1` after a preposition requiring the genitive cannot be made grammatical by the translator. German has the same issue in milder form with articles.

Four responses exist, in rough order of preference.

1. **Recast as label and value.** *%1: invalid value* agrees with nothing. The colon turns the inserted noun into a heading, and the grammar of the rest no longer depends on it. This rescues most gender and case problems at the cost of a slightly more technical tone.
2. **Choose a verb or structure that does not agree.** Polish *Wybrano %n fontów* (literally, "there were selected %n fonts") uses an impersonal verb form that stays the same whatever follows. German passive and infinitive constructions often avoid agreement in the same way.
3. **Ask for one string per case.** Dr International recommends writing out each sentence in full, *Are you sure you want to delete the directory?* and *Are you sure you want to delete the subdirectory?*, rather than one sentence with a slot. This is the correct end state, and it needs a source change.
4. **Report the source.** A string that cannot be translated correctly for its possible values is a source defect. The FontLab principles say to report it and not to guess, and [508](508-source-text-as-evidence.md) describes how.

The first two responses are the translator's; the last two are the translator's request to engineering. A translation that simply picks the gender of the most common value is a guess dressed as a decision, and the ledger should say so if it ships that way.

## Sentences the application assembles

The hardest strings are fragments. A trailing space, a leading space or an obviously unfinished phrase means the program joins this string to something else at run time. Esselink's *Can't find record* with a trailing space is followed by a record number; a German translation that keeps English word order ends up with the verb in the wrong place and the number glued to it. His answer for strings that cannot be reordered is a colon, *Widerrufen: Ausschneiden* for an assembled *Undo Cut*, and the colon is still the standard rescue.

Dr International adds the layout version of the problem: a text field or drop-down placed in the middle of a sentence. The German translation of such a sentence needs the control in a different position, and the localizer must either move it or accept broken syntax. The recommended design keeps controls outside the sentence.

**Worked example: the kerning dialogs.** FontLab's kerning adjustment dialog builds one sentence out of three labels and two controls: *Adjust* (with a trailing space), a drop-down offering *negative* or *positive*, *kerning values by* (with a leading space), a number field, and *units*. In English it reads *Adjust negative kerning values by 10 units*. The catalog shows each fragment separately, with no hint that they form a sentence.

```text
en  "Adjust "               [negative|positive]  " kerning values by"      [10]  "units"
de  "Anpassung "            [negativer|positiver] " Kerning-Werte um"      [10]  "Einheiten"
es  "Ajustar los valores "  [negativos|positivos] " de kerning en"         [10]  "unidades"
fr  "Ajuster les valeurs "  [négatives|positives] " de crénage de"         [10]  "unités"
pl  "Dostosuj "             [ujemne|dodatnie]     " wartości kerningu o"   [10]  "jednostek"
```

The Spanish review notes record what happens when the fragments are translated one at a time: *Adjust* became *Ajustar*, and the assembled result read *Ajustar negativos los valores…*, with the adjective before the article. The fix moved *los valores* into the first fragment so that the drop-down's adjective follows its noun, and it inflected the drop-down entries for the masculine plural noun. The German moved further: it turned the command into the noun phrase *Anpassung negativer Kerning-Werte um …*, adjustment of negative kerning values by, so that the drop-down entries take the genitive ending *-er*. The fragments are no longer translations of their English counterparts; together they translate the sentence. That is the only way assembled text can work, and it is why the leading and trailing spaces are part of the contract.

The companion filter dialog shows German redistributing meaning between fragments. *Remove exceptions that differ from class pair by* [number] *units or less* became *Ausnahmen entfernen, deren Abweichung vom Klassenpaar höchstens* [number] *Einheiten beträgt*: *or less* moved forward as *höchstens*, at most, and the verb *beträgt* moved to the end, after the number. The German review notes point out that *höchstens* keeps the inclusive limit of *or less*, so the condition survives the move.

The Polish draft shows the limit of what fragments allow. *jednostek* is the genitive plural, correct after 5 and above (*o 5 jednostek*) but not after 2 to 4 (*o 2 jednostki*) or 1. A fixed unit label after a free number field cannot agree with the number, in Polish or in any language with count-dependent forms. The usual solutions are an abbreviation that does not inflect or a layout that puts the unit in a label before the field; both are decisions for the pending native review, not for the translation of one fragment.

Two smaller traps belong here. Code sometimes appends punctuation to a message, so a translator who adds a final period produces two; check the running interface before adding or removing one. And a string that looks complete may be a prefix: *Adjust* followed by a space is a fragment even though *Adjust* is a word.

## A contract for every placeholder

Each problem in this chapter disappears when the translator knows the message's contract. The writing guide's message-contracts page lists what that contract contains: a stable identity and source revision, the trigger, the purpose, and for each value whether it is user text, an identifier, an already localized label or a quantity, with its range, unit and empty-value behavior. It adds that a translator must not infer grammatical gender or case from one sample name.

The FontLab review could not always get a contract, and read the code instead. The German guide records, for example, that the preview options form one runtime sentence, *Im Glyphenfenster bevorzugt: einzeilige/mehrzeilige/automatische Vorschau*, and that the feminine adjective endings were needed in three messages of another context because a constructor replaces the form's default text at run time. No catalog shows that relationship. A reviewer found it in the source.

Tools check the mechanics and nothing else. vexy-localizzy's default Qt policy requires the exact multiplicity of `%1`, `%L1`, `%n` and `%Ln` in the target, lets numbered arguments move, and, when a catalog is checked with its printf policy, delegates C printf checking to GNU `msgfmt`. Part 6 describes how machine translation protects placeholders through parsing, instruction and repair ([606](../6-machine-translation/606-the-placeholder-protocol.md)). No check can confirm that *um* is the right preposition before a number of units, or that a drop-down's entries agree with the noun two fragments away. That is the translator's work, and it starts with asking what goes in the slot.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 3: variables, concatenated strings and problematic strings)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 7: string handling and UI controls)
- `data-fontlab-cpp/i18n-repo/fontlab_de.ts`, `fontlab_es.ts`, `fontlab_fr.ts` and `fontlab_pl.ts` in the fl10n repository
- [localization/ui-strings](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/ui-strings/), [localization/message-contracts](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/message-contracts/), [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/), [localization/de](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/de/), [localization/es](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/es/) and [localization/fr](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/fr/) in the vexy-fontlab-writing-styleguide repository
- [docs/quality.md](../8-toolkit/quality.md) in the vexy-localizzy repository
