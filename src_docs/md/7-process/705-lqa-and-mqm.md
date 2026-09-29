---
this_file: src_docs/md/7-process/705-lqa-and-mqm.md
---

# 705. Linguistic quality assurance: MQM families, severities, thresholds and sign-off

"Is the translation good?" has no answer until someone says good for what, measured how, and accepted by whom. Linguistic quality assurance, LQA in the trade, is the practice of answering those three questions before the review starts, so that the review produces a decision rather than an opinion. This chapter covers the passes a localized release goes through, the error typology most of the industry now uses, the weights attached to severities, and the sign-off that turns a list of findings into a release.

## Passes, levels and who signs

Esselink (2000) distinguished quality assurance, the processes that make a good result likely, from quality control, the checks that find what went wrong in a result. He divided localization testing into three levels. Linguistic testing has a translator review the running application in context. Cosmetic testing checks that everything fits: truncation, hot keys, dialog sizes. Functionality testing confirms that localization has not broken anything. Jiménez-Crespo (2024) keeps Esselink's three stages and adds a fourth, accessibility or user-experience testing, which checks among other things that labels read aloud to screen-reader users are translated and correct.

The FontLab writing guide adopts the four passes and gives each its own sign-off: linguistic, cosmetic, functional and accessibility. It adds a warning that both older sources support. Functional testing is easy to score, so it crowds out the linguistic pass. Jiménez-Crespo quotes Dunne on the reason: because functional aspects can be assessed objectively, "people often perceive software development and localization as processes that are akin to manufacturing", and forget that linguistic quality is partly a matter of judgment. The guide's remedy is administrative: keep the linguistic sign-off separate and record the name of the person who gave it.

Dr International (2002) narrows the scope from a different direction. Its argument is that a single world-ready binary, tested once for global functionality, makes localization testing "less technical and more a matter of checking grammar and spelling". Esselink and the FontLab guide still run separate cosmetic and functional passes for each language. The positions differ in their assumptions rather than their facts. If the binary really is world-ready and the resources are really separate, per-language functional testing finds little. The FontLab guide records per-feature support and the tested build precisely because that assumption cannot be taken on trust: its runtime checklist includes parsers that read localized numbers and shortcuts on the actual keyboard layout, both of which a translation can break.

Before counting errors, record what the language is supposed to have. Jiménez-Crespo reports a three-level scheme for software, attributed to Brooks at Microsoft: an *enabled* product accepts the user's language and script while its interface stays in another language; a *localized* product translates the interface and help; an *adapted* product also adapts language tools and content. The FontLab guide records this level per language, separately from the depth of review, so that everyone means the same thing by done.

## Error families

The error typology in wide use is MQM, the Multidimensional Quality Metrics framework. Jiménez-Crespo describes how it merged with the TAUS Dynamic Quality Framework and lists its core issue types. The FontLab guide builds its house categories on the same core and gives each an example from its own catalog.

| Family | What it covers | A FontLab example |
|---|---|---|
| Accuracy | Omission, addition, mistranslation, untranslated text | Invented specificity: *anchor cloud* for *cloud* |
| Terminology | Wrong term, inconsistent term, one concept two ways | A term that contradicts the core memory |
| Linguistic conventions | Grammar, spelling, punctuation, register | Wrong case after a placeholder |
| Locale conventions | Numbers, dates, quotation marks, key names, units | A key name that is not the local one |
| Style | Correct but reads as a translation | Headline style not applied |
| Compliance | Platform and variety rules | A platform command that does not match the localized system |
| Design and markup | Placeholders, tags, clipping, mnemonics | A duplicate mnemonic |
| Audience | Suitability for the reader | A native word where professionals expect the loan |

Two entries need comment. MQM calls the last family *audience appropriateness*; Jiménez-Crespo notes that an earlier MQM draft called it *verity*, covering cases where a text is fluent and accurate yet wrong for the market, such as a support contact that does not exist in the target country. *Compliance* is not in the MQM core. Jiménez-Crespo reports it as a video-game customization for errors against platform guidelines, and the FontLab guide borrows it for mismatched operating-system commands and mixed dialects.

The FontLab table also settles a question that causes arguments in every review: an established professional loan is not a terminology error, and an unattested calque is. Part 4 covers how that evidence is gathered.

## Severities and weights

A finding needs a severity as well as a family. Sources agree on the idea and disagree on the numbers.

| Scheme | Critical | Major | Minor | Null | How the result is used |
|---|---|---|---|---|---|
| LISA QA model, as described by Jiménez-Crespo | 10 | 5 | 1 | none | Above a set threshold, the text is unpublishable |
| MQM defaults, as described by Jiménez-Crespo | 100 | 10 | 1 | 0 | Weighted error total against a threshold |
| FontLab house scale | 100 | 10 | 1 | 0 | No open criticals; every major fixed or accepted by name |
| Lokalise translation scoring, as reported in research/04 | minus 75 | minus 15 | minus 1 | none | Score of 0 to 100; 80 or more may be approved automatically |

The *null* severity records a change that is not an error, typically a synonym a reviewer prefers. It keeps preferential edits in the ledger without counting them against the translator. Jiménez-Crespo adds that, according to Lommel, weights have not been widely implemented in practice, which matches the FontLab rule of treating minor counts as a planning figure rather than a gate.

The Lokalise scheme is the easiest to apply to one segment, if its penalties are read as deductions from 100. A segment with one major error scores 85 and clears the threshold of 80. A segment with two major errors scores 70 and goes to a person, as does any segment with a critical error. Research/04 reports the same threshold for model judges, with the added rule that any critical span goes to a person regardless of score. The arithmetic is simple; the choice of threshold is not, and none of the sources derives it from data.

Severity depends on consequence in context, and the FontLab guide gives the example that makes this concrete. A clipped final word can hide the scope of a destructive action, which is critical; clipping an optional explanation may leave the task understandable, which is minor. The category is the same in both cases. What the reader could misunderstand or fail to do sets the severity.

## A worked finding

The first FontLab metrics pass recorded this change to the German catalog, one of nine entries that make the same change to the source "Width" in different contexts:

```json
{
  "language": "de",
  "id": "FL-3d51ea191da7b93d",
  "context": "ActionAdjustMetrics",
  "source": "Width",
  "before": "Breite",
  "after": "Dickte",
  "why": "The control edits glyph advance/metrics width; it does not measure the outline bounding box. Proteus advanceWidth()/gi::AdvanceWidth; FontForge de Width TU 27422753."
}
```

The ledger records the reason and the evidence but not an MQM category or severity. Classifying it under the house table is instructive. *Breite* is a correct German word for width, so this is not a linguistic error. It names the wrong concept: the bounding-box width instead of the advance width, which German type designers call *Dickte*. That is a terminology error, the wrong term. Its severity depends on the control. On a label that sets the advance width, a user who reads *Breite* may expect the command to change the outline and be surprised when only the spacing moves. Under the house scale that is a major error: the user notices and is slowed, but is not led to damage anything. The reason field is what makes the classification possible. A ledger that recorded only "Breite to Dickte" would leave the next reviewer to guess.

## Thresholds, sampling and sign-off

A threshold is only as good as the sample it is applied to. The FontLab guide asks reviewers to go first to the strings least like approved translations: new contexts, long strings, strings with placeholders, and strings an engine drafted without a memory match. It asks for the sample's selection, size, source revision and exclusions to be recorded, and states the limit that follows: a sample score cannot certify every string. It also sets a stopping rule. If the first hundred strings show a systematic error, fix the cause and review again, rather than correcting string by string.

The same guide is cautious about back-translation. Translating the target back into English can raise questions, but it introduces another translation, so a proficient reviewer must still resolve the meaning against the source and the product.

The release rule then follows from the severity scale:

1. No critical finding is open.
2. Every major finding is fixed or accepted by a named person.
3. Minor findings are counted for planning, not for release.
4. Each pass has its own sign-off, and the linguistic sign-off names its reviewer.

The FontLab guide adds one more distinction that keeps sign-off honest: accepting a known issue for a release does not mean it was fixed, and the ledger should keep release disposition separate from repair status. Chapter [707](707-review-tools-and-people.md) turns to the people who give these sign-offs and the tools they use.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 5: QA and QC, levels of testing)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 3: levels of localization; chapter 4: LQA stages, MQM and DQF, the LISA QA model, error severity)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 11: the world-ready approach to testing, localization testing)
- `research/04-ai-driven-translation-and-quality-assurance.md` in the fl10n repository (section 4.7.3)
- [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/) and [localization/runtime-review](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/runtime-review/) in the vexy-fontlab-writing-styleguide repository
- `data-fontlab-cpp/i18n/review/2026-09-28-metrics.json` in the fl10n repository
