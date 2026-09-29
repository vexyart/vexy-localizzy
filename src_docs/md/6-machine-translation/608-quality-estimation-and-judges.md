---
this_file: src_docs/md/6-machine-translation/608-quality-estimation-and-judges.md
---

# 608. Quality estimation and judges: QE metrics, LLM-as-judge, MQM scoring and their limits

Deterministic checks ([606](606-the-placeholder-protocol.md)) prove that a translation will not break the application. They say nothing about whether it means what the source means. For that, a pipeline has three kinds of automatic help: metrics that compare the output with a reference translation, quality estimation that scores the output without one, and language models asked to judge it against an error typology. All three are useful for deciding where a human should look first. The sources disagree about whether any of them may decide that a human need not look at all.

## Reference metrics and why they lost their place

The oldest automatic metrics compare machine output with one or more human reference translations. Roturier (2015) describes BLEU, which counts overlapping word sequences, alongside Meteor, TER and others, and makes two points that still hold. The scores are meaningful at the corpus level, for comparing systems, and not for judging a single segment. And they capture different aspects of quality: BLEU says more about fluency than about whether the meaning survived.

For interface strings the problems multiply. A two-word label has too few word sequences to measure. There is usually no reference translation for a new string, which is the reason it is being translated. And a correct translation can share few words with the reference. The 2026 research corpus puts the consensus bluntly as "BLEU is dead for LLM translation" and recommends never gating a decision on n-gram metrics for neural or language-model output. It keeps BLEU and chrF only for backward comparison.

The corpus also reports a result that shows why metric choice matters. In the 2024 WMT evaluation, as it summarizes it, one language model won nine of eleven language pairs on human evaluation, while a different system led on the COMET metric. Its sources read that split as a sign of systems optimized for a metric rather than for readers.

## Quality estimation

Quality estimation predicts the quality of a translation from the source and the output alone. Roturier described it in 2015 as a supervised machine-learning task: extract features from the source and target (lengths, language-model probabilities, punctuation counts), train a model on examples labelled by humans, and predict a label such as good or bad, a comprehensibility grade or the post-editing effort a segment will need. He also notes the Internationalization Tag Set 2.0 data category for machine translation confidence, a score from 0 to 1 that lets tools exchange such estimates alongside the content.

The neural successors named in the research corpus are more accurate and work the same way from the outside. COMET-QE and COMETKiwi score a translation without a reference, which suits new strings. xCOMET adds error spans and is the corpus's recommended default when a reference exists. MetricX-24 led the neural metrics at WMT24, according to the corpus.

A QE score is a number per segment. It is good at ranking: this string looks riskier than that one. It is weaker at the absolute question of whether a given string is acceptable, and it cannot say what is wrong unless it reports spans. That makes it a natural triage tool. The fl10n specification treats it that way: an optional, heavyweight layer that flags low-scoring units for further checking.

## Language models as judges

A language model can be asked to read a source and a translation and list the errors it finds, with a category and a severity. The research corpus traces the approach through several methods, as it reports them:

- **GEMBA-MQM** (Kocmi and Federmann, 2023) used GPT-4 with a fixed three-example prompt to produce MQM error spans, and reached 96.5 percent system-level pairwise accuracy on WMT23.
- **Rubric-MQM** (2025) used span-level rubric prompts and a score from 0 to 100, addressing GEMBA's tendency to overuse the mistranslation category and the major severity and to fail on error-free segments.
- **HiMATE** (2025) assigned one agent per MQM category and reported large gains over a single-model baseline.

A judge finds what a linter cannot: a meaning that drifted, a register that is wrong for the product, a term that ignores the glossary. The corpus's typographic example is a model translating "Kern" in a font editor with the word for a fruit kernel. A judge given the domain would flag that; a placeholder check never would.

The corpus is equally direct about the costs. Judges are probabilistic and inconsistent between runs, report 15 to 25 percent false positives without calibration, drift when the provider updates the model, and cost far more than a local check. The mitigations it lists are structured JSON output, temperature 0, voting across several judges, calibration against a set of segments labelled by humans, and a pinned model and prompt version. The fl10n specification adds sampling, judging about one unit in ten, and records the judge model and prompt version with each score.

The corpus also lists ways to detect semantic drift without a judge: back-translate the output and compare sentence embeddings with the source, or use a reference-based metric. The FontLab quality specification is wary of the first. Back-translation introduces another translation, it notes, and can raise questions but cannot by itself establish accuracy; a proficient reviewer resolves the meaning against the source and the product.

A judge that shares the translator's blind spots is a particular risk. If the same model family drafts and judges, a systematic misreading can pass twice. Where possible, judge with a different model, and always calibrate on examples where the right answer is known.

## MQM scores and their weights

Multidimensional Quality Metrics provides the vocabulary judges and human reviewers share. Jiménez-Crespo (2024) describes the merged MQM-DQF framework: error families for accuracy, linguistic conventions (formerly fluency), terminology, style, locale conventions, design and markup, and audience appropriateness, with severities critical, major, minor and null. A critical error makes the product unfit for use or carries legal or reputational risk; a major error prevents the reader from understanding the intended meaning without making the product unusable; a minor error does not affect usability; a null severity records a preferential change without penalty. [705](../7-process/705-lqa-and-mqm.md) treats the framework as a sign-off instrument.

The typology is shared. The weights are not.

| Scheme | Critical | Major | Minor | Decision rule |
|---|---|---|---|---|
| LISA QA model (as described by Jiménez-Crespo 2024) | 10 | 5 | 1 | project threshold on combined points; above it the text is judged unpublishable |
| FontLab house specification | 100 | 10 | 1 | ship with no critical open and every major fixed or accepted by name; a count of minors is a planning figure, not a gate |
| Lokalise translation scoring (as reported in the research corpus) | deducts 75 | deducts 15 | deducts 1 | score from 0 to 100; 80 or above approves automatically, below 80 goes to a human |

A worked example shows how far apart they land. Take a batch of twenty strings with one wrong term (major) and two misplaced spaces (minor). The Lokalise-style score is 100 minus 15 minus 2, which is 83, and the batch approves itself. Under the FontLab rule the batch cannot ship until someone fixes the term or records by name why it may stay. Under the LISA model it depends entirely on the threshold the project set. The same errors produce three decisions, and none of the three numbers says which string holds the wrong term. A score summarizes; it does not locate.

## Triage or approval

Here the sources disagree outright.

The fl10n specification lets the judge decide eligibility: a score of 80 or above makes a unit eligible for automatic approval, while a score below 80 or any critical span routes it to a human. A human confirmation in the review tool remains the only path to the approved state, but the score decides which units are routed to a person for correction and which arrive already marked as acceptable.

The FontLab writing guide says quality estimation may triage and may not approve: a score can point the reviewer at risky strings and cannot say that a string is right. vexy-localizzy is built on the same line. Its content checks explicitly exclude linguistic quality scoring, its `ready` flag means every message has an acceptable candidate and not semantic approval, and engine output is always written for review.

The difference comes down to the cost of a false pass. For help articles read once and replaced next quarter, an 80 threshold with sampled human review may be a sound trade. For interface labels that ship for years and train users' vocabulary, the guide's rule is safer: use the score to order the queue, and let a human approve.

Whichever rule a team adopts, it needs its own evidence. The research corpus recommends a golden set of about 200 segments per language, scored by humans with MQM, against which candidate models are re-measured quarterly. It treats vendor-published results as upper bounds from interested parties. The figure it singles out as most credible, because the customer published it, is Mozilla Pontoon's 2023 pretranslation trial: 61 percent of suggestions approved on average across 3,211 strings, 84 percent for German and 42 percent for Traditional Chinese. A team deciding whether a score may approve anything should know its own version of those numbers first.

## Sources

- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 5.5.2: evaluation; sections 5.7.4 to 5.7.6: statistical and machine-learning checks, quality standards)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 4: MQM-DQF, the LISA QA model, error severity)
- `research/04-ai-driven-translation-and-quality-assurance.md` in the fl10n repository (sections 4.7 and 4.9)
- `research/06-tldr.md` in the fl10n repository (chapter 4 summary)
- `spec/05.md` in the fl10n repository (sections 5.1 and 5.5)
- `docs/quality.md` and `docs/translation.md` in the vexy-localizzy repository
- `src_docs/md/localization/quality.md` and `memories.md` in the vexy-fontlab-writing-styleguide repository
