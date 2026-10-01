---
this_file: src_docs/md/7-process/710-release-provenance-and-roadmap.md
---

# 710. Release, provenance and the roadmap: shipping, auditing, and what to build next

A catalog that compiles is not a released translation. It is a file that a compiler accepted. Between that file and a user who reads the right word in the right dialog lie the delivery package, the installed build, the settings of a real machine, and the records that let someone answer, six months later, why a message says what it says. This last chapter covers the release check, the provenance a localization should leave behind, and the roadmap: what the FontLab practice and the vexy-localizzy toolkit built, what they deferred, and what a team starting now should build first.

## What shipping means

Esselink (2000) ended functional testing with a delivery test: install the localized product from the final deliverables on a localized system, following the end user's instructions, and compare the result with the original. His checklist is concrete. Do the localized and original deliverables contain the same number of files? Are all installed components in the right language? Does the uninstaller remove everything? Are there temporary or old files in the delivery? Do the file names and folder structure match the source? Have all escalated issues been resolved or reported again?

The FontLab writing guide restates the delivery test for a product that installs from a package rather than a set of disks. Repeat the relevant cases against the actual delivery package in its supported environment, because a development copy can find fonts, catalogs or help files that an installed copy lacks. Include installation, upgrade and removal where the brief requires them. Record which configurations were tested and which checks were deferred. And it states the limit of the paperwork: "A signed checklist establishes responsibility, not coverage beyond the evidence attached to it."

The FontLab review records draw the same line for catalogs. After recording that every catalog compiled with all messages finished, the review README adds that catalog creation or successful compilation alone does not establish completed translation or runtime availability. A release note for a localized build should therefore say three separate things: which messages are finished, which were reviewed and by what kind of review, and which runtime checks were run on which build.

| Claim | Evidence that supports it | Evidence that does not |
|---|---|---|
| Every message is translated | The native compiler reports all messages finished | A translation management system at 100 percent |
| The translation was reviewed | A ledger or sign-off naming the pass and reviewer | A finished state in the catalog |
| The build shows the translation | A runtime check on the delivered package | A successful compile |

## Provenance: what to keep

Provenance is the record of where each translated string came from and why it changed. Part 4 describes the ledger that holds reasons for terminology decisions in [410. Ledgers and decisions](../4-terminology/410-ledgers-and-decisions.md), and Part 3 describes edits that change only what they mean to change in [309. Byte-preserving edits](../3-formats/309-byte-preserving-edits.md). At release time the question is broader: can the team reconstruct, for any shipped message, its source revision, its origin and its history?

The FontLab and vexy-localizzy records keep five kinds of provenance:

1. **Change ledgers.** Every change to a shipped translation is recorded with the previous text, the new text and the reason, keyed by message id. The FontLab writing guide makes this a condition of a finished review.
2. **Origin sidecars.** Each catalog message has a record of where its current translation came from. When a record is refined, the prior origin is kept under `previous`. When the incoming data had no origin, the record says so explicitly with `previous: null` and `previous_absent: true`; no origin is invented.
3. **Upgrade reports.** Each upgrade writes a report with the path, SHA-256 hash and message count of the fresh, approved, new and retired catalogs, one outcome per fresh message, the memories used, and two invariants that must hold before anything is written.
4. **Translation records.** The vexy-localizzy translation cache keys each batch on every field that influenced it, including context, glossary and examples with their provenance, and records the requested model, the model the provider reported, and the request digests.
5. **Baselines.** The original incoming files and their hashes are kept, so every later state can be compared with the starting point.

An excerpt of the upgrade report's shape shows what a release audit can check without reading any translation:

```json
{
  "fresh":    {"path": "fresh/fontlab_de.ts",    "sha256": "…", "messages": 10484},
  "approved": {"path": "approved/fontlab_de.ts", "sha256": "…", "messages": 10474},
  "counts":   {"exact": 0, "machine": 0, "retired_active": 0, "unfilled": 0},
  "invariants": {
    "every_fresh_classified": true,
    "approved_consumed_or_retired": true
  }
}
```

The message totals are those of the German catalogs after the founder's update of 29 September 2026; the category counts are placeholders, and the field names are the report's own. An auditor who sees `unfilled` above zero knows the release is not complete, and one who sees a `machine` count knows how many messages need a reviewer's name beside them.

Provenance has one subtlety that the FontLab review met in practice. Some decisions of the founder's review returned a message to its original incoming text: *Collapse* and *Oblique* were two. A naive audit that compares the current text with the baseline would conclude that nothing happened. The FontLab verification script follows provenance chains by content, so a message that went from A to B and back to A still shows both steps and both reasons.

## Auditing a release

A release audit asks whether the records and the files agree. The verification of the 29 September update, recorded in the project's work log, is a compact example:

| Check | Result |
|---|---|
| Validator: active messages per catalog | 10,484, none unfinished, no errors |
| `lrelease`: finished messages per catalog | 10,484 |
| Scan of catalog and help for every retired term | Clean |
| Project test suite | Passes |
| Independent review of the scripted changes | Three defects found, fixed and verified again |

The last row is the one the other checks could not produce, and chapter [704](704-the-qa-gate.md) describes what it found. An audit that stops at the first four rows certifies that the files are consistent with each other. It does not certify that they are right.

After release, the audit continues in another form. Uren, Howard and Perinotti (1993) described "quiet releases" that fix a batch of problems, and the difficulty large companies had certifying fixes across divided responsibilities. The FontLab guide asks for a route from user reports to the owner who can fix them: keep the build, message identity and reproduction evidence with each report as it moves from support to source, translation or product. A report that says "the German label is wrong" without the message's context and the build is hard to act on; a guessed key or a back-translated label cannot identify the resource.

Esselink and the FontLab guide disagree on one point of reporting. Esselink advised against reporting a problem that cannot be reproduced on the same or another machine. The FontLab guide asks for intermittent failures to be reported even when they cannot yet be repeated, with the observed conditions, the attempts to reproduce them and the uncertainty marked. The later position reflects systems where timing, caches and network loading make some localization failures intermittent by nature: a language change that overlaps a delayed request is one example the guide gives.

## The roadmap, planned and built

The original toolkit specification planned four phases:

| Phase | Planned scope |
|---|---|
| P0 | Canonical model, TS and `.ui` parsing, a localizability scan, extraction and conversion with round-trip tests |
| P1 | Translation with context, placeholder protocol and delta processing; deterministic QA; pseudo-localization |
| P2 | A review tool, estimation and judge layers, a golden-set benchmark, the CI pipeline |
| P3 | Deferred: assisted source instrumentation, TMS integration, automated model re-benchmarking |

What was built by the end of September 2026 differs from the plan in structure more than in scope. The specification put everything in one package. The work of September 2026 split it into three layers: [abersetz](https://code.twardoch.com/abersetz/) as the translation engine, vexy-localizzy as the localization software (memories, memory-aware translation, the ten-tier TS upgrade, byte-preserving TS edits, deterministic QA and the browser reviewer), and a project layer that knows FontLab's catalogs, languages and memories. The review tool changed shape too. The specification planned to grow it from a prototype single-page application; the shipped reviewer is a packaged browser application with a filesystem store, revision checks and an append-only journal. Its design notes record a browser verification against the design concept at desktop, laptop and phone sizes, and state that this interface acceptance does not imply the rest of the planned pipeline is complete.

The work log is equally direct about what remained open. On 28 September 2026 it listed the Spanish direct review from message 7,200 onwards, Spanish and French help, and 37 further catalogs as pending. The entry for the Polish localization named a native editorial pass as the next step for Polish, with 59 units of the Polish core memory still proposed rather than approved. A roadmap that lists its own gaps is more useful than one that lists only its milestones.

## What to build first

Research/05 closes with a staged rollout for a team starting from nothing, and its order agrees with the FontLab experience once scope is added. Adapted for a team that owns its catalogs in git:

1. **Extraction and a deterministic gate.** Native extraction, a parser-based check of placeholders, markup and plurals, and the native compiler in CI. These prevent broken builds.
2. **Identity-aware upgrades and ledgers.** Keep reviewed translations across source changes and record every change with its reason. These keep review effort proportional to change.
3. **A full review of every entry in each existing language.** Before trusting a residual model, find out what the catalog actually contains. For FontLab the German pass changed about one message in five.
4. **A review surface with states and reasons.** Drafts that are not approvals, approvals that leave a trace, and conflicts that do not overwrite.
5. **Machine translation behind memories.** Engines for what no memory covers, with provenance recorded per batch.
6. **Pseudo-localization, sampled judgment and TMS integration**, when volume justifies them.

The research synthesis adds a short list of things not to do, and three of them are worth repeating at the end of a book about process: do not write your own format converter where a maintained one exists, do not gate quality on BLEU, and do not ship machine pretranslations without human review for any language that brings in more than about five percent of revenue. The FontLab practice adds a fourth. Do not call a translation done because a tool says so. Say which review it had, name who gave it, and keep the evidence where the next person will look.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 5: delivery testing, bug tracking)
- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (chapter 8: maintenance and repair of anomalies)
- [docs/ci.md](../8-toolkit/ci.md) and [docs/design/architecture.md](../8-toolkit/design/architecture.md) in the vexy-localizzy repository
- [docs/upgrade.md](../8-toolkit/upgrade.md), [docs/translation.md](../8-toolkit/translation.md), [docs/review.md](../8-toolkit/review.md) and [docs/design/review-fidelity.md](../8-toolkit/design/review-fidelity.md) in the vexy-localizzy repository
- The work log and changelog of the FontLab localization project, and its review ledger directory README
- [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/) and [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/) in the vexy-fontlab-writing-styleguide repository
