---
this_file: src_docs/md/6-machine-translation/602-from-rules-to-models.md
---

# 602. From rules to models: statistical, neural and large language model translation

Machine translation has been rebuilt from the ground up three times since the 1990s. Each rebuild changed what a localization team customizes, what the engine can see of a string, and what kind of mistake it makes. A team that knows the history can read a vendor claim or a research paper and ask the right question: which of these three properties does the new system change, and which does it leave alone?

This chapter walks through rule-based, statistical, neural and large language model translation, then compares them on the axes that matter for software strings.

## Rules and dictionaries

Rule-based machine translation works in three steps. The system analyses the source sentence, transfers its structure into a target structure, and generates a target sentence that follows the target language's rules of agreement and inflection. Roturier (2015) notes that the analysis step carries most of the weight: a misreading there propagates through the other two, and in the SYSTRAN system about 80 percent of the code base was analysis.

For a localization team, the customizable part of such a system was the dictionary. Roturier describes a workflow attributed to Allen (2001): translate the content with the baseline system, identify the terms it gets wrong, write dictionary entries for unknown words, words to preserve and mistranslated phrases, then translate again. Pre-processing modules normalized spelling in the source, and post-processing modules fixed systematic errors with search-and-replace patterns and regular expressions. That last idea, automated post-editing of recurring errors, returns in [609](609-post-editing.md) almost unchanged.

The output of a rule-based system is predictable. Given the same input and the same dictionaries, it produces the same sentence, and a linguist can trace a wrong word to the rule or entry that produced it. The cost is coverage: every construction the rules do not anticipate comes out garbled.

Esselink (2000), writing when these systems were current, was blunt about where they paid off. Machine translation, he wrote, had proven effective only for very controlled input planned for by the post-editing team, and only after the source had been made suitable and the system loaded with specialized terminology. Online gisting engines such as the AltaVista service built on SYSTRAN were not used by professional localization vendors. Microsoft's *Developing International Software* (2002) took a milder view: machine-translated text still needed editing, but editing often took less time than translating from scratch.

## Statistics from memories

Statistical machine translation replaced rules with probabilities learned from parallel text. In the phrase-based variant Roturier describes, a decoder searches thousands of candidate translations built from phrase pairs, scoring each with a translation model (does this phrase mean that phrase?) and a language model (does the result read like the target language?). Training needs aligned sentence pairs, and those mostly come from translation memories created by human translators. Roturier cites the LetsMT! recommendation of at least one million parallel sentences for a translation model and five million for a language model, far more than one freelance translator's memories hold.

Three consequences follow for software.

- **Domain matters more than volume.** Phrases must have been seen to be translated. Training data from sports news is nearly useless for medicine leaflets, and general web text is weak on "kerning class".
- **The unit is the phrase, not the sentence.** Word order across long distances and agreement with a word outside the phrase window are weak points.
- **Evaluation is statistical too.** Metrics such as BLEU count n-gram overlap with a reference translation. Roturier notes they are meaningful at the corpus level, not for a single segment. That limit matters again in [608](608-quality-estimation-and-judges.md).

Customization now meant data rather than rules: collecting and cleaning parallel text, tuning feature weights on a few thousand held-out sentences, and choosing between adapting a generic system and building a new one. Hybrid systems chained a rule-based and a statistical engine, at a cost in complexity that Roturier advises not to underestimate.

## Neural models and the sentence

Neural machine translation, in production from about 2016, reads the whole segment before producing any output. Jiménez-Crespo (2024) illustrates the gain with two sentences that differ in one adjective: "the old man could not cross the street because it was too tired" and "... because it was too wide". The attention mechanism links "it" to the man in the first and to the street in the second, so a Spanish system can pick the right grammatical gender. He quotes Esselink (2022) calling neural translation the innovation with the most impact on the industry in the preceding six years.

The same chapter names the weakness that shapes this whole part: neural output is *deceptively fluent*. A well-formed sentence hides an omission or a shifted meaning, and post-editors who are not used to the task miss it. For software the deeper problem is that the context a UI string needs is rarely inside the segment. "Open" in a File menu and "Open" describing a contour are the same segment. Jiménez-Crespo notes that this can be only partly mitigated by domain adaptation on parallel UI corpora, which are scarce. He reports one attempt to close the gap, Koneru and colleagues' 2023 dataset of UI segments enriched with contextual information for neural systems. The idea of giving the engine the context of a string predates language models. He also records how cautious the platform owners were. Google discouraged developers from localizing their apps with its neural engine, then in mid-2023 released a service that did exactly that for strings and store descriptions in seven languages. The engines were good enough to offer; whether end users would notice remained, in his framing, an open question.

## Large language models

Large language models are built on the same transformer architecture but trained for general text generation. Jiménez-Crespo contrasts them with neural translation engines on three points:

| Property | Neural MT engine | Large language model |
|---|---|---|
| Purpose | translation only | general generation: translate, review, rewrite, explain code |
| Repeatability | tends to give the same output for the same segment | may give a different answer to the same prompt |
| Output | more accurate, less fluent | highly fluent, less accurate |

The research corpus the FontLab localization project assembled in 2026 adds the property that made language models attractive for software: they accept instructions and metadata. A model can be told that "Open" is a verb in a menu, that `%1` is a file name that must survive, that the German glossary renders "mask" as *Maske*, and that the label has room for fifteen characters. The corpus calls the discipline of assembling that information context engineering, the subject of [603](603-context-engineering.md), and states its central thesis almost identically across documents: the difficulty lies in the prompting method, not in raw model power.

It also records a limit on that thesis, from a 2025 study it attributes to researchers at Charles University, Johns Hopkins, LMU Munich and ETH Zurich: "If a model has not learned to translate a given language pair or style, no amount of carefully worded prompting will make it perform better." Model selection comes first; the prompt refines a capable model and cannot create a missing capability.

## What changed for software strings

Each generation moved the point of customization and the typical failure.

| Generation | What the engine sees | What a team customizes | Typical failure on UI strings |
|---|---|---|---|
| Rule-based | one sentence, through its rules | dictionaries, pre- and post-processing rules | garbled output outside the rules' coverage |
| Statistical | phrases within a sentence | training and tuning data | wrong term from the wrong domain; broken long-range agreement |
| Neural | the whole segment | domain adaptation data, glossaries | fluent output with the wrong sense of a short label |
| Language model | whatever the prompt contains | the prompt: context, glossary, style, examples, output contract | fluent, confident output that follows the most plausible reading, and variation between runs |

Two things did not change. The engine still knows nothing about a string that nobody tells it, and its output is still a draft that someone must check against the source.

A worked example shows the shift. The research corpus uses the English label "Home". A neural engine given the bare word has two German candidates, *Zuhause* (a residence) and *Start* (the navigation target), and picks by frequency. A language model given the same bare word does the same. Given a context line that says "navigation button, returns to the start page", the model has what it needs, and a rule-based system of 1995 would have needed a dictionary entry scoped to the product. The engine changed; the requirement that someone supply the meaning did not.

Keep the older advice historical. Esselink's 2000 verdict that machine translation suits only controlled input described engines that could not use context. It is no longer true that a language model needs controlled English to produce usable output. His underlying point, that return on the investment depends on terminology loaded in advance and a planned post-editing step, is still the design brief for chapters [604](604-memory-first-pipelines.md) to [609](609-post-editing.md).

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 11: translation technology, machine translation)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (localization tools and machine translation)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 5.5: rule-based, statistical and hybrid machine translation)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 12: machine translation and localization; large language models and localization)
