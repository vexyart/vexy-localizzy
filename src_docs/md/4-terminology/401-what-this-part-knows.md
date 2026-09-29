---
this_file: src_docs/md/4-terminology/401-what-this-part-knows.md
---

# 401. What this part knows

A font editor has a word for the extra height a round letter needs to look as tall as a flat one: overshoot. A German type designer says *Überstand*, a French one *débordement*. A Polish interface, until September 2026, said *wydłużenie optyczne*, "optical lengthening", a phrase that explains the idea and fits nowhere. Then the founder of the company wrote one line in a review: overshoot is *naddatek*, a surplus, an optical surplus, and "we should also use this principle in other languages if we're unsure". That line contains most of this part. A term is a decision about a concept. The decision has to rest on something better than translating the word. It has to be recorded where every translator and every engine will find it. And when the English word will not travel, there should be a plainer English phrase that will.

## What the part covers

Parts 1 to 3 dealt with what a string is, how code prepares it for translation and which files carry it. This part deals with the words inside the strings that carry meaning across hundreds of messages: the terms. It is written for the terminologist, the translator, the reviewer and the engineer who builds the pipeline, because all four touch the same records.

The chapters move from the concept to the record to the decision:

- [Chapter 402](402-terminology-work.md) sets out what terminology work is: concepts before words, one meaning per term, and the extraction and validation that come before translation.
- [Chapter 403](403-a-glossary-schema.md) designs the glossary record, field by field, with the reason for each field.
- [Chapter 404](404-the-fallback-original-term.md) introduces the fallback original term: a short, plain English rendering stored beside a term, which a translator can translate literally when the term itself has no good equivalent.
- [Chapter 405](405-core-and-project-memories.md) separates the two memories a product needs: the core memory that fixes concepts and the project memory that recycles whole strings.
- [Chapter 406](406-evidence-and-attestation.md) explains how to choose a translation from attested professional usage, and what happens when a decision overrides the evidence.
- [Chapter 407](407-house-voice-across-languages.md) shows how a house voice crosses languages: humor, playful Power names, sly Smart features and ordinary words.
- [Chapter 408](408-word-formation-and-derivation.md) treats a term as a family of forms: the verbs, adjectives, compounds, plurals and cases that follow from one chosen noun.
- [Chapter 409](409-do-not-translate-with-restraint.md) limits the do-not-translate list to what really must stay English.
- [Chapter 410](410-ledgers-and-decisions.md) records every change with its reason, so that the next catalog cannot reintroduce what a review removed.

## Why it matters

The older books agree on the problem. Esselink (2000) calls terminology management a task that projects routinely underestimate and describes a practice built around three kinds of glossary: the operating environment's, the client's and the project's. Roturier (2015) names the three failures that follow from neglect: inconsistent translations, inaccurate ones and inappropriate ones. Jiménez-Crespo (2024) puts terminology "at the core of localization" because digital products keep inventing concepts that need new words.

What has changed since 2000 is who reads the glossary. In Esselink's day a senior translator looked terms up in a termbase linked to a translation memory tool. In 2026 a language model reads the glossary in every batch it translates, and it follows the glossary more literally than any human did. A wrong entry is now copied into a thousand strings before anyone notices, and a missing entry leaves the model to translate the word, which is the error this part is written to prevent. The records have to be precise enough for a machine and explained well enough for a person.

## How the FontLab practice appears

The worked examples come from one real localization. FontLab 9 has a catalog of about 10,500 messages, reviewed in German, Spanish and French in 2026 and localized into Polish in the same year. The founder's review remarks, kept in the `fl10n` repository as issues 133 and 146, turned a pile of corrections into general rules: one meaning gets one translation; do not add detail; keep the length; derive consistently; keep humor; go easy on do-not-translate. The writing styleguide publishes those rules and holds the data: one YAML file per English term, one core translation memory per language, and a project memory of reviewed interface strings. The `vexy-localizzy` toolkit reads those memories when it translates and upgrades catalogs.

Neither the product nor the toolkit is the point. The FontLab case is useful because every decision in it is recorded with the text before and after, so the reasoning can be checked. Where the FontLab data disagrees with itself, for example a language guide that still describes an older decision, the chapters say so. That disagreement is part of the lesson of [chapter 410](410-ledgers-and-decisions.md).

## How to read the part

Read [402](402-terminology-work.md) and [403](403-a-glossary-schema.md) first if you are setting up a glossary. Read [404](404-the-fallback-original-term.md), [407](407-house-voice-across-languages.md) and [408](408-word-formation-and-derivation.md) if you translate or review. Read [405](405-core-and-project-memories.md) and [410](410-ledgers-and-decisions.md) if you build the pipeline. The part leans on the TMX and TBX formats described in [chapter 306](../3-formats/306-tmx-and-tbx.md), and it prepares [chapter 605](../6-machine-translation/605-glossary-enforcement.md), which sends the glossary to an engine and checks that the terms arrived.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 12: terminology)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 5.4: terminology)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 3: terminology and localization)
- `issues/133.md`, `issues/146.md` and `issues/147.md` in the fl10n repository
- [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/) and `localization/tm/pl-core.tmx` in the vexy-fontlab-writing-styleguide repository
- [docs/memories.md](../8-toolkit/memories.md) in the vexy-localizzy repository
