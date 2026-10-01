---
this_file: src_docs/md/7-process/707-review-tools-and-people.md
---

# 707. Review tools and people: what a reviewer needs on screen, and how reviewers rotate

A reviewer looking at the German word *Breite* in a spreadsheet cell cannot tell whether it is right. Beside the English "Width", in a context called `ActionAdjustMetrics`, with a note that the control changes a glyph's advance, the same reviewer can see that it is wrong. Most of the difference between a useful review and a ceremonial one is decided before the reviewer reads the first string: by what the screen shows, by what the tool lets the reviewer change, and by who reads after them. This chapter covers the review surface, the states a review moves a message through, and the people who take turns at it.

## What belongs on the screen

Esselink (2000) insisted that linguistic review happen in the running application, because dialogs shown in a resource editor are not the dialogs users see. Dynamic dialogs show one set of options in the editor and several in the product, and a word such as *copy* can be translated as a noun in the resource file and used as a verb at runtime. Jiménez-Crespo (2024) describes the tools that grew out of that problem: visual, "in-context" localization tools that show each string in its final interface, so that expansion, hot-key collisions and concatenation become visible while translating. He also notes where they are missing. In video-game localization translators often work from spreadsheets without the game, and he quotes Bernal-Merino's description of the result as "an error-prone guesswork exercise".

The toolkit design lists what a reviewer needs for each message, and the vexy-localizzy browser reviewer implements most of it:

| On screen | Why the reviewer needs it |
|---|---|
| Context, source and disambiguating comment | Identity: which message this is |
| Developer notes and extracted comments | What the developer meant, including placeholder values |
| Every target form | Plurals and length variants are reviewed together, not one at a time |
| QA findings for this message | Structural problems before linguistic ones |
| Suggestions with provenance | What the memory holds, and where it came from |
| A rendered preview of the dialog | Width, wrapping and neighbors |

The vexy-localizzy design contract arranges these in three full-height panels: a searchable message list, a preview of the dialog rendered from the real Qt `.ui` file, and an editor with the target slots, quality checks, context and suggestions. Clicking rendered text selects the matching message. The preview updates as the reviewer types, and Original and Localized tabs switch between the two languages. A suggestion carries its provenance on screen, in the form "Memory · sample:1", so the reviewer knows whether a proposal comes from an approved memory or from an engine.

The preview has limits the reviewer should know. It renders standard Qt widgets and preserves their geometry, but custom application widgets may appear as generic placeholders, and it does not execute application code. It is a quick check for fit in designer-built dialogs. Review in the running application, with real data and real settings, remains a separate pass, described in Part 5 in [510. Review in the running application](../5-interface/510-review-in-the-running-app.md).

## States, reasons and conflicts

A review tool is also a state machine. What each button does to a message's state decides what the next person, and the build, can trust.

vexy-localizzy keeps two actions. **Save draft** stores the edit and leaves the message in `needs_review`. **Approve** sets it to `approved`. Both reject edits with structural QA failures, so a broken placeholder cannot be saved even as a draft. Approving a message without changing its text requires a nonblank reason, which is kept in the journal. When the catalog is exported to Qt TS, drafts are written as unfinished and approved text as finished; the canonical JSON keeps the finer distinction. An edit is sent as one small record:

```json
{
  "key": "<message key>",
  "revision": "sha256 of the catalog the reviewer loaded",
  "targets": {"scalar": "Otwórz plik"},
  "action": "approve",
  "reason": ""
}
```

The original toolkit specification, written earlier, had Save set the state to `translated` and made Approve the only route to `approved`. The implementation is stricter on one point: a saved draft is still `needs_review`, so "someone typed here" never looks like "someone checked this". The requirement of a reason for approving unchanged text closes a gap the specification left open. Without it, a reviewer could approve a whole list of untouched machine drafts with one keystroke each and leave no trace of whether anything was read.

Two reviewers on one catalog will eventually collide. Each save carries the revision the reviewer loaded, and the server checks it while holding a file lock. A stale revision is refused with a conflict rather than silently overwriting the other person's work, and the reviewer's draft is kept so it can be reconciled after reloading. The journal records each edit's intent with old and new hashes before the catalog is replaced, then a completion marker, so an interrupted save can be recognized on reopening. This is the same discipline chapter [703](703-branches-and-merges.md) asks of automated edits: change a message only while it is still the text you saw.

## Roles

Uren, Howard and Perinotti (1993) separated two roles that are still worth separating. The localizer combines technical and linguistic skill, manages the software through conversion and supervises the translator. The translator, a native speaker of the target language, translates text, alerts engineers to cultural problems, and "has to accept the terminology dictated by the software developer and the Localizer". The last clause reads differently in 2026. Terminology is still decided outside any one translator's session, but it is decided from evidence and recorded in a memory, and a translator who finds that an approved term does not work is expected to propose a correction, as Part 4 describes.

Esselink's testing chapter adds a rule that transfers directly to linguistic review: testing and fixing should never be done by the same person. A tester reports, an engineer fixes, and the tester verifies and closes; only testers open and close bugs. In review terms, the person who changes a translation should not be the only person who approves it.

Jiménez-Crespo lists the agents a modern process may involve: localization managers and engineers, translators, terminologists, reviewers and proofreaders, testers, and in-country reviewers. For the last, he cites Esselink's distinction between validation and editing: an in-country reviewer checks technical consistency, completeness and agreed terminology rather than rewriting style.

The FontLab writing guide turns this into assignment rules. Assign reviewers by language, product and subject knowledge. Define each pass's scope: a market reviewer checks audience suitability, an editor checks meaning and terminology, a proofreader checks final layout. None of them should ignore a meaning defect because it falls outside their pass; they record it and send it to the person who can resolve it. Keep the pre-edit version, distinguish a needed correction from a preferred synonym, and let the translator see the reasons for accepted edits.

## How reviewers rotate

Rotation means that a translation is read by more than one kind of reader before it ships, and that no reader's blind spot becomes the catalog's. The FontLab localization of 2026 shows a rotation with four kinds of reader.

1. **An engine drafts.** New or unmatched messages get machine translations, marked unfinished.
2. **A model reviews.** A script sends messages with the language's style sheet and glossary to a model, which returns candidate corrections. For French in September 2026, the full catalog went through this reviewer.
3. **A reviewer decides.** A saved candidate is not accepted work; each one needs a contextual decision. Accepted candidates are applied only through a second script that checks the live text still matches what the model saw, compares placeholders and punctuation against the English, and writes an exact ledger. In the French pass, 1,182 corrections were applied and 17 proposed expansions of the abbreviation PPM were rejected.
4. **The founder reads the result.** The founder's review and the update of 29 September 2026 are review remarks written as rules and examples: one meaning gets one translation, keep the compression of headline-style labels, do not add specificity. The update gives each correction as a context and source, then, per language, the current target followed by the target it should have.

A fifth reader appears when the corrections are applied by rule rather than one at a time. After the Polish terminology update of 29 September 2026, an independent review pass found a rule that doubled a word on a second run and a plural form the pattern had missed. Chapter [704](704-the-qa-gate.md) tells that story in full.

Research/05 proposes rotating models as well as people: track the human approval rate for each pair of locale and model, and replace the model when the rate stays below about seventy percent. The same logic applies to human reviewers without the number. If one reviewer's approvals keep being overturned by the next pass, the rotation has found something, either in the reviewer's brief or in the reviewer.

The rotation only works if each reader leaves evidence the next can use: the reason for each change, the source revision, and the unresolved questions. A reviewer who fixes a word and leaves no reason has made the next review harder, not easier. Part 4 describes the ledger that holds those reasons in [410. Ledgers and decisions](../4-terminology/410-ledgers-and-decisions.md).

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 5: linguistic testing in the running application, testing team setup, test management)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 3: localization technologies, agents in the localization process)
- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (chapter 8: roles and responsibilities)
- [docs/review.md](../8-toolkit/review.md), [docs/design/review.md](../8-toolkit/design/review.md) and [docs/design/review-fidelity.md](../8-toolkit/design/review-fidelity.md) in the vexy-localizzy repository
- [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/) and [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/) in the vexy-fontlab-writing-styleguide repository
- The founder's review remarks on the German, Spanish and French catalogs (September 2026), the founder's update of 29 September 2026, and the changelog and work log of the FontLab localization project
