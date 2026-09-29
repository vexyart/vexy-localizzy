---
this_file: src_docs/md/5-interface/502-headline-style.md
---

# 502. Headline style: keeping the compression of a compact source string

A good English interface label is already a compressed sentence. *If mask is active* has no article before *mask*. *Select same flag* does not say what gets selected. *Brush to contours* has no verb at all. The writer removed those words because the control had no room for them and because the reader, looking at the control, supplies them without effort. A translator who restores the missing words produces a correct sentence and a worse label: longer, slower to read, and often too wide for the control.

This chapter is about carrying that compression into the target language. It is the most visible single habit of a good interface translation, and the one that literal translation and machine drafts break most often.

## Why the source is short

Every book on software localization treats length as a constraint before it treats it as a style. Esselink (2000) tells translators to keep menu names and commands as short as possible and to "adopt a concise and clear translation style for software strings", because every extra character costs resizing work later. He also describes the extreme case: fixed layouts shared by all languages, where the translator must choose shorter wording or abbreviate, and must record each abbreviation so it is used consistently. Roturier (2015) finds the same need in mobile applications, where translation guidelines often supply official short forms for strings that must shrink.

What these sources describe as a constraint is also a register. English interface text has developed a telegraphic grammar of its own: noun phrases for commands (*Kerning pairs*), conditions without a verb (*if active*), conversions written as destinations (*Brush to contours*). Users of the language read it fluently. German, French and Spanish have the same resource in their newspaper headlines, signage and technical labels, where articles and the verb *to be* drop out without any loss of clarity. The FontLab review of 2026 called this *headline style* and made it a rule for compact target labels.

## Source style and target style are different jobs

The older literature seems to say the opposite, and the disagreement is worth stating. Uren, Howard and Perinotti (1993) advise the writer of the English source to avoid telegraphic style and not to omit prepositions or articles. Dr International (2002) repeats the advice for documentation: include the optional words, keep the articles, because omitted words invite misreading and mistranslation.

Both books address the author of the source, and for that author the advice holds. An English string with its articles and prepositions shows the translator the relationships between its words. A string such as *Record error* is ambiguous (is *record* a noun or a verb?), and Uren uses exactly this kind of example to show what terse messages cost the reader and the translator.

The FontLab principles reconcile the two positions by scope. The source keeps its syntactic cues so that translators can see what the words mean. The target compresses only where the control is compact, and only as far as the language allows without ambiguity. Explanatory prose in any language keeps its full grammar: a tooltip, a help paragraph and an error message are sentences and stay sentences. Headline style is a rule for labels, not for everything a catalog contains.

## Four ways a label compresses

The review ledgers of the German, French and Spanish FontLab catalogs record hundreds of compressions. Almost all of them are one of four moves.

**Drop the article.** *Wenn die Maskenebene aktiv ist* becomes *Wenn Maske aktiv*; French *Si le masque est actif* becomes *Si masque actif*; Spanish *Si la máscara está activa* becomes *Si máscara activa*. The English has no article, so the translation needs none.

**Drop the copula.** The same examples also lose *ist*, *est* and *está*. The founder's own German for this string keeps the verb, *wenn neue Dickte kleiner als aktuelle ist* (issue 133); the shipped catalog went one step further and dropped the final *ist*, which a comparison can spare only because the control frames it as a condition. The book shows the shipped form and records the deviation. The verb *to be* carries no information in a condition that the control already frames.

**Drop the conversion verb.** A command that turns one thing into another can name only the result. German *Pinsel in Konturen umwandeln* becomes *Pinsel zu Konturen*: the reader supplies *wird* (*Pinsel wird zu Konturen*) without noticing. The pattern covers a whole family of commands: *Strich zu Konturen*, *Zu Komponente*, *Schnittmenge aus Konturen* in place of *Schnittmenge der Konturen bilden*. The founder's remark in issue 133 described the reasoning: start from the full sentence, rewrite it as a becoming, then let the becoming fall away.

**Drop padding the English did not need.** Some English strings carry words only because they had room. *Select OCR languages to enable (currently: English and Russian)* was translated as *Verfügbare OCR-Sprachen auswählen*, choose the available OCR languages. The list contains only available languages, so *verfügbar* says nothing; the review made the German *OCR-Sprachen auswählen*, the French *Choisir les langues OCR*, the Spanish *Elegir idiomas OCR*. (The English has since been rewritten as a two-sentence description, and the German kept its compressed opening.) *Reset code editors font to default* became *Schrift der Code-Editoren zurücksetzen*, because resetting already means returning to the default.

| Source | Before review | After review |
|---|---|---|
| If mask is active | Wenn die Maskenebene aktiv ist | Wenn Maske aktiv |
| Select same flag | Glyphen mit gleicher Farbmarke auswählen | Gleiche Farbmarke wählen |
| Select same flag (es) | Seleccionar glifos con la misma marca | Seleccionar misma marca |
| Intersect contours | Schnittmenge der Konturen bilden | Schnittmenge aus Konturen |
| Echo text | Aktivem Text folgen | Text wiederholen |
| Echo text (fr) | Suivre le texte actif | Répéter le texte |

The last two rows show that compression and correction often arrive together. *Aktivem Text folgen* (follow the active text) was not only long, it described a different feature; the review replaced it with the shorter and more accurate *Text wiederholen* in all three languages.

## Worked example: a condition in an import dialog

The metrics import dialog offers a choice that applies only when the imported advance width is narrower than the current one. The English label is a fragment that the dialog completes:

```xml
<context>
    <name>FontLabUI.dlgimportmetrics</name>
    <message>
        <source>if new is narrower than current</source>
        <translation>wenn neue Dickte kleiner als aktuelle</translation>
    </message>
</context>
```

The German before review read *wenn die neue Dickte kleiner als die aktuelle ist*: two articles and a copula the English never had. The Spanish read *si el nuevo ancho es menor que el actual*. After review, the Spanish became *si nuevo ancho es menor que actual*, keeping *es* but dropping both articles.

Look at what the German kept. The English says *new* and *narrower*, and *narrower* carries the dimension: it can only mean width. German *kleiner* (smaller) does not carry it, so *Dickte* (advance width) has to appear as a noun or the condition could mean any size. This is not added detail in the sense of [503](503-no-added-detail.md): the translation moves information that the English put in the adjective into a noun, because German puts it there. Compression removes words the target does not need. It never removes the meaning a word carried.

The Spanish result also shows that languages compress differently. Spanish headline style tolerates a missing article more readily than a missing verb in a comparison, so the reviewer kept *es*. The rule is to compress as far as the target language compresses naturally in labels, not to match the English word count.

## Where compression stops

A few limits keep headline style from turning into cipher, and one check confirms the result.

**Ambiguity.** A verbless label must still be unambiguous on screen. German nouns formed from verbs (*Skalieren*, *Füllung*) can read as a command or as a property, and the principles require such labels to be checked in the running interface, where the surrounding controls decide the reading. A compressed Spanish or French condition with a lone adjective can lose its referent. When in doubt, keep one more word.

**Strict panels.** Some panels allow no growth at all. In the FontLab Measurements panel, every label had to be at most as long as the English. *Vertical UC straight* had been translated as *Versalstamm, vert. gerade*; after review it reads *UC vert. gerade*, keeping the English abbreviation *UC* for capitals. French went from *Vertical droit des capitales* to *Cap. vert. droit*, Spanish from *Asta vertical, mayús. rectas* to *May. vert. recto*. Here compression uses abbreviations the profession already reads (*UC*, *lc*, *cap.*, *bdc*, *may.*, *min.*), recorded in the core memory so they stay consistent, exactly as Esselink recommended for fixed layouts in 2000. The sources disagree slightly on how strict the rule is: the principles and the German and French ledgers say no label may exceed the English, while the Spanish ledger records the goal in its own words as labels as short as the original or nearly so (*tan cortas como el original o casi*). The principles allow one exception: a fixed professional term that is one character longer, such as German *Oberlänge* for *Ascender*, stays and the exception is recorded.

**Sentences.** A message that explains something is a sentence, even when its English is clipped. The metrics import dialog reports what a file contains: *Metrics file %1 contains metrics info for %2 glyphs, %3 of which exist in the current font. Metrics file contains %4 kerning pairs, %5 of which are new.* The German keeps full grammar, articles and relative clauses: *Die Metrikdatei %1 enthält Metrikdaten für %2 Glyphen, von denen %3 in der aktuellen Schrift vorhanden sind. Sie enthält %4 Kerning-Paare, davon %5 neue.* The second English sentence drops its article; the German replaces the repeated noun with a pronoun, *Sie enthält*, as ordinary German prose would. Compressing prose into label grammar makes it harder to read, not easier.

**Checking it.** Length is the one aspect of headline style a script can measure. The FontLab quality specification lists two automated checks: a length ratio far outside the language's expected range, and any target longer than its source in a panel with a length cap. Both produce findings to inspect, not verdicts: a German label twice as long as *Edit* may be the correct *Bearbeiten*. A reviewer looking at a flagged string asks three questions in order. Is there an article or copula the English did not have? Is there a verb the result could imply? Is there a word that repeats what the control already says? If all three answers are no, the label is as short as the language allows, and the problem, if the text still does not fit, belongs to layout ([510](510-review-in-the-running-app.md)).

Record the compressions that recur. A catalog with one hundred conditions of the form *if X is active* should render them identically, and the rendering belongs in the language guide and in the project memory ([405](../4-terminology/405-core-and-project-memories.md)) so the next catalog does not unlearn it.

## Sources

- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (section 4.4)
- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 3: space restrictions)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 9)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 4.2.2)
- `issues/133.md` in the fl10n repository
- `data-fontlab-cpp/i18n/review/2026-09-28-issue133-de.json`, `-es.json` and `-fr.json` in the fl10n repository
- `data-fontlab-cpp/i18n-repo/fontlab_de.ts`, `fontlab_es.ts` and `fontlab_fr.ts` in the fl10n repository
- [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/), [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/), [localization/de](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/de/), [localization/es](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/es/) and [localization/fr](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/fr/) in the vexy-fontlab-writing-styleguide repository
