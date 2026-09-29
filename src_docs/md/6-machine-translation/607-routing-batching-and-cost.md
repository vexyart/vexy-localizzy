---
this_file: src_docs/md/6-machine-translation/607-routing-batching-and-cost.md
---

# 607. Routing, batching, caching and cost: which model for which string

Once a pipeline knows what to send ([603](603-context-engineering.md)) and what not to send ([604](604-memory-first-pipelines.md)), four operational questions remain. Which model gets which string? How many strings go in one request? When may an earlier answer be reused? And what does all of it cost? The sources answer the first question in two different ways, agree on the second only roughly, and give cost figures that should be read as direction rather than price.

## Tiers in the research, ordered lists in practice

The 2026 research corpus is unanimous that a team should not pick one model. It proposes routing by tier:

| Tier | Strings | Kind of model named in the corpus |
|---|---|---|
| A, critical | legal, marketing, brand, transcreation | the vendors' flagship models |
| B, technical | ICU logic, nested placeholders, code in text | reasoning models, or flagship models with extended thinking |
| C, high volume | simple buttons, drafts | small, fast, inexpensive models |

The fl10n specification turns that into a routing file: rules evaluated top to bottom, first match wins, with conditions such as "has a plural and at least two placeholders" or "context name matches `About*`", and a default rule that sends everything else to the cheapest tier. The corpus's model names and context-window figures are a snapshot of 2025 and 2026 and will date quickly; the corpus says so itself.

The toolkit that was actually built does something simpler. vexy-localizzy takes an **ordered list** of models. It tries the first, and moves to the next only when a provider is unavailable or a model's output fails validation after its bounded retries ([606](606-the-placeholder-protocol.md)). Provider outages set a cooldown that persists in the cache by endpoint and model, so a restarted run does not hammer a route that just failed. A batch that succeeded on a fallback stays pinned to that result after the preferred model recovers; new batches try the preferred model again. The FontLab Polish catalog went further still and used one model for everything.

The two approaches answer different questions. Tier routing is about cost and quality per kind of string. An ordered list is about availability: it gets the same work done when a provider is down. Tier routing also assumes the team knows which model is better for which class of string, and that knowledge needs evidence. The research corpus recommends measuring approval rates per locale and model on the team's own golden set, and switching models when the rate drops below about 70 percent ([608](608-quality-estimation-and-judges.md)). Until a team has that evidence, a routing table encodes guesses. Start with one good model and an ordered fallback, measure, and add tiers where the data says a cheaper model is good enough.

## How big a batch

Batching trades three things against each other: the context the model sees, the damage a failure does, and the number of requests.

The research corpus recommends grouping related strings, all the strings of one dialog for example, into one request of roughly 2,000 to 4,000 tokens, following logical interface groupings rather than file structure. The fl10n specification adopts that: units grouped by context, chunked to that size, split back afterwards.

vexy-localizzy counts differently. A batch holds 1 to 100 distinct message IDs and must fit a byte budget; when an enriched batch exceeds it, the batch splits automatically, and a single item that cannot fit fails explicitly instead of being truncated. The transport also checks the final request, instructions included, against its own limit. The fl10n `localize` command sends batches of 50 messages by default.

Those numbers are not in conflict, only in different units. What matters is the principle underneath: keep siblings together so terminology stays consistent within a screen, and keep a batch small enough that a malformed response costs a retry of fifty strings rather than five hundred.

The FontLab Polish run adds a practical wrinkle. The toolkit processes one batch after another, and a whole catalog through a slow model took hours. The project split the English catalog into four shards and ran four `fl10n localize` processes at once. The splitting script assigns whole Qt contexts to shards, balancing message counts, so no dialog is divided between two processes; a merge step then fills the full target catalog by message identity and refuses to finish quietly if anything stayed unfilled. Parallelism was added at the level where it could not cost context.

Failure handling is part of batch design. When every candidate model fails for a batch, vexy-localizzy raises a pending state that leaves all completed batches intact, and calling again after recovery resumes where the run stopped. Known provider outages get one attempt before the next model is tried, while malformed output gets its bounded retries. Concurrent callers that race on the same batch receive the one committed result. None of this is visible in a quality report, but it decides whether an interrupted overnight run costs a restart or nothing.

## What a cache must key on

A cache turns a repeated run into a free run, and a careless cache turns a changed request into a stale answer. The rule is that every input that could change the output belongs in the key.

vexy-localizzy's key covers the endpoint, the transport version, the temperature, the QA policy and the complete batch: source strings, context, comments, notes, plural descriptions, the glossary terms selected for that batch, style guidance and retrieved examples with their provenance. Changing any of them invalidates reuse. The validator runs again on every cache hit, so a tightened rule rejects an old answer that no longer passes. The run records the model that was requested and the model the provider reports having used, which is not always the same thing.

The research corpus calls the same idea delta translation: translate only new or changed keys and lock the rest, which cuts cost and stops a model from drifting on strings that were fine. The fl10n specification records a source hash, the model and the prompt version per unit, and retranslates when any of the three changes.

A worked example shows why the key must include the batch's own glossary rather than the glossary file. Suppose a reviewer adds one new term to a 300-term core memory and reruns the catalog. Because terms are selected per batch ([605](605-glossary-enforcement.md)), only the batches whose messages contain the new term receive a different term list, and only their keys change. Every other batch is served from the cache, with one condition. If the new term also equals the whole text of some message, that message becomes a whole-string hit and leaves the engine queue; because vexy-localizzy cuts batches in order from the messages that remain, every batch after that point shifts its boundaries and misses the cache. Had the key hashed the whole glossary file, one new term would have invalidated every batch and paid for the whole catalog again. Had the key ignored the glossary, the batches that needed the new term would never have received it.

## Settings that change the answer

Temperature is where the sources disagree in detail. One draft in the research corpus recommends 0.2, raised slightly on retry; another recommends 0 or very low for reproducibility. The corpus reconciles them as a range of 0 to 0.3, with the low end favoured in continuous integration. The fl10n specification uses that range with 0.2 as the default. vexy-localizzy's adapter also defaults to 0.2 but accepts any finite value from 0 to 2, and requires that an overridden value be included in the cache's engine identity, so output generated at one setting is never reused for another.

A low temperature reduces variation. It does not make a hosted model deterministic, and Jiménez-Crespo (2024) lists unpredictability, different answers to the same prompt, as one of the properties that separate language models from neural translation engines. Reproducibility therefore comes from the cache and the recorded request, not from the setting ([610](610-data-terms-and-trust.md)).

## What it costs

The research corpus gives these figures for 2025 and 2026. It flags the per-character prices as projections from a document whose citations could not be resolved, so treat the whole table as directional.

| Item | Figure reported in the research corpus |
|---|---|
| Neural MT services | about 10 to 25 US dollars per million characters, depending on provider |
| Raw language-model pretranslation of documentation | about 0.26 to 0.57 US dollars per 1,000 words, more for mobile XML with code metadata |
| Language-model judging, run only on strings that pass deterministic checks | about 5 to 15 percent of translation spend |
| Trend from 2024 to 2026 | roughly a fivefold cost reduction per unit of quality |

Two conclusions follow, and they are this book's reasoning rather than figures from the sources. If the per-word prices are even roughly right, the engine is unlikely to be the largest cost of a machine-assisted localization; the human review of its output is. And the measures that cut engine spend, memory-first filling, per-batch glossaries and exact caching, also cut review, because every string that was not regenerated is a string nobody has to reread. Roturier (2015) made the volume argument for statistical systems: at low volumes, the effort of deploying machine translation did not justify the loss in quality. With hosted models the deployment effort is small, but the review effort per string is not, and that is the cost a team should plan around.

## Sources

- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 5.5: volume as a criterion for machine translation)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 12: neural translation engines and language models compared)
- `research/04-ai-driven-translation-and-quality-assurance.md` in the fl10n repository (sections 4.3, 4.6, 4.7 and 4.9)
- `spec/04.md` in the fl10n repository (sections 4.3, 4.5 and 4.6)
- `scripts/shard_ts.py` and `src/fl10n/engines/localize.py` in the fl10n repository
- `WORK.md` in the fl10n repository (issue 145)
- [docs/translation.md](../8-toolkit/translation.md) and [docs/memories.md](../8-toolkit/memories.md), and `src/vexy_localizzy/translate/batches.py`, in the vexy-localizzy repository
