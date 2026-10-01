---
this_file: src_docs/md/7-process/704-the-qa-gate.md
---

# 704. The quality gate: deterministic checks, estimation, judges and the residual for humans

A translated catalog can fail in two ways. It can break the product: a `%1` that disappears, a tag that no longer closes, a plural with two forms where the language needs three. Or it can mislead the user while working perfectly: a German label that names the wrong operation, a Spanish warning that drops its condition. The first kind of failure is cheap to detect and expensive to ship. The second is expensive to detect at all. A quality gate is the arrangement of checks that deals with both, in the right order, and hands people only what the machines cannot settle.

## A gate in layers

Research/04 describes the gate that nearly every 2026 source converges on. A translated string passes through deterministic checks first. If it passes, a quality-estimation metric may score it. If the score is low or the string matters, a language model acting as a judge rates it against an error typology. Only what survives, or what the judge flags, reaches a person.

```text
translated string
  -> deterministic checks   (placeholders, tags, plurals, length)  fail: block
  -> quality estimation     (reference-free score)                 low: escalate
  -> model judge            (error typology, on a sample)          major: to a person
  -> human review of the residual
  -> merge
```

The economics explain the order. Deterministic checks cost almost nothing and run in milliseconds. Research/04 reports that they catch about eighty percent of breakages; the figure comes from the synthesis of several deep-research outputs rather than a measured study, so treat it as an order of magnitude. Judges cost tokens and time, so the same source advises spending them only on strings that already pass, which keeps judge cost to roughly five to fifteen percent of translation spend. People cost the most, and the gate exists to spend their attention on what only they can judge.

The toolkit design implements the same three layers over its canonical catalog: deterministic linters always, quality estimation optionally, a sampled judge optionally, and then human confirmation in the review tool. The details of estimation and judging belong to Part 6, in [608. Quality estimation and judges](../6-machine-translation/608-quality-estimation-and-judges.md). This chapter is about the gate as a process: what each layer is allowed to decide.

## The deterministic layer

The deterministic layer compares tokens. It does not read language. Within that limit it is exact, and its findings can block a build without argument. The FontLab writing guide lists the checks a script runs before any person reads a translation:

- missing or empty targets, and targets identical to a translatable source
- the placeholder set, order constraints, and `%n` in every plural form
- tag and markup counts, escapes, leading and trailing whitespace, ellipses
- mnemonic count per label and duplicate mnemonic letters per context
- a length ratio far outside the language's expected range, and targets longer than the source in panels with a length cap
- two sources in one context sharing one target, and one source with two targets across the catalog
- core-memory terms present in the source and absent from the target in any inflected form
- a target that reintroduces a term the core memory retired
- non-translatable strings that changed: tags, glyph names, paths, identifiers
- diacritics not in NFC, and presentation-form ligatures

Several of these are terminology checks rather than syntax checks, and they only work because the project keeps its terms in a memory the checker can read. Part 4 describes that memory.

The syntax checks need a parser for the actual message format, not a regular expression that looks roughly right. vexy-localizzy's content checks default to Qt syntax: exact multiplicity of `%1`, `%L1`, `%n` and `%Ln`, ampersand mnemonics, and ordered HTML tags with protected attributes. Other syntaxes are chosen explicitly. Python brace fields are parsed with Python's own formatter, and C printf formats are checked by calling GNU `msgfmt`, with a missing tool treated as an error rather than a pass.

```python
from pathlib import Path

from vexy_localizzy.formats import ts
from vexy_localizzy.qa import TextPolicy, check_text
from vexy_localizzy.qa.catalog import check_catalog

check_text("Delete %1 glyphs?", "%1 Glyphen löschen?",
           policy=TextPolicy(), unit_key="demo")      # []
check_text("Delete %1 glyphs?", "Glyphen löschen?",
           policy=TextPolicy(), unit_key="demo")      # one PH-MISMATCH, critical

catalog = ts.load(Path("fontlab_de.ts"))
findings = check_catalog(catalog, required_plural_forms=("0", "1"))
```

The catalog check visits every active message with a nonblank source, including untranslated ones, and every plural and length variant. It requires the caller to state the target language's native plural positions and never substitutes CLDR categories for Qt's integer positions. Part 3 and Part 5 explain why those two plural systems differ. The last deterministic check is the native compiler: a Qt catalog is not accepted until `lrelease` compiles it.

The protocol for placeholders in machine translation, which uses these checks to repair engine output, is in [606. The placeholder protocol](../6-machine-translation/606-the-placeholder-protocol.md).

## Block, escalate or pass

A gate needs a policy for each kind of finding. Research/05 states one that the other sources share:

| Finding | Examples | Action |
|---|---|---|
| Hard failure | Broken placeholder, invalid XML, missing plural form, dropped tag | Block the job |
| Semantic concern | Low estimation score, a major accuracy issue from a judge | Escalate to a person |
| Minor warning | Fluency or style preference | Merge if the release is low-risk |

The spec's `qa` command expresses this as a threshold, `--fail-on critical` by default, tightened to `major` or `any` where the release warrants it. vexy-localizzy's translation cache uses its validator the same way: output with a major or critical finding is rejected before it is cached, and again when the cache is reopened, so a rule added later also applies to old results.

Two findings in vexy-localizzy deliberately do not fit the table. `TARGET-UNCHANGED` reports a target identical to its source, and `SOURCE-MARKUP` reports a defect already present in the source. Neither blocks, and neither approves. A product name that stays *FontLab* in every language is correct; a German label left in English by accident is not; the check cannot tell them apart, so it leaves the finding visible for review.

## Noise, and what to do about it

Every rule has false positives, and a gate that cries wolf gets ignored. Research/04 suggests tracking the false-positive rate of each check and disabling checks above about ten percent, naming the unchanged-translation check for brand names as the usual offender. The FontLab writing guide disagrees about the remedy: it says to tune rules per project, because "a noisy rule gets switched off and then catches nothing", and to preserve the reason for each exception so that the next run does not silently suppress a different defect. The toolkit design takes a middle course, with per-message ignore markers stored in the unit's notes and a configuration list of disabled checks.

The FontLab position is the safer default for a small catalog with a known vocabulary. A per-message exception with a reason keeps the rule alive for every other message. Disabling a rule catalog-wide is appropriate when it is wrong for a whole language, such as a punctuation rule written for Latin script applied to CJK text, which is the other example research/04 gives.

Judges are noisier than linters. Research/04 reports false-positive rates of fifteen to twenty-five percent for uncalibrated model judges and recommends temperature 0, structured output, a versioned model and prompt, and calibration against a golden set of about 200 segments that people have scored. It also gives a rule for replacing a model: when the human approval rate for a given pair of locale and model drops below about seventy percent. These figures are the synthesis's recommendations, not measurements from this project.

## The residual, and a worked example

The residual is what the gate leaves for people. The research synthesis sizes it at five to ten percent of strings in a mature pipeline. The FontLab review sized it differently for its first pass, because every German message was reviewed directly, as chapter [702](702-continuous-localization.md) describes. What the gate contributed there was not a smaller residual but a safer one: every change a reviewer accepted went through the same checks before it reached the catalog.

The verification recorded after the German consistency review and the founder's review shows what a deterministic audit covered and what it did not:

| Check | Result recorded |
|---|---|
| Review IDs audited | 960 |
| Recorded concerns checked | 27 |
| Repeated-source groups checked | 108, of which 7 intentionally differ by meaning or context |
| Literal syntax, plurals, composed labels, mnemonics | Pass |
| Native validation and Qt 5.15.19 compilation | 10,587 finished messages per catalog (the September 2026 review; later pulls count 10,474 and then 10,484 messages) |

The same record states the limit plainly: these checks "do not establish GUI pixel fit or physical keyboard behavior". Pixel fit belongs to the running application, which chapter [706](706-pseudo-localization-and-layout.md) and Part 5 cover.

The founder's update of 29 September 2026 shows the residual doing its job on scripted changes. The Polish terminology update was applied by rules: ordered literal replacements and two case-aware families that changed stems and adjusted agreement. The rules passed the validator and `lrelease`, and a scan found no retired term left. An independent review pass then found three defects the gate could not see: a rule that was not idempotent and doubled a word on a second run, a genitive plural that the stem pattern missed in 20 strings and 4 help passages, and one wrong reflexive phrase. All three were fixed and verified again. The gate proved the catalog was well formed. A second, independent reading was needed to show that it was also correct Polish.

That is the division of labor to design for. The FontLab guide puts it in one sentence: automated checks compare tokens, and they cannot approve language.

## Sources

- [docs/quality.md](../8-toolkit/quality.md) and [docs/translation.md](../8-toolkit/translation.md) in the vexy-localizzy repository, and its `src/vexy_localizzy/qa/` package
- [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/) in the vexy-fontlab-writing-styleguide repository
- The review ledger directory README and the work log of the FontLab localization project (the 29 September update)
