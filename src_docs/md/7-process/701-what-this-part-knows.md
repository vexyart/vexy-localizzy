---
this_file: src_docs/md/7-process/701-what-this-part-knows.md
---

# 701. What this part knows

In September 2026 the German catalog of the FontLab interface, 10,587 messages, was reviewed entry by entry, and 2,172 of its messages changed. The catalog had compiled cleanly before the review and compiled cleanly after it. Nothing in the build could tell the two versions apart. Everything that could, the reasons for each change, the passes that were run, the names of the people who signed, lived outside the catalog, in the process around it. This part is about that process.

## What the part covers

Parts 1 to 6 dealt with what a string is, how code prepares it, which files carry it, how its terms are chosen, how its wording is judged and how machines draft it. This part deals with the flow that joins those pieces: how a source change reaches a compiled catalog, how that catalog is checked, reviewed and shipped, and what records it leaves. It is written for the localization engineer who builds the pipeline, the project manager who scopes and schedules it, and the reviewer who has to sign it off, because all three work on the same catalogs at the same time.

The part draws on two eras. Esselink's *A Practical Guide to Localization* (2000), Dr International's *Developing International Software* (2002) and the 1993 introduction by Uren, Howard and Perinotti describe localization as a project with kits, freezes, test cycles and vendors. The 2026 research corpus and the fl10n specification describe it as a continuous loop in a repository, with deterministic gates and language models. Much of the older advice survives the change of shape, and some of it does not. Where the sources disagree, the chapters say so.

## How the chapters connect

The chapters follow a translation from the moment its source changes to the moment someone asks, months later, why it says what it says.

- **[702](702-continuous-localization.md)** describes the loop: extract, diff, pseudo-localize, translate, check, review, merge and build. It sets the waterfall against continuous delivery and shows one real catalog upgrade.
- **[703](703-branches-and-merges.md)** keeps git the source of truth when several writers touch the same catalogs, and follows one message through two repositories.
- **[704](704-the-qa-gate.md)** arranges the checks in layers: deterministic checks that block, estimation and judges that escalate, and a residual for people.
- **[705](705-lqa-and-mqm.md)** gives linguistic review a specification: MQM error families, severities and their weights, thresholds and sign-off.
- **[706](706-pseudo-localization-and-layout.md)** catches breakage before any translator is paid, and marks the limits of what a pseudo-locale proves.
- **[707](707-review-tools-and-people.md)** describes what a reviewer needs on screen, how review states and conflicts work, and how different readers take turns.
- **[708](708-vendors-tms-and-projects.md)** covers who does the work, which translation management system carries it, and how a project is scoped and priced.
- **[709](709-help-docs-and-media.md)** extends the process to help, documentation, screenshots and media, which quote the interface and break when it changes.
- **[710](710-release-provenance-and-roadmap.md)** ends with the release check, the provenance a localization should keep, and a roadmap for teams starting now.

## Three ideas that recur

**Order the work by cost.** Cheap checks run before expensive ones, and people see what machines cannot settle. Chapters 702, 704 and 706 apply this at different stages.

**A state is a claim, and claims need evidence.** "Finished" in a catalog, "100 percent" in a translation management system and "passed" in CI each mean something narrower than "done". Chapters 705, 707 and 710 separate what each state proves from what it does not.

**Keep the reason with the change.** A ledger of previous text, new text and reason, keyed by message, turns review into something the next reviewer can build on. It also lets a correction survive the next upgrade. Chapters 703, 707 and 710 depend on it, and Part 4 describes it in [410](../4-terminology/410-ledgers-and-decisions.md).

## How much of this you need

Research/05 draws the boundary that every reader should apply to this part: a one-language utility needs none of this machinery, and a product maintained in many languages over many years depends on all of it. Most teams sit in between. Chapter 710 ends with an order for building the pieces. The FontLab records argue for one step the research synthesis leaves out: before trusting any automated residual, review every entry of each existing catalog once.

FontLab and the vexy-localizzy toolkit appear throughout as worked examples, because their records are open and exact. They are one way of doing the work, recorded as it happened in 2026, not the only way.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002
- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993
- `research/05-format-conversion-cicd-and-continuous-localization.md` in the fl10n repository (section 5.7)
- `data-fontlab-cpp/i18n/review/README.md` in the fl10n repository
