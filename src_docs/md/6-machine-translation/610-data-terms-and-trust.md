---
this_file: src_docs/md/6-machine-translation/610-data-terms-and-trust.md
---

# 610. Data terms, privacy and trust: unreleased strings, provider policies and reproducibility

Every chapter of this part has asked the pipeline to send more: comments, sibling strings, glossary entries, style sheets, retrieved examples, screenshots. Each of those is information about a product that has not shipped. A catalog for the next release names features before they are announced, and a screenshot shows them. Sending it to a hosted model is publishing it to a third party, under that party's terms.

This chapter covers the two obligations that follow. The first is to know what those terms allow before anything is sent. The second is to be able to show, months later, exactly what was sent, what came back and who approved it. The first is about privacy, the second about trust, and a machine-assisted catalog needs both.

## What leaves the building

Confidentiality was a localization problem long before language models. Roturier (2015) lists it among the reasons developers withhold context from translators: even under a non-disclosure agreement, a publisher may refuse to show a running build or its screenshots to a third party, to prevent leaks. He also notes the translator's side. A translator must make sure that using a particular tool does not breach the agreement signed with the customer, and may object to a tool whose terms conflict with their views on how the data will be handled.

Context engineering sharpens that tension. The fields that most improve a translation, screenshots and surrounding strings above all, are the ones that reveal most. A team has three honest options, and it should choose one on purpose:

- send full context to a provider whose terms it has read and accepted for unreleased material;
- send reduced context, such as comments and glossary hits but no screenshots, and accept more review work;
- run a model the team controls, which the research corpus mentions for open-weight models deployed on the team's own infrastructure for privacy.

The wrong option is the default one: sending everything to whatever endpoint a developer configured last, because nobody asked.

## Reading the terms

The FontLab writing guide states the rule: check the provider's data terms before sending unreleased strings; a tool whose terms allow retention or training conflicts with the release schedule and with the confidentiality a company owes its own roadmap. Roturier's exercise for students asks the same questions of a translation management system: find the terms and conditions, read how uploaded content may be handled or used by the system's owner, and check what they say about data privacy and the copyright of translations.

This book does not summarize any provider's policy. Policies change, and a summary would be out of date before it was read. What does not change is the list of questions a team should be able to answer, in writing, for each endpoint it uses:

| Question | Why it matters |
|---|---|
| Is request content retained, and for how long? | retained strings are unreleased product information held by someone else |
| May it be used to train or improve models? | trained-in strings can resurface outside the company's control |
| Where is it processed and stored? | jurisdiction and data protection law, which Roturier notes can determine whether and how content is localized |
| Who can access it, including for abuse monitoring? | a human reader at the provider is a disclosure |
| Who owns the output? | the translated catalog must be the company's to ship and relicense |
| Do the answers differ by account type or contract? | the same model may come with different terms through different channels |

Record the answers with the date they were checked and the document they came from. A decision that exists only in someone's memory will not survive the next change of provider.

## Keeping the choice with the project

Tooling can make the right choice easy or accidental. vexy-localizzy's design puts every choice about where data goes in the hands of the project that calls it. Its documentation states that credentials, endpoint, model choices and project guidance belong to the calling application. The toolkit never hard-codes a product path, name or language roster. The engine endpoint is a setting, any service that speaks the OpenAI-compatible protocol can be named, and the API key is read from an environment variable the project designates. A memory-only mode sends nothing anywhere.

The review tool follows the same principle. It serves on the loopback interface only, so reviewers work on their own machine rather than on a shared web service, and it renders previews in an isolated frame that disallows scripts and network loads. Private glossaries and style guidance stay with the caller and are passed in per run.

None of this settles the policy question. It makes sure the question has one place to be answered: the project's configuration, which can be reviewed like any other change.

## Reproducibility

Jiménez-Crespo (2024) lists unpredictability among the properties that separate language models from neural translation engines: the same prompt can produce a different answer. The FontLab guide draws the operational consequence. Pin the prompt, the model and the settings, and record them beside the output, because a review that cannot name what it reviewed cannot be repeated.

vexy-localizzy records more than that. Each translation run writes a provenance report beside the output catalog, with the input digest, the language pair, every memory file with its SHA-256 and unit count, the counts per outcome, and one row per message giving its origin, match class, memory file and unit IDs, the glossary terms it received, the model requested, the model the provider reported, and the digest of the request. The cache keeps the exact responses keyed by everything that shaped them ([607](607-routing-batching-and-cost.md)). When the embedding step and the translation step need separate environments, the prepared contexts can be frozen into an archive with checksums, and translation refuses to start if the archive does not match.

On request, the origin is also written into each filled message as a Qt extra element, which Qt keeps with the message:

```xml
<extra-localizzy-origin>memory:de-fontlab-ui.tmx#Menu|Save;match=context</extra-localizzy-origin>
```

The default is the sidecar report only, so shipped catalogs carry no extra diff. The FontLab Polish run kept one provenance report per shard, four in all, stored with the upgrade data.

A worked audit shows what this buys. Suppose a German user reports that a menu item reads oddly, and support asks why the catalog says what it says.

| Question | Where the answer is |
|---|---|
| Was this text a kept translation, a memory hit or engine output? | the message's row in the run's provenance report |
| If memory, which file and unit, and was the match by ID, context or source? | the same row: memory file, unit IDs, match class |
| If engine, which model produced it and with what glossary terms? | requested and reported model, glossary terms, request digest |
| Exactly what did the model receive? | the cached request under that digest |
| Who approved it, when, and with what reason? | the review journal or the project's ledger ([410](../4-terminology/410-ledgers-and-decisions.md)) |

Without those records, the only possible answer is a guess, and a correction made on a guess can reintroduce the error it fixes.

## What a catalog state may be trusted to mean

Trust in a machine-assisted catalog comes down to what its states promise. The rules worth adopting, each of them implemented in vexy-localizzy, are short:

- **Generated text is never finished.** Engine output and weak memory matches are written unfinished; only named match classes may be written finished.
- **Approval is a human act with a record.** In the review tool, a draft stays unfinished and approval sets the approved state. Approving text identical to the source requires a written reason, kept in an append-only journal.
- **Ready is not approved.** A run is ready when every eligible message has an acceptable candidate. That says the checks passed, not that anyone read the result.
- **Finished in the file is not reviewed.** The toolkit writes engine output unfinished, yet the FontLab Polish draft was later marked finished throughout, compiled that way, and was still awaiting a native editorial pass. The project records do not say which step set the state, and that gap is exactly why a finished flag cannot be read as review. Keep the richer review state beside the native file when the native format cannot hold it.

Trust also runs outward, to the people who use the product. Jiménez-Crespo (2024) distinguishes overt machine translation, where users know a text came from a machine, from covert use, where they do not. He describes two companies that published unreviewed machine translation deliberately and measured the result: Microsoft asked readers of machine-translated help pages whether the page solved their problem and treated a page that mostly did as fit for purpose, and eBay flagged machine-translated product pages that drew heavy traffic from one region for human post-editing or full localization. Both are defensible because the decision was explicit and the feedback loop was real. An interface catalog shipped from an unreviewed draft, with no record that it was one, is covert use by accident.

A reader of a catalog, whether a reviewer, an auditor or the next engineer, should be able to tell from the file and its records which strings a person has read. When that is true, a model can draft as much as the budget allows. When it is not, every string in the catalog carries the same unanswered question, and the fastest translation in the world has produced a file nobody can vouch for. [710](../7-process/710-release-provenance-and-roadmap.md) carries these records through to release.

## Sources

- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 1.1.3: local laws; section 3.2.4: confidentiality and context; section 5.2: translation environments and their terms; task 5.9.1: reviewing the terms and conditions of an online translation management system)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 12: overt and covert machine translation; neural translation engines and language models compared)
- `research/04-ai-driven-translation-and-quality-assurance.md` in the fl10n repository (section 4.6: open-weight models for on-premises use)
- `WORK.md` in the fl10n repository (issue 145: per-shard provenance)
- `README.md`, `docs/memories.md`, `docs/translation.md`, `docs/retrieval.md` and `docs/review.md` in the vexy-localizzy repository
- `src_docs/md/localization/memories.md` and `pl.md` in the vexy-fontlab-writing-styleguide repository
