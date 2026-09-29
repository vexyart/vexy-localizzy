---
this_file: src_docs/md/4-terminology/410-ledgers-and-decisions.md
---

# 410. Ledgers and decisions: recording every change with its reason so the next catalog cannot regress

A terminology decision that is not recorded will be unmade. Not by anyone who disagrees with it, but by the next translator who never heard of it, the next engine run that was not given it, or the next catalog merge that brings back an older file. The FontLab localization principles say it in one line: a decision that lives only in a chat message is not a decision. This chapter describes the record that makes a decision stick: the ledger, which logs every change to a shipped translation with the text before and after and the reason; how ledgers chain across reviews; how a decision is kept in agreement across the ledger, the core memory and the language guide; and how retired strings and replayable rules protect the next catalog.

## What a ledger is for

A ledger answers three questions about any string in a catalog: what did it say before, what does it say now, and why did it change. The FontLab principles make it a condition of finishing a review: every change to a shipped translation is recorded with the previous text, the new text and the reason, keyed by message id. Without that record, a reviewer who finds an odd translation cannot tell whether it is a mistake to fix or a decision to respect, and an automated upgrade cannot tell whether an old translation in a memory is still valid.

The older literature does not use the word, but it describes the need. Esselink (2000) assigns one person to maintain the project glossary and wants every new term or terminology change communicated to the publisher's reviewers throughout the project. Roturier (2015) recommends exporting translation memory metadata, including authors and dates, so that a memory can be maintained. A ledger is the same idea applied to each change rather than to each unit.

## Anatomy of a ledger entry

The German review of September 2026 wrote its ledgers as JSON files, one per area of the interface, under `data-fontlab-cpp/i18n/review/` in the `fl10n` repository. Each file states its scope and the batches it read, with a digest of each request, and then lists the changes:

```json
{
  "language": "de",
  "id": "FL-a0c27c69c3d3c9fc",
  "ordinal": 1174,
  "context": "DlgArtworkWarning",
  "source": "Scale to UPM, align to descender",
  "comment": "",
  "before": "Auf UPM skalieren, an Unterlänge ausrichten",
  "after": "Auf Gevierthöhe skalieren, an Unterlänge ausrichten",
  "why": "PasteUPM_Descender setzt die Zielhöhe auf die Kegelauflösung ..."
}
```

Every field has a job:

| Field | Job |
|---|---|
| `id`, `context`, `source`, `comment` | Identify the message, so the entry still resolves after the catalog is regenerated |
| `before` | The exact prior target; applying the change fails if the catalog no longer contains it |
| `after` | The exact new target |
| `why` | The reason, with its evidence: an issue number, a source function, an attestation |
| file-level `scope` and `inputs` | What was reviewed and from which inputs, so the review can be reproduced |

The `before` field is a guard as well as a record. The issue 146 corrections were applied to the catalogs with exact prior-target checks: a change applies only if the string still says what the reviewer saw. If someone else has changed it in the meantime, the change stops rather than overwriting their work.

Two practical notes from the same data. The German ledgers name the reason field `why` in some files and `reason` in others; pick one name and enforce it, because a tool that looks for one misses the other. And the issue 146 ledger groups its 746 entries into three lists (35 western corrections, 663 Polish catalog changes, 48 help changes) without a reason per entry, because every entry in it has the same reason: the founder's instructions in issue 146. A per-entry reason is needed when the reasons differ; a file-level reason is enough when they do not, provided the file names the issue.

## Decisions chain

A string can change several times, and each change can be right in its own moment. The ledgers keep the chain. The German label *Descender to UPM* in the paste preferences shows how:

| Step | Translation | Recorded reason |
|---|---|---|
| Original catalog | *Unterlänge bis UPM* | |
| German consistency review | *Geviert ab Unterlänge* | The code sets the target height to one em measured from the descender, which is not the coordinate range from descender to UPM; the ledger names the two functions it read |
| Review of issue 133 | *Unterlänge bis Gevierthöhe* | The founder: the label names a distance from one line to the other |
| Build pulled for issue 146 | message retired; new source *UPM height from descender* translated as *Gevierthöhe ab Unterlänge* | The English source itself was reworded in the product |

Read without the ledgers, the final German looks like a reversal of the issue 133 decision. Read with them, it is the consequence of a new English source: the message that the founder's rule applied to no longer exists, and the retired catalog keeps it. The FontLab principles describe this property: provenance follows the chain of ledgers by content, so a decision that returns a string to an earlier form is still traceable.

The same mechanism records supersession of a term rather than a string. Issue 132 chose *Kegelauflösung* for UPM in German; issue 133 replaced it with *Geviertauflösung*. The review directory's README states that the explicit instructions of issue 133 take priority over older glossary entries and names this case, so that nobody restores the older term from an older ledger.

## One decision, three records that must agree

A terminology decision lives in three places, each for a different reader:

- **the ledger**, for the exact strings that changed;
- **the core memory**, for every future translation of the term, by person or engine;
- **the language guide**, for the reasoning behind the less obvious choices.

The FontLab principles say that a review is not complete until all three agree. The Polish core memory shows one way to keep the memory in step: each unit changed in issue 146 carries a translator's note of the form *Przegląd 2026-09-29 (issue 146): decyzja założyciela, poprzednio „…”*, "review of 29 September 2026, issue 146: founder's decision, previously …", so the prior term travels with the new one into every export.

Guides drift more easily, because they are prose. Two examples from the FontLab guides as they stood at the end of September 2026:

- The German guide's list of decisions and the German core memory say *Power-Schub* for Power Nudge, following issue 133. A longer section further down the same guide still explains the name as *Power-Verschiebung*, from an earlier review.
- The principles page still gives *Descender to UPM* as *Unterlänge bis Gevierthöhe*, a correct record of the issue 133 rule for a source string that the product has since retired.

Neither is a catalog error; the strings are right. Both are the kind of stale reasoning that misleads the next reviewer, and both are found the same way: search the guides for every rejected form named in the core memory notes and the ledgers.

The catalogs drift too. A concept search for *Power Brush* in the German catalog in September 2026 finds *Power-Pinsel* in two contexts and the English *Power Brush* in a third, the list of element types. An earlier German ledger records the reason for *Power-Pinsel*: it is the established product term, consistent with *Power-Strich* and *Power-Hilfslinien*. Whether the third string is a deliberate exception or a missed one is exactly the question a ledger entry should answer, and the absence of an entry is the signal to ask.

## Retired strings and the next catalog

When a new build regenerates the catalog, some messages disappear. They are not deleted from the record. The upgrade that brought in the issue 146 build wrote 63 messages per language to a retired catalog under `data-fontlab-cpp/i18n/retired/`. A reviewed translation is never lost because its source changed; if the source returns, the translation is still there to compare.

Retired terms need the opposite treatment. After a terminology change, the old term must not come back through any door: a project memory built from an older catalog, a machine draft primed with an older glossary, a help file translated before the change. The issue 146 verification included a retired-term scan of the catalogs and help, which came back clean. The FontLab memory guidance states the general rule: after a decision changes, regenerate the exports and identify the translations that used the superseded form.

## Rules that can be replayed

A large terminology change is applied by a program, and that program is part of the record. Issue 146 was applied by a script with three modes: report, apply and ledger. Its first run contained a rule that was not idempotent and a stem pattern that missed the genitive plural ([chapter 408](408-word-formation-and-derivation.md)). An independent review pass caught both, the fix was applied, and the ledger was extended with the repaired strings.

Three properties make such a program safe to run again:

1. **Idempotence.** Running the rules on their own output changes nothing.
2. **Guards.** Every change checks the exact prior text and refuses to apply otherwise.
3. **A ledger as output.** The program writes what it changed, so the review reads the ledger rather than diffing the catalog by eye.

## A worked example: making a decision stick

A reviewer changes Polish *pchnięcie* to *holowanie* for *Nudge*. To make it stick:

1. **Core memory.** Update the unit: target *holowanie*, status approved, note naming the issue and the previous form.
2. **Catalog and help.** Apply the change by message with prior-text guards, including derived forms such as *superholowanie* for Power Nudge.
3. **Ledger.** Write every changed string with context, source, before and after, under the issue.
4. **Guide.** Update the language guide's list of decisions, and search its prose for the old word.
5. **Project memory.** Rebuild it from the corrected catalog.
6. **Scan.** Search catalog, help and memories for *pchnięcie*, the variant *popychanie* that one tooltip used, and their inflected forms, and confirm that nothing but the retired catalog and the ledger's `before` fields still contains it.

The next time a catalog is upgraded, the project memory supplies the new strings, the core memory supplies the term to the engine for anything new, and the old word has no way back in.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 12: terminology reference materials)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 5.3: translation memory)
- `data-fontlab-cpp/i18n/review/README.md`, `2026-09-28-de-consistency.json`, `2026-09-28-issue133-de.json`, `2026-09-28-de-properties-tools.json` and `2026-09-29-issue-146.json` in the fl10n repository
- `data-fontlab-cpp/i18n/fontlab_de.ts` and `data-fontlab-cpp/i18n/retired/` in the fl10n repository
- `CHANGELOG.md`, `issues/133.md` and `issues/146.md` in the fl10n repository
- [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/), [localization/memories](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/memories/), [localization/de](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/de/) and `localization/tm/pl-core.tmx` in the vexy-fontlab-writing-styleguide repository
