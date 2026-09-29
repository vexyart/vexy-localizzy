---
this_file: src_docs/md/5-interface/508-source-text-as-evidence.md
---

# 508. Source text as evidence: wrong strings, source defects and translating the behavior

Translators are trained to be faithful to the source. In interface work, the source is sometimes wrong. A button labeled *Remove stroke* deletes the whole text element. A field labeled *Y position* shows the X coordinate. A tooltip copied from another dialog describes a different tool. A faithful translation of such a string carries the error into every language, and a careful translator, who has read the code or used the control, knows it.

This chapter is about what to do then. The answer is neither to translate the error nor to fix it silently, but to translate the behavior as far as the evidence reaches, record the source defect, and keep the two linked so that the eventual fix does not leave the translation wrong in a new way.

## The English text is the key

In Qt, and in every catalog format keyed by source text, the English string is not only content but identity. A translation is found by its context, its source text and its disambiguation comment. The FontLab interface-strings page spells out the consequence: rewording a shipped English string, even to fix a typo, orphans its translation in every catalog. The old entry becomes *vanished* and a new unfinished entry appears, to be translated again ([310](../3-formats/310-identity-and-upgrade.md)).

This gives source edits a cost, and the older literature treats that cost as a reason for restraint. Dr International (2002) tells writers to change content in an upgrade only when the reason is more than cosmetic, because every change destroys exact matches in the translation memory. The same principle protects catalogs: a source edit needs a behavioral reason.

A wrong string has one. But the source may not change for months, and the translator is translating now. The FontLab principles settle the order: when the English is wrong but the control's behavior is clear, translate the behavior and file the source defect; do not wait for the English to change.

## How wrong source strings look

Few projects measure how often their English is wrong. The FontLab review of 2026 did, as a side effect. While writing the German, Spanish and French guides, reviewers compared English strings and help articles with the C++ code, and recorded every place where they believed the application, not the translation, was wrong. The claims were then extracted and each was checked against the source by reading code; nothing was compiled or run.

| Stage | Count |
|---|---|
| Raw claims from the three guides | 223 |
| Candidates after merging and dropping pure terminology remarks | 126 |
| Confirmed | 83 |
| Partially confirmed | 33 |
| Refuted | 10 |

Of the 116 confirmed or partially confirmed candidates, 4 were rated major, 68 minor and 44 trivial. They fall into a few recurring shapes:

- **Labels that describe another operation.** *Remove stroke* in the text bar deletes the whole text element. A button labeled *Apply* in the source panel reverts unapplied edits.
- **Tooltips copied from elsewhere.** Two buttons in the collection dialog carried tooltips about audit tests; a thickness field said *Y coordinate*.
- **Swapped pairs.** *X position* and *Y position* attached to the wrong fields; an On and Off description written backwards.
- **Numbers that disagree with the code.** A color-flag button labeled with a step of one while one of its code paths always steps by ten; a help article that gave a limit of 75 where the code allows 150.
- **Unfinished strings.** A tooltip that stops mid-phrase: *Variation selector (1-16 for*.

Ten candidates were refuted. That number matters as much as the others: a translator's suspicion is a hypothesis, and about one claim in thirteen did not survive a reading of the code.

## Translating the behavior

Translating the behavior means the translation describes what the control does. It does not mean the translator decides what the control should do. The FontLab guides show where the line runs.

**Correct the label for its own message only.** In the French catalog, the correction for *Remove stroke* in the text bar was *Supprimer l'élément de texte*, delete the text element, backed by the handler that removes the active element. The correction was limited to that context; other *Remove stroke* strings keep their meaning. When a shared key serves two controls, a correction can be impossible: in the French notes, one inspector key labeled both a lock button and a genuine enlarge button, so correcting it for one would have made the other wrong. The translation stayed, and the defect went to the source review.

**Keep what cannot be verified.** The color-flag tooltip says *Increase color flag value* with a step of minus one. The German translation reads *Farbmarkenwert verringern*, decrease the color flag value, keeping the numbers exactly as given. The code has two paths, one stepping by one (ten with Shift), one always by ten; the German notes say the translation does not change the step sizes on suspicion. The verb was provably wrong and changed. The number was a discrepancy between code paths, and stayed a source question.

**Invent nothing.** For the unfinished tooltip *Variation selector (1-16 for*, the German and Spanish translations name the field, *Variationsselektor* and *Selector de variación*, and stop. The missing words and the true range are not in evidence; the French notes observe that the widget accepts 0 to 48, which is neither the English's 1 to 16 nor, according to the source review, the range the underlying library supports. A translation that completed the sentence would have added a claim nobody checked. The French notes describe the same decision, but on 29 September 2026 the French catalog read *Sélecteur de variante (1-16 pour*, reproducing the fragment, with the noun from a later term decision (issue 145); the Polish draft copies the fragment too. A decision made for one message needs a guard against the next batch.

**Let the founder's doubt be checked, not obeyed.** In issue 133 the founder questioned the German *Textelement entfernen* for *Remove stroke*: it sounded odd, please double-check. The check against the code confirmed that the button removes the text element, and the German stayed. A reviewer's authority settles terminology; it does not settle what a button does. The code does.

The evidence standard is the same throughout: a file and line number, a reason, and a statement of what was not checked. The German notes on the welcome tips, for example, say that menu paths were corrected from the menu definitions and that no visual check of the running application was claimed.

## Worked example: X and Y, before and after the fix

The interpolation dialog in FontLab has two fields for absolute position. In September 2026 the constructor gave the field that displays the X value the label *Y position*, and the Y field the label *X position*. The German, Spanish and French reviewers each translated by function: the field showing X was labeled *X-Position*, *Posición X*, *Position X*, even though its English source said *Y position*. The German guide records this as an exception for exactly two message IDs, not a general rule that X translates as Y, and the source review filed the swap as defect B-019, with the fix of swapping the two `tr()` calls.

The fix landed. By 29 September 2026 the dialog's source attached *X position* to the X field. From that moment, the behavior-based translations were wrong: each catalog now had *Y position* translated as *X-Position*. The update pulled from the application repository brought catalogs that matched the corrected source, and fl10n issue 146 records the decision in one line: the approved German and Spanish catalogs had X and Y swapped, the new files have them right, keep the new values. All four catalogs, including the Polish draft, now translate *X position* as X.

A behavior translation is therefore a debt with a trigger. It is correct only while the source defect exists, and it becomes a new defect the day the source is fixed. Three habits keep the debt from being forgotten. Record the exception in the ledger with the ID of the source defect it depends on. Limit it to the affected message IDs, so a later search finds exactly those. And when a source fix lands, search the ledgers for that defect ID before accepting the new catalog, as the X and Y case was handled.

The same review shows the opposite risk. The French correction for *Remove stroke* is in its ledger, dated 28 September 2026. On 29 September the French catalog in the application repository read *Supprimer le trait* again, the pre-correction text, while the German and Spanish kept their behavior-based renderings. A correction that exists only in a ledger is not a correction. The ledger chain is what lets someone find out which later step lost it ([410](../4-terminology/410-ledgers-and-decisions.md)).

## Read a catalog diff as evidence

Separate translation edits from XML formatting, source-location updates,
added messages and changed lookup keys. Compare each message by context,
source, disambiguation and numerus identity; compare each plural form's text
separately from indentation. A large diff need not contain many language edits.

Then separate recurring preferences from local choices and unresolved defects.
A repeated *hinzufügen* to *hinzu* change supports a compact-command rule.
The two separator jokes belong to their copy-text controls. One changed plural
form does not establish that the whole message is consistent, and an apparent
typo does not become approved spelling. Retain the original before/after record
and the reason for adopting, limiting or declining each pattern. Update the
canonical term memory and guides before regenerating portable tables and
phrase books; a new phrase book alone cannot teach a prose rule.

## Filing the defect

A source defect goes to its owner as a separate record, not as a comment inside the translation. The FontLab review keeps these under `data-fontlab-cpp/i18n/source-review/` in fl10n, each with a verdict, a severity, the file and line, and a suggested fix. The quality specification keeps the categories apart: a string that should never have been translatable is a source defect, a clipped label the translator could not see is a layout defect, and a mnemonic that collides with a runtime-inserted item is an engineering defect ([504](504-mnemonics-shortcuts-and-keys.md)). Esselink (2000) describes one more category that still applies: debugging messages that reach the string table are better left in English, so that developers can read a bug report from any locale, and the publisher should decide this rather than the translator.

Some source defects are invisible in English. The review found a menu handler that compared a translated label with the English word *unlink* to decide what to do, which made the command misbehave in every localized build. Only a translator or localization reviewer is likely to notice such code, because only they see the label change. Uren, Howard and Perinotti (1993) describe the related older problem of text that never reached the resource files, and suggest running the program with every message replaced by a row of x's so that English leftovers stand out. The FontLab string audit states the modern version plainly: a complete catalog is not evidence that the interface source is fully covered.

The translator's contribution is the observation and the evidence. The decision about the fix belongs to engineering, and the translation follows the fix, not the other way round.

## Sources

- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (section 4.5.1)
- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 3: problematic strings)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 9)
- `issues/133.md` and `issues/146.md` in the fl10n repository
- `data-fontlab-cpp/i18n/source-review/README.md` and `possible-bugs-2026-09-28.md` in the fl10n repository
- `data-fontlab-cpp/i18n/review/2026-09-28-fr-text-element-delete.json` in the fl10n repository
- `data-fontlab-cpp/i18n-repo/fontlab_de.ts`, `fontlab_es.ts`, `fontlab_fr.ts` and `fontlab_pl.ts` in the fl10n repository
- `Proteus/workspace2/dlgsetinterpolation.cpp` in the FontLab application source
- [localization/ui-strings](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/ui-strings/), [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/), [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/), [localization/de](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/de/) and [localization/fr](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/fr/) in the vexy-fontlab-writing-styleguide repository
