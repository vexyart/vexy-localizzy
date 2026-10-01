---
this_file: src_docs/md/6-machine-translation/605-glossary-enforcement.md
---

# 605. Glossary enforcement: sending the right terms, checking that they arrived

A glossary records decisions: this concept is *Kerning-Klasse* in German and *klasa kernowa* in Polish, this product name stays English, this retired rendering must not come back. Part 4 describes how those decisions are made. This chapter is about the two moments a pipeline can lose them. The first is before translation, when the engine may receive too few terms, too many, or the wrong ones. The second is after, when the engine may have ignored, misinflected or half-applied a term, and nobody checks.

A glossary instruction in a prompt is a request. Enforcement means checking that the request was honored.

## Two jobs for one glossary

In a memory-first pipeline the core memory does two different things, and it helps to keep them apart.

- **Prompt terms.** For each batch sent to the engine, the relevant terms travel with the strings as hints. The engine is expected to use the approved rendering inside whatever sentence it writes, inflected as the sentence requires. The FontLab writing guide describes the core memory in exactly these terms: a hint on how to render the term inside any sentence.
- **Whole-string hits.** When a message consists of nothing but a term, the pipeline can fill it directly from the glossary without asking the engine ([604](604-memory-first-pipelines.md)).

The first job cannot be verified by the engine's cooperation alone; the second can go wrong in a way that looks correct. Both are covered below.

## Sending the right terms

A glossary attached whole to every request is the common mistake. The FontLab guide puts it plainly: a glossary of two hundred terms attached to a ten-string batch drowns the terms that matter. The model's attention goes to a long list of irrelevant pairs, and the rule for the one term in the batch is harder to find.

vexy-localizzy selects terms per batch. The rules are worth copying even into a pipeline built on other tools.

1. **Match on the text the reader sees.** Before matching, tags, single `&` accelerators and placeholders are removed from each message, so `&Kerning` and `<b>Kerning</b>` both match the term *Kerning*. Matching is on word boundaries, so *class* does not match inside *classic*.
2. **Send only terms that occur.** Each batch gets the terms found in its own messages, and no others.
3. **Cap the list, longest first.** At most sixty terms are sent. When more match, longer terms win. The guide explains why that order matters: the translations of *kerning* and *class* do not compose into the translation of *kerning class*, so the multiword term must not be crowded out by its parts.
4. **Sort for stability.** The selected terms are sorted by source text, so the same batch always produces the same request and the same cache key ([607](607-routing-batching-and-cost.md)).
5. **Send only decided terms.** By default only terms with the status *approved* or *do-not-translate* are used. Proposed terms can be included with an explicit flag. A do-not-translate term is sent as mapping to itself, which tells the model to keep it and leaves it free to inflect around it ([409](../4-terminology/409-do-not-translate-with-restraint.md)).

The status rule deserves a moment. At the end of the first Polish pass, the core memory still held 59 Polish units as proposed, for want of attestation in published Polish sources. Sending them as if approved would have given the engine an unreviewed decision with the authority of a reviewed one. Leaving them out means the engine falls back on its own choice for those concepts, which a reviewer must then check. Neither is free, and the choice should be made deliberately, per run, rather than by default.

## Whole-string hits and the word "open"

A whole-string hit ignores case, tags and accelerators, and it ignores context. That is its weakness. A glossary entry for "open" as the adjective (an open contour) will fill a menu command "Open" whose meaning is the verb. The vexy-localizzy documentation names this exact case, and its default reflects it: term hits are written unfinished, for review, unless the run explicitly allows them to be finished. When a term hit fills a label that starts with a capital letter and the glossary target starts with a lowercase one, the target's first letter is capitalized to match; a do-not-translate term keeps its spelling.

The general rule is that a glossary knows concepts and a catalog holds strings. A string that happens to equal a term is probably that concept, which is enough for a draft and not enough for approval.

## Checking that the terms arrived

After translation, the pipeline has the source, the target and the list of terms that were sent. The check that follows is simple to state: for every core-memory term present in the source, is the approved rendering present in the target? The FontLab guide adds the qualifier that makes it hard: *in any inflected form*.

A check that matches only the dictionary form reports a missing *Kerning-Klasse* whenever the German says *Kerning-Klassen*, and stays silent in Polish, where a noun can take a dozen endings. The guide's list of scripted checks includes three related rules:

- a core-memory term present in the source and absent, in any inflected form, from the target;
- a target that reintroduces a term the core memory retired;
- one source string with two targets across the catalog, and two source strings in one context sharing one target.

The retired-term check matters most after a decision changes. When the FontLab founder issued a Polish terminology update on 29 September 2026, it retired a set of renderings the first Polish draft had used: *reguła przetwarzania* for lookup, *kreska główna* for stem, *szerokość posuwu* for advance width, and others. A scan of the catalog and the help files for every retired term, in every form, was the evidence that the update had been applied everywhere.

A worked example shows how easily such a check misses. The Polish update was applied by a script with ordered literal replacements and two case-aware rule families. One family handled stems: *kreska główna* became *trzon*, with the adjective agreeing (*kreska standardowa* became *trzon standardowy*). The other handled lookups: *reguła przetwarzania* became *podprogram zecerski*, with the plural decided by the governing word.

An independent review pass then found three defects. One rule was not idempotent and doubled *zecerskich* when it ran over text it had already changed. One replacement left the ungrammatical *nakładki się* in a string, the kind of slip that only a reader of Polish would catch. And the stem rule had missed the genitive plural *kresek głównych* in 20 catalog strings and 4 help passages.

The last defect is a textbook case of why inflection-aware checking is hard. Polish inserts a vowel in some genitive plurals, so the stem *kresk-* does not occur in *kresek*. The dative and locative singular *kresce* escapes the same stem through a consonant change. A pattern written by looking at the nominative misses both:

```python
import re

# Every case and number of the retired "kreska główna" (stem).
naive = re.compile(r"\bkresk\w*\s+główn\w*", re.IGNORECASE)
full  = re.compile(r"\bkres(?:k\w*|ek|ce)\s+główn\w*", re.IGNORECASE)

for text in ["kreska główna", "kresek głównych", "kresce głównej"]:
    print(text, bool(naive.search(text)), bool(full.search(text)))
# kreska główna True True
# kresek głównych False True
# kresce głównej False True
```

Three habits follow. List the forms of a term from a grammar, not from the examples at hand; the language portraits in [509](../5-interface/509-language-portraits.md) say which languages need this. Run every replacement rule twice on its own output and require no change on the second run. And test each rule on valid counterexamples as well as intended matches, as the FontLab guide requires: a recurring edit is not by itself evidence for a global rule. After the three defects were fixed, the full retired-term scan came back clean and the catalog compiled with no unfinished messages.

## Where enforcement ends

A term check proves presence, not correctness. It cannot tell whether *trzon* is the right word in a sentence about a stroke cap, which the Polish update deliberately kept as *zakończenie*, or whether a font table and an interface table deserve different words (the update chose *tablica* for the first and kept *tabela* for the second). Those distinctions live in the glossary's definitions and in the reviewer's reading. The script's job is to make sure that every place a decided term should appear has been looked at. Whether it reads well is still a human judgement ([609](609-post-editing.md)).

When a term decision changes, push it to the core memory the same day, regenerate whatever is built from it, and scan for the superseded form. The FontLab guide's reason is short: a decision that lives only in a chat message is not a decision. [410](../4-terminology/410-ledgers-and-decisions.md) describes the ledger that records it.

## Sources

- [docs/memories.md](../8-toolkit/memories.md) in the vexy-localizzy repository (glossary memory, prompt terms, term hits)
- [localization/memories](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/memories/), [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/) and [localization/pl](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/pl/) in the vexy-fontlab-writing-styleguide repository
- The founder's update of 29 September 2026, in the FontLab localization project (the Polish terminology update)
- The work log and changelog of the FontLab localization project (the 29 September update: rule families, review findings, verification)
