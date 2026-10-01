---
this_file: src_docs/md/6-machine-translation/601-what-this-part-knows.md
---

# 601. What this part knows

In 2000, Bert Esselink described a machine translation setup that any localization engineer in 2026 would recognize: search the translation memory first, send what is left to the machine, have a translator post-edit the result, and store the corrected segment back in the memory. He also warned that machine translation paid off only for carefully controlled input and a system loaded with the right terminology. Twenty-six years later the machine is a large language model that can read a comment, a sibling string and a screenshot, and the warning still holds in a new form. The model is fluent enough to hide its mistakes, and the work has moved from customizing an engine to controlling what the engine is given and checking what it returns.

This part is about that work. It treats a model as one component of a localization pipeline, not as a translator that happens to be fast.

## What the part covers

The part follows a string from the moment it needs a translation to the moment a person approves it.

- **[602](602-from-rules-to-models.md)** traces machine translation from rule-based systems through statistical and neural engines to large language models, and says what each generation could and could not see of a software string.
- **[603](603-context-engineering.md)** lists the context a model needs to translate a label correctly: context name, comment, placeholder inventory, siblings, glossary, style sheet, length budget, screenshot.
- **[604](604-memory-first-pipelines.md)** puts the model last. A catalog is filled from kept translations and memories before any engine is asked, and whatever nothing can fill stays visibly pending.
- **[605](605-glossary-enforcement.md)** shows how to send only the terms a batch needs, and how to check afterwards, in every inflected form, that they arrived.
- **[606](606-the-placeholder-protocol.md)** covers the one check that can break a build: parse the placeholders, instruct the model, validate the result by count, and repair or refuse.
- **[607](607-routing-batching-and-cost.md)** deals with which model gets which string, how batches are sized, what a cache must key on, and what the published cost figures are worth.
- **[608](608-quality-estimation-and-judges.md)** examines automatic quality scores, language-model judges and MQM error weights, and the disagreement over whether a score may approve anything.
- **[609](609-post-editing.md)** describes what a human does with a draft and how the recurring edits between draft and final text become glossary entries and rules.
- **[610](610-data-terms-and-trust.md)** closes with what leaves the building when a string is sent to a provider, and how to make a machine-assisted catalog reproducible and auditable.

## Why it matters

A model that translates ten thousand interface strings overnight changes the economics of a release, and it changes where errors come from. A human translator who does not understand "Open" asks a question. A model picks a meaning and moves on, and the German reads well. Jiménez-Crespo (2024) calls neural output deceptively fluent: the distortion is harder to see because the sentence is well formed. Every chapter here is a response to that one property. Context reduces the guessing, memories remove the guessing for strings already decided, glossaries and placeholders are checked mechanically, scores point reviewers at risk, and people approve.

The part also records where the sources disagree. The 2026 research corpus recommends routing strings to model tiers; the vexy-localizzy toolkit tries an ordered list of models instead. The original toolkit specification lets a judge's score of 80 make a string eligible for approval; the FontLab writing guide says quality estimation may triage and may not approve. These disagreements are stated where they arise, with the reasoning on each side.

## How the chapters connect

Chapters 603 to 607 describe one pipeline in the order a string passes through it. Chapter 608 describes the automatic checks at its end, and chapter 609 the human work that follows them. Chapter 610 applies to all of it. The part leans on earlier parts for material it does not repeat: memories and ledgers are in [405](../4-terminology/405-core-and-project-memories.md) and [410](../4-terminology/410-ledgers-and-decisions.md), plurals and agreement in [505](../5-interface/505-plurals-in-practice.md) and [506](../5-interface/506-placeholders-and-agreement.md), and catalog upgrades in [310](../3-formats/310-identity-and-upgrade.md). The quality gate and MQM sign-off that consume this part's output are in [704](../7-process/704-the-qa-gate.md) and [705](../7-process/705-lqa-and-mqm.md).

The worked examples come from the FontLab localization. Its German, Spanish and French catalogs were upgraded mostly by porting approved translations onto the new catalog, with a handful of engine translations per language. Its first Polish catalog was drafted by a single model, claude-opus-5-5, with a core memory, a seed glossary and a style sheet, then corrected by the founder's terminology guide. Both are ordinary cases, and both show where a model helps and where it needs watching.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 11: translation technology, machine translation)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 12: machine translation and large language models)
- [docs/quality.md](../8-toolkit/quality.md) and [docs/design/architecture.md](../8-toolkit/design/architecture.md) in the vexy-localizzy repository
- The work log and changelog of the FontLab localization project (the Polish localization and the founder's update of 29 September 2026)
- [localization/memories](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/memories/) in the vexy-fontlab-writing-styleguide repository
- `README.md` and [docs/memories.md](../8-toolkit/memories.md) in the vexy-localizzy repository
