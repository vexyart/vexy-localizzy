---
this_file: src_docs/md/7-process/702-continuous-localization.md
---

# 702. Continuous localization: the loop from source change to compiled catalog

A developer renames a menu command on Tuesday afternoon. In a waterfall project that change waits for the next localization kit, and by then it has three siblings, two of which contradict it. In a continuous project the change reaches the German catalog before the developer has closed the pull request, and the only question is whether it arrives reviewed or merely translated. This chapter describes the loop that carries a source change to a compiled catalog, the decisions that shape it, and the places where the loop is weaker than its diagrams suggest.

## From kits and freezes to a loop

The process Esselink described in 2000 was a sequence. Terminology came first, then software translation, then help and documentation, then engineering and testing of the software, then screen captures, then help engineering, desktop publishing and final quality assurance. Each step depended on the one before: help could not be finished until the software it referred to was translated and tested, and screen captures could not be taken until the localized build was stable. The project manager's main tool against that chain was the freeze. Esselink recommends freezing the software translation once linguistic testing is done, and freezing the user interface after the cosmetic test, because a late terminology change forces rework in every help file and manual that quotes the interface.

Jiménez-Crespo (2024) names this shape the waterfall model and sets it against agile and continuous workflows. In a waterfall, one stage begins when the previous one ends, and a problem found late is expensive because the developers have moved on. In an agile workflow, localization happens in sprints alongside development. Continuous localization is the subset of agile practice built on continuous integration and delivery: small updates are pushed several times a day, a translation management system pulls new content from the repository, matches it against translation memory, routes what is left to machine translation and people, and pushes the results back. His description of the process as "a never-ending job with recurring small updates" is the key change. There is no end state to freeze, only a stream of deltas to keep clean.

The two models solve the same problem differently. The waterfall controls change by stopping it. The loop controls change by making every change small, visible and checked. Neither removes the dependency Esselink described: a help topic that quotes a label still has to be updated when the label changes. The loop only makes the dependency cheaper to detect.

## The eight stages

The 2026 research corpus (research/05) reduces the continuous pipeline to eight stages, and the toolkit design maps each one to a command. The table combines both.

| Stage | What happens | What it produces |
|---|---|---|
| 1. Extract | Native tooling reads the source: `lupdate` for Qt, `xgettext` for gettext, an i18next extractor for web code | A fresh source catalog |
| 2. Diff | Compare the fresh catalog with the approved one | New, changed and removed messages |
| 3. Pseudo-localize | Build a pseudo-locale and take screenshots | Layout failures before translation |
| 4. Translate | Memories first, then an engine with glossary and context | Draft targets, marked unfinished |
| 5. Deterministic gate | Placeholder, tag, plural and length checks | Pass, or a blocking finding |
| 6. Selective judgment | Quality estimation or a model judge on a sample | Escalations to people |
| 7. Commit and pull request | Catalogs plus a machine-readable QA summary | A reviewable change |
| 8. Merge and build | `lrelease` or the equivalent compiler | Binary catalogs in the build |

Two rules from research/05 govern the whole table. Extract with the native tool, not by scraping built artifacts, because only the native tool knows which strings the code actually marks. And run the cheap stages before the expensive ones: a missing placeholder should fail in milliseconds, before any model is called. Chapter [704](704-the-qa-gate.md) describes stages 5 and 6; chapter [706](706-pseudo-localization-and-layout.md) describes stage 3.

Stage 2 is the one teams underestimate. Delta processing, sending only new and changed keys to translation, is what makes the loop affordable, and it depends entirely on how messages are identified across versions. If a context rename makes every message look new, the delta is the whole catalog. Part 3 covers identity in detail in [310. Identity and upgrade](../3-formats/310-identity-and-upgrade.md). For the loop, the practical rule is that identity must ignore line numbers and file locations, which change on every commit, and must treat a changed source text as a changed message even when its key survives.

## Principles, and where the sources disagree

Research/05 lists six design principles for the loop. Four of them hold up without argument: git is the source of truth for code, translations are scoped to pull requests, only deltas are processed, and cheap validation runs first. Two deserve a closer look.

**Human review as the exception.** The research synthesis says automation and rule-based checks should handle more than ninety percent of strings, leaving people roughly five to ten percent where judgment matters. The FontLab practice in 2026 went the other way for its first releases. The German catalog of 10,587 messages was reviewed directly, every entry, and the review produced 2,172 net German changes against the incoming translations. That is about one message in five. A pipeline that had sent only a residual to review would have shipped most of those defects. The two positions are not contradictory once scope is added: the research figure describes a mature loop feeding small deltas into catalogs that have already been reviewed, while the FontLab figure describes the first professional review of a catalog that had never had one. A new language, or a language whose existing catalog nobody has read, needs a full pass before the residual model is safe.

**Replacing string freezes with gates.** Research/05 recommends replacing hard freezes with automated pull-request gates that block a release branch when translations are missing or checks fail. Esselink's freeze existed for a reason the gate does not address: a changed label invalidates every document that quotes it. A gate can confirm that the new label is translated; it cannot tell you that the tutorial on page 40 still says the old one. Keep the gate, and keep a short freeze on the interface labels that documentation quotes, or add a check that compares quoted labels in help against the catalog. The FontLab writing guide lists exactly that check: "labels quoted in the Help Panel and the manual that do not match the catalog".

A smaller disagreement concerns where translations live. Research/05 names the translation management system as the source of truth for translations and git as the source of truth for code, then advises keeping a git-stored canonical copy even behind a TMS or an over-the-air delivery network, to avoid lock-in. The toolkit design settles it the second way: the canonical catalog stays in git and any TMS is a sync target. Chapter [703](703-branches-and-merges.md) follows that choice.

## A worked loop: a Qt catalog upgrade

The FontLab localization in September 2026 shows the loop at the size of one release. The application's developers ran `lupdate`, which produced fresh `.ts` files containing the messages the code now held. The reviewed translations lived in separate approved catalogs. The upgrade step ported one onto the other. The project wrapper calls `localizzy upgrade`; written out directly, with illustrative paths, the call has this shape:

```sh
localizzy upgrade fresh/fontlab_de.ts approved/fontlab_de.ts \
    --out new/fontlab_de.ts --retired retired/fontlab_de.ts \
    --direct-memory de-project.tmx --glossary-memory de-core.tmx \
    --target de --endpoint URL --model MODEL
```

The command writes three files: the new catalog, which keeps the fresh file's bytes and re-renders only the messages that changed; a retired catalog holding the approved messages that nothing used; and a JSON report with exactly one outcome per fresh message. It refuses to write anything unless every fresh message is classified and every approved message is either consumed or retired. Messages that no approved translation or memory covers go to the engine and stay unfinished. With `--no-engine` instead, they stay empty and the command exits with status 1, which makes the gap visible in CI rather than filling it with guesses. The upgrade tiers are described in [310](../3-formats/310-identity-and-upgrade.md).

The September 2026 upgrade run on the German, Spanish and French catalogs gave these results per language:

| Outcome | Messages |
|---|---|
| Exact ports from the approved catalog | 10,448 |
| Fuzzy ports after source typo fixes | 11 |
| Memory hits | 7 to 10 |
| Engine translations | 5 to 8 |
| Retired to a separate file | 128 |
| Finished messages compiled by `lrelease` | 10,474 |

Every fuzzy port, memory hit and engine translation was then reviewed by hand before the messages were marked finished. That is the loop working as intended: more than ninety-nine percent of the catalog carried over untouched, and human attention went to the few dozen messages that were new or changed. The contrast with the first full review is the point of the previous section. The residual model only became safe after the catalog underneath it had been read.

Two details of the build stage matter for anyone copying this. The specification commits the `.ts` catalogs and ignores the compiled `.qm` files, because the binary form is a build artifact and diffs of it are meaningless. And `lrelease` runs in the packaging job, not in every developer build, so the compile check sits where release decisions are made.

## When the loop is too much

Research/05 closes with a warning that belongs at the top of any process chapter: a one-language utility needs none of this machinery, while a multi-locale product maintained over years depends on all of it. Between those poles, build the stages in the order of their payoff. Extraction with native tools and a deterministic gate come first, because they prevent broken builds. Delta processing and identity-aware upgrades come next, because they keep review effort proportional to change. Pseudo-localization in CI, sampled model judgment and TMS integration come last, when the volume justifies them.

Uren, Howard and Perinotti (1993) observed that last-minute changes were hard to handle when the parties to localization were far apart, and that distance was measured in courier days. The loop removes the courier. It does not remove the need for someone to decide, for each change, whether it has been reviewed or only translated. The catalog states, the report and the ledgers described in the rest of this part exist to keep that distinction on the record.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 5: linguistic testing as a freeze point; chapter 14: scheduling, dependencies, sequence)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 3: the localization process, waterfall versus continuous workflows)
- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (chapter 8: time and accuracy)
- [docs/ci.md](../8-toolkit/ci.md) in the vexy-localizzy repository
- [docs/upgrade.md](../8-toolkit/upgrade.md) in the vexy-localizzy repository
- The work log and changelog of the FontLab localization project (the September 2026 upgrade run)
- The README of the review ledger directory of the FontLab localization project
- [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/) in the vexy-fontlab-writing-styleguide repository
