---
this_file: src_docs/md/7-process/708-vendors-tms-and-projects.md
---

# 708. Vendors, translation management systems and project management

Localization is a small project wrapped in a large coordination problem. Translating 73 new messages into four languages is an afternoon's work for competent translators. Deciding who translates them, from which files, with which terms, checked by whom, delivered where and paid how, can take longer than the translation. This chapter covers the three decisions that shape that coordination: who does the work, which system carries it, and how the project is scoped, priced and run.

## Who does the work

Uren, Howard and Perinotti (1993) framed the first decision geographically, for a US developer shipping to Western Europe. Their three models were: do everything at home; internationalize at home and localize in the target country; or develop in both places and localize and manufacture in the target country. Each trades time against accuracy. A localizer near the developers communicates quickly but may be out of touch with current usage in the target market and short of local hardware and software. A localizer in the market knows the language as it is spoken now, the local distributors and the local press, but every question costs a day. Their description of office hours overlapping for about an hour between California and Europe, and of packages taking three or four days by courier, is dated; their conclusion is not. Last-minute changes are hard to handle when the parties are far apart, and accuracy depends on how precisely and how promptly information reaches every party. The distance that matters now is organizational rather than geographic: a vendor who cannot see the running product is far away even on the same street.

They also warned about a failure that still occurs: some companies saw quality deteriorate because a collaborator responsible for localization costs cut them too far. The remedy they gave was contractual, with ownership of the localized product settled in writing. They note that in some countries, France among them, the translator owns the copyright to the translation unless the contract says otherwise.

Esselink (2000) turned the division of labor into a checklist to settle before the project begins: who tests, who fixes, what level of testing is required, whether test scripts exist and who writes them if not, how bugs are reported and tracked, whether automated testing is needed, how many regression cycles there will be and how long each takes. His default division was that vendors perform cosmetic and basic functional testing on what they localized, while the publisher owns full functional and internationalization testing, because source-code and internationalization defects can only be fixed by the publisher.

He also recorded the practice of releasing languages in tiers. The main European languages, French, Italian, German and Spanish, were commonly Tier 1 and the Nordic languages Tier 2, varying by publisher. The FontLab project uses a similar idea in its language roster, and its writing guide adds a caution: a tier describes the planned depth of review, not the scope of localization, which is recorded separately as a level.

## Choosing a translation management system

A translation management system, or TMS, holds source strings, memories, glossaries and workflow state, and connects translators, engines and reviewers to the repository. Jiménez-Crespo (2024) describes its role in continuous localization: it pulls new content from the repository through connectors, matches it against translation memory, sends what remains to machine translation and people, and pushes results back.

Research/05 compares three systems as they stood in 2025 and 2026. Its prices and model lists change too quickly to reproduce here; the structural differences are more durable:

| Concern | Crowdin | Lokalise | Weblate |
|---|---|---|---|
| Format coverage | Over 100 formats, Qt `.ts` native | About 80, the major ones | The Translate Toolkit formats |
| Quality scoring | Third-party app or external prompt | Built-in MQM-style score on higher plans | External prompt |
| Repository integration | GitHub Action | Push and pull actions | Webhooks and a git remote |
| Hosting | Hosted | Hosted | Hosted or self-hosted (GPLv3) |
| Per-seat fees | No | Yes, on lower tiers | No, when self-hosted |

The research synthesis recommends Crowdin for a Qt desktop product because of its native `.ts` support, Lokalise where score-based routing matters, and self-hosted Weblate where data must stay on premises or per-word billing is unwelcome. The toolkit design treats all three as optional: the project runs on git, a command-line tool and a model provider, and a TMS would be a sync target, not the owner of the translations.

That choice has a cost and a benefit. Without a TMS, the project writes its own glue: the upgrade, review and ledger tools described elsewhere in this part. With one, it inherits a web editor, translator management and vendor integrations, and it takes on the lock-in risk that research/05 warns about. Whatever the choice, keep a canonical copy of every catalog in git, as chapter [703](703-branches-and-merges.md) argues, and check how the TMS handles the format's hard parts before committing: plural forms, disambiguating comments, and placeholders.

## Scoping, pricing and the kit

Esselink's chapter on project evaluation begins from a simple observation: the word counts and file lists a publisher sends are rarely enough to define the scope. An evaluation should establish both unit counts and production hours, for every component: software, help, documentation, graphics and desktop publishing. His practical rules have aged well:

- Count words with at least two tools, because different tools give different counts from the same files.
- Separate the total into new words, internal repetitions, and matches against previous translations, including fuzzy matches.
- Look for words the counters miss: text in graphics, meta tags, scripts and generated messages.
- Test-compile the source before translation, because a defect found now is fixed once and a defect found later is fixed once per language.
- Treat licence agreements separately, and ask whether they need translation or rewriting by a lawyer in the target country.

His pricing chapter gives the unit for each activity: translation by word, engineering by dialog or hour, testing by hour or help topic, desktop publishing by page, graphics by screen or hour. He puts software translation at about 20 to 30 percent above documentation per word, because it is harder. On project management his figures disagree with each other. The introduction to the chapter gives the industry standard as around 10 percent of total project cost. The pricing section gives 10 to 15 percent, sometimes with a further 2 to 5 percent for communication. Both are reported as industry practice around 2000; a reader budgeting today should treat them as a range rather than a rule.

Research/05 adds a modern budget line that Esselink could not have had: model inference. It suggests tracking cost per thousand words per model and language, and rethinking the architecture if language-model spend exceeds about 30 percent of total localization spend. Like the other figures in that synthesis, this is a recommendation rather than a measurement.

The deliverable that turns an evaluation into work is the localization kit. Esselink lists what a translator should receive: the schedule, the instructions, the files in native and tool formats, a running version of the product, previous translations, reference material such as glossaries and style guides, and the procedures to follow. Jiménez-Crespo's process description adds a testing plan and an analysis of third-party components. The FontLab translator handoff states the same needs in terms of responsibility: name the delivery revision, the expected files, the review responsibilities and the person who resolves source questions; share accepted answers across all affected languages; and include corrected editable sources in the return package so that a late fix survives the next build.

## A worked scope: one catalog update

The founder's update of 29 September 2026 is small enough to scope completely. Suppose it had gone to a vendor instead of being handled in house. The request would have needed to state:

| Item | Content |
|---|---|
| Languages | German, Latin American Spanish, French, Polish |
| Catalog work | 73 messages new since the last approved catalog, already translated by developers, to be reviewed; 63 removed messages to retire, not translate |
| Polish terminology | A founder's term list applied across the catalog, the Help Panel and the welcome tips |
| Reference | Core and project memories per language, the language guides, the running build |
| Deliverables | Corrected `.ts` catalogs, an exact ledger of every change with prior text and reason, updated memories |
| Acceptance | Validator and `lrelease` pass with every message finished; no retired term left in catalog or help |
| Owner of source questions | Named in the request |

Three lines in that table are there because of what went wrong elsewhere. The ledger is required because a vendor's corrections are only reusable if the next reviewer can see why they were made. The acceptance line names machine checks, which are necessary, and says nothing about whether the Polish is idiomatic, which is why the independent review described in chapter [704](704-the-qa-gate.md) still happened. And the retired messages are listed so that nobody is paid to translate strings the code no longer contains.

Esselink advised adding assumptions to every proposal, among them that many stylistic or preferential changes requested by a publisher's reviewers would be invoiced as extra time. The FontLab severity scale gives that assumption teeth: a preferential edit is recorded with severity *null*, so the ledger itself separates corrections from preferences, and the argument about who pays for which becomes a query rather than a negotiation.

## Running the project

Esselink's project manager keeps one project folder with every delivery in both directions, numbers deliveries sequentially with a language code, keeps a communication plan with an escalation path, and tracks time, quality and budget together. In a repository-based project most of that is replaced by version control: the folder is the repository, the numbered delivery is a commit, and the escalation path is an issue tracker.

What version control does not replace is measurement. Research/05 lists the indicators worth tracking per language: coverage, freshness (days since the last sync and the number of outdated strings), cost per thousand words, the distribution of quality scores, and the human approval rate per pair of locale and model. None of them says whether the translation is good. Together they say where to look first, which is the question a project manager is paid to answer.

## Sources

- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (chapter 8: time, accuracy, geography, business relationships, ownership, roles)
- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 5: division of testing responsibility; chapter 13: project evaluations and word counts; chapter 14: project management, quotations, tiers, kits, scheduling)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 3: project preparation, localization technologies)
- [docs/ci.md](../8-toolkit/ci.md) in the vexy-localizzy repository
- The founder's update of 29 September 2026, and the changelog and work log of the FontLab localization project
- [localization/handoff](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/handoff/) and [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/) in the vexy-fontlab-writing-styleguide repository
