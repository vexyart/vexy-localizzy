---
this_file: src_docs/md/6-machine-translation/604-memory-first-pipelines.md
---

# 604. Memory-first pipelines: kept, memory, engine, pending

The cheapest, fastest and most consistent translation of a string is the one somebody already approved. A pipeline that sends every string to a model pays for work that was done, invites the model to translate a reviewed label differently, and hands reviewers thousands of strings to reread. A memory-first pipeline asks the model only about what nothing else can answer, and it says plainly which strings nothing could answer.

This chapter describes the order, what counts as a match at each step, and why an honest "pending" is a better result than a guessed translation.

## An old order with a new engine

The order is not new. Esselink (2000) described the typical setup of his day: the tool searches the translation memory for the sentence; if there is no match or fuzzy match, the translator asks the machine translation system, edits the result and stores it in the memory. In batch mode the whole text is pre-translated against the memory first and only the remaining segments go to the engine, whose output a human post-edits and confirms segment by segment. Jiménez-Crespo (2024) describes the same arrangement as current practice in MT-assisted translation memory workflows: a localizer is offered a memory match or, when there is none, a machine proposal, and rarely translates from scratch.

What changed is the engine at the end of the chain and the amount of context it can use. What did not change is the reasoning: reviewed human work outranks any machine proposal, and every confirmed translation should flow back into the memory so the next run asks the engine less.

## Four outcomes

vexy-localizzy's `translate` command makes the order explicit. Each eligible message ends in exactly one of four outcomes, decided in this order:

| Outcome | Condition | Written as |
|---|---|---|
| kept | the catalog is already in the target language and the message has a complete translation that passes QA | unchanged |
| memory | a direct-memory or glossary hit that passes the QA gate | finished for `id` and `context` matches by default, otherwise unfinished |
| engine | a validated, cached model batch | unfinished, for review |
| pending | no engine was configured, or no model returned a valid result | empty |

The counts in the run report sum to the number of messages, so nothing disappears between the categories. Engine output is never written as finished: the toolkit's guarantee is that generated text reaches a catalog only as a candidate for review. A separate flag names the memory match classes that may be written finished, and by default only exact matches by message ID or by context qualify.

Two details of the first step prevent common damage. An existing translation that fails the QA gate or is only partly filled is left exactly as it is and reported, not silently replaced. And clearing existing translations to start over is refused unless an engine is configured and the output will not overwrite the input, because clearing without a way to refill would destroy reviewed work.

## What counts as a memory match

Part 4 describes the two kinds of memory: a core memory of terms and a project memory of whole reviewed strings ([405](../4-terminology/405-core-and-project-memories.md)). In the pipeline they play different roles.

A direct memory is matched verbatim. Only Unicode NFC normalization and line-ending normalization apply, so case, spacing, punctuation, `&` accelerators and placeholders all count. Among units with the same source, a match on the message ID outranks a match on context and comment, which outranks a match on the source alone. When every context in the memory gives the same target for a source, the source-only match is offered, unfinished. When they disagree, there is no hit at all and the run records a conflict. A plural message needs units for exactly the forms the target language uses, or it records a plural-shape finding instead of a partial match.

A glossary memory contributes whole-string hits: a message whose entire text is a term takes the term's rendering. [605](605-glossary-enforcement.md) covers both that and the prompt terms a glossary sends to the engine.

A memory can also match the wrong language variant. Catalog tags and memory tags rarely agree: a catalog tagged `de_DE` meets a memory tagged `de`, and `es_MX` meets `es-419`. vexy-localizzy uses the exact tag when the memory has it, and otherwise the single closest variant of the same language that uses the same script, does not cross Brazilian and European Portuguese, and lies within a small distance. `de` may answer `de_CH` and `es-419` may answer `es_MX`, but `es-ES` may not answer `es_MX`, and `en` may not answer `en_GB`. A tie, or no acceptable variant, is a configuration error that someone must resolve by naming the memory language explicitly. Quietly filling a Mexican catalog from a Castilian memory is precisely the kind of plausible, wrong answer a memory-first pipeline exists to avoid.

Every memory hit passes the same QA gate as engine output before it is used. A memory unit whose `%1` has gone missing, or whose accelerator was lost, is rejected with a finding, and the next candidate is tried.

The sources disagree about what to do with a near match, the one case the verbatim rule leaves out.

The 2026 research corpus, and the toolkit design built on it, send translation memory matches above a fuzzy threshold of about 75 percent to the model as few-shot examples. The idea is that a similar approved translation shows the model the house terminology and phrasing.

vexy-localizzy's direct memory ignores fuzzy matches entirely: a string either matches verbatim after normalization or goes on down the chain. Similar examples can reach the model, but only through a separate, experimental retrieval step that attaches examples with their provenance, and the documentation states that such references are examples, not automatic approval of terminology.

The FontLab writing guide takes the strictest line on the human side. A fuzzy match is a draft, never an answer, and should be judged by meaning rather than score: a string that shares most of its words with the new one can describe a different action, and in German and Polish an identical English phrase can need a different case ending.

These positions are compatible once the roles are separated. A fuzzy match may inform a draft, as an example the model sees. It may never fill a message by itself. Treat any pipeline that writes fuzzy matches into a catalog as finished with suspicion.

## Pending is a result

The fourth outcome is the one teams are tempted to hide. When no model returns a valid batch, or when the run is deliberately memory-only, some messages stay empty. vexy-localizzy writes them as unfinished, counts them, and exits with status 1, meaning "not ready". Completed batches remain cached, so rerunning after a provider recovers repeats no finished work.

An empty, counted message is honest. A plausible guess written in its place, from a fallback that was not validated or from a fuzzy match promoted to an answer, is a defect that looks like progress. A pending count is also a planning figure: it tells the team how much work a memory-only run left for the engine or for a translator, before any money is spent.

## A worked comparison

The FontLab project in September 2026 ran two very different jobs on the same memory-first principle, through two commands: `localizzy upgrade` for the existing languages and `localizzy translate` for the new one.

The German, Spanish and French catalogs already existed and had been reviewed. When a new build regenerated the English catalog, the upgrade path ported the approved translations onto it ([310](../3-formats/310-identity-and-upgrade.md)). The CHANGELOG entry for that pass gives the proportions per language:

| Step | Messages per language |
|---|---|
| exact ports of approved translations | 10,448 |
| fuzzy ports, after source typo fixes | 11 |
| memory hits | 7 to 10 |
| engine translations | 5 to 8 |
| retired messages moved to a separate file | 128 |

The upgrade writes fuzzy ports as needing review rather than as finished, in line with the rule above, and all the fuzzy ports, memory hits and engine translations were then reviewed by hand. A model contributed fewer than ten strings per language out of more than ten thousand.

The Polish catalog, created the same week, had no project memory to draw on. Of its 10,474 messages (the count at that pull; a later pull has 10,484), 201 were whole-string glossary hits and the rest were engine output. The same order produced a near-opposite distribution, because the memory-first order reports what the memories actually cover rather than hiding it. The 201 glossary hits are labels whose whole text, ignoring case, tags and accelerators, equals a term. A term inside a sentence cannot fill a message, only guide the engine. A new language therefore starts with almost everything in the engine column, however good its glossary is, and the glossary's value shows up in the consistency of that engine output rather than in the hit count.

The lesson for planning is that the first catalog in a new language is the expensive one. Every later release of that language costs little engine time, provided the reviewed catalog is fed back into the project memory after each review. The FontLab guide says the same from the other side: a memory that is not fed the final text goes stale.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 11: translation memory combined with machine translation)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 12: MT-assisted translation memory workflows)
- The work log and changelog of the FontLab localization project (the Polish localization)
- `README.md`, [docs/memories.md](../8-toolkit/memories.md), [docs/translation.md](../8-toolkit/translation.md) and [docs/retrieval.md](../8-toolkit/retrieval.md) in the vexy-localizzy repository
- [localization/memories](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/memories/) in the vexy-fontlab-writing-styleguide repository
