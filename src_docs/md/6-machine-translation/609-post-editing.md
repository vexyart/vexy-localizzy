---
this_file: src_docs/md/6-machine-translation/609-post-editing.md
---

# 609. Post-editing: what a human does with a draft, and how the draft-to-final diff feeds the glossary

Jiménez-Crespo (2024) gives the shortest definition: post-editing is "the editing and correction of MT output by a translator", quoting Do Carmo and Moorkens. The definition hides two decisions that shape everything else. How much editing is the job? And what happens to the edits afterwards: do they fix one catalog, or do they change the pipeline so the next draft needs fewer of them?

This chapter treats both. It uses the FontLab French review and the first Polish catalog to show what post-editing looked like in 2026, and it ends with a case where published evidence and the product owner disagreed.

## How much editing

Roturier (2015) traces three levels of post-editing, each introduced to fix the ambiguity of the one before.

| Level | Introduced | Goal | Problem |
|---|---|---|---|
| Rapid | European Commission, 1980s | minimal corrections so readers can get the gist | two readers disagree about what is comprehensible |
| Minimal | industry, 1990s | publishable text with no accuracy errors and the fewest changes | editors disagree about which edits are necessary and which preferential |
| Full | TAUS and CNGL guidelines | correct spelling, grammar, punctuation and syntax, and text that reads well | poorly translated segments can take longer to repair than to rewrite |

Jiménez-Crespo adds the corresponding distinction by purpose: machine translation for *assimilation*, where a reader wants the gist of a page, and for *dissemination*, where the publisher shows the text permanently as its own. Interface strings are dissemination by definition. The FontLab writing guide draws the conclusion without hedging: declare the editing level before work starts; full post-editing for interface and help text, which ship and live for years; nothing lighter reaches a catalog.

The full level carries a trap of its own. The TAUS and CNGL guidance, as Roturier reports it, asks post-editors to use as much of the raw output as possible. The FontLab guide rejects any such quota: replace an unusable suggestion whenever rewriting gives a clearer, accurate result. Keeping machine wording is not a goal in itself.

## Read the source first

Neural and language-model output is fluent, and fluency is persuasive. Jiménez-Crespo calls the output deceptively fluent, which makes omissions and shifted meanings hard to spot, and he reports research by Guerberof-Arenas and Toral (2022) finding that post-edited translations were measurably less creative than translations written from scratch: working from a suggestion primes the translator toward it.

The FontLab guide turns those findings into working rules.

- **Compare against the source, not against fluency.** Read the English first, then the draft. A fluent draft hides omissions, changed conditions and invented specificity, such as *Kerningpaar* where the English said only "pair".
- **Then read the target alone** and in the assembled document or screen, because a string that is correct against its source can still be wrong beside its neighbours.
- **Rotate reviewers.** After long exposure to machine phrasing an editor stops seeing it.
- **Do not draft marketing from one suggestion.** A single proposal narrows what the writer considers. Draft prose by hand or from several candidates.
- **Do not trust edit distance as a measure of effort or quality.** It counts surface changes. A one-letter correction that reverses a condition is worth more than a rewritten sentence that meant the same thing.

These rules apply whether the post-editor is a freelance translator, a staff reviewer or the product's founder with a list of corrections.

## What the FontLab passes did

Two passes in September 2026 show the range of the work.

The French catalog already existed. A model reviewer read the whole catalog against the English with the French style sheet and glossary, and proposed corrections. 1,182 of them were applied, among them *glyphe composé*, *fonctionnalité*, *indice de glyphe*, *sélecteur de variante*, French typographic spaces and register fixes, and 17 proposals that expanded the abbreviation PPM were rejected. The model proposed; the ledger records what was accepted and what was refused. The tool that applied the accepted corrections only did so while the live source and translation still equalled what the reviewer had seen, and it listed stale corrections instead of forcing them. Each change went into a ledger with its before and after ([410](../4-terminology/410-ledgers-and-decisions.md)).

The Polish catalog was new. It was drafted by a model, passed every placeholder, markup, accelerator and plural check, and compiled with every message marked finished. The writing guide's Polish page nevertheless describes it as a draft awaiting a native editorial pass. Those two facts are not in tension. A finished flag in a Qt catalog is a state the build tool reads; it records nothing about whether a person has read the text. Treat any report of "fully finished" from a machine-assisted run as a statement about the file, not about the translation.

A day later the founder issued a Polish terminology guide, 50 English terms each with the old and the new Polish rendering, and it was applied across the catalog and the help files. The project's own records give two sizes for that pass: the work log says 663 catalog strings changed, the changelog says 643. Both agree on 48 Help Panel and welcome-tip entries. Whichever figure is right, it shows the scale of what a terminology decision does to a draft: a few dozen decisions, several hundred strings.

## Mine the diff

The edits between draft and final text are data. Most of them are one-off corrections, but some recur, and a recurring edit is a defect in the pipeline rather than in one string.

The idea is old. Roturier describes Allen's (2001) dictionary workflow for rule-based systems: translate, identify the problem terms, write dictionary entries, translate again. He also describes automated post-editing, fixing systematic errors with search-and-replace patterns and regular expressions when a dictionary entry cannot. Jiménez-Crespo describes interactive and adaptive systems that learn from a post-editor's corrections so the same fix is not needed twice.

With a memory-first pipeline, the equivalent is to move each recurring edit to where the next draft will see it:

- a term the post-editor keeps changing becomes a core-memory entry, so the engine receives it as a glossary hint ([605](605-glossary-enforcement.md));
- a style correction, such as headline compression or French spacing, becomes a line in the language's style sheet ([603](603-context-engineering.md));
- a mechanical fix across existing text becomes a replacement rule, tested on intended matches and on valid counterexamples, and run twice to prove it changes nothing the second time;
- every reviewed catalog feeds the project memory, so the next release asks the engine only about new strings ([604](604-memory-first-pipelines.md)).

The Polish terminology pass followed that route. The decisions went into the Polish core memory, where 51 units moved to approved status, the project memory was rebuilt from the corrected catalog, and the term table was regenerated. A later Polish run that draws on the updated core memory receives the approved renderings as glossary hints instead of choosing its own. The FontLab guide sets a standard of proof for the step: a recurring edit is not by itself sufficient evidence for a global rule. The independent check that caught a non-idempotent rule and a missed genitive plural in that same pass, described in 605, is what the standard looks like in practice.

## When evidence and the owner disagree

Post-editing sometimes surfaces a conflict that no metric resolves. Before the founder's update, the Polish core memory had been reviewed against nineteen Polish interface glossaries and the Polish editions of several typography books. On that evidence the review chose *kreska główna* for stem, *szerokość posuwu* for advance width, keeping it apart from geometric width, and *pchnięcie* for nudge, and recorded why.

The founder's guide replaced all three: *trzon*, *szerokość pola* and *holowanie*, with *superholowanie* for Power Nudge. It also introduced renderings chosen for the product's own voice, such as *Pełna krasa* for True Fill and *naddatek* for overshoot. The founder explained *naddatek* as an optical surplus and proposed the same principle for other languages when a term is uncertain.

Both positions are legitimate and they rest on different authority. Attestation shows what Polish professionals and localized competitors already say, which matters for a reader who knows those tools ([406](../4-terminology/406-evidence-and-attestation.md)). The product owner decides the product's voice and can choose a clearer or more native word where usage is split or poor. The FontLab guide's rule for disputes is that a vote does not replace checking the disputed meaning against the working product, and that each decision is recorded with its reason.

The resolution in this case was procedural, and it is the one to copy: the owner's decision became the approved term, the earlier evidence stayed on record beside it, and the style page for Polish now states both, so the next reviewer can see what was chosen, what it replaced and why. Post-editing ends there, not with a corrected file, but with a decision that the next draft will inherit.

## Sources

- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 5.5.1: dictionary customization and automated post-editing; section 5.6: types of post-editing, tools and analysis)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 12: post-editing, assimilation and dissemination, priming, interactive machine translation)
- `src_docs/md/localization/memories.md`, `quality.md` and `pl.md` in the vexy-fontlab-writing-styleguide repository
- `issues/133.md` and `issues/146.md` in the fl10n repository
- `WORK.md` and `CHANGELOG.md` in the fl10n repository (issues 145 and 146)
