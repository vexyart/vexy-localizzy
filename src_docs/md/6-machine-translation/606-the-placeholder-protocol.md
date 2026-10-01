---
this_file: src_docs/md/6-machine-translation/606-the-placeholder-protocol.md
---

# 606. The placeholder protocol: parse, instruct, validate, repair

Most translation errors cost a reader some understanding. A placeholder error costs the application its behavior. A Qt message that loses `%1` shows a sentence with a missing file name. A Python format string with a renamed field raises an exception at the moment the message is displayed. A broken closing tag spills formatting across the rest of a dialog. A plural form without `%n` tells the user that something happened to an unstated number of objects. None of these shows up when someone reads the target text in isolation, and all of them are easy for a model to produce while writing an otherwise good sentence.

This is the one class of error a pipeline can catch completely and mechanically. The 2026 research corpus calls the pattern mandatory and gives it four steps. This chapter explains each step, shows where a common validator goes wrong, and records a disagreement about what to do when repair fails.

## Four steps

1. **Parse.** Extract every placeholder, tag and accelerator from the source before anything is sent. The toolkit design stores this inventory on each unit of the canonical model ([307](../3-formats/307-the-canonical-model.md)), so nothing is parsed with ad hoc patterns at translation time.
2. **Instruct.** Tell the model what each token is and that it must survive: `%1` is a file name, `%n` is the count, `<b>` and `</b>` are markup. State which tokens may move. The instruction is a guide, not a guarantee.
3. **Validate.** Parse the returned text with the same parser and compare it with the source inventory. This is the step that matters; the other three exist to make it pass more often.
4. **Repair.** On a mismatch, ask again with the exact discrepancy stated, or refuse the result. Never write a string that failed validation into a catalog as a translation.

The research corpus adds that letting a capable model place tags itself works better than the older approach of stripping tags, translating plain text and projecting the tags back. That claim concerns the instruct step. It changes nothing about validation, which must run whichever way the model got there.

## Count tokens, do not compare sets

The research corpus offers a short Python validator that extracts placeholders with a regular expression per syntax and compares the *set* of tokens in source and target. It is a useful sketch and it has two defects that a Qt project will hit.

First, a set cannot see repetition. A source that uses `%1` twice and a target that uses it once have equal sets. Second, its Qt pattern, `%\d+`, finds `%1` but not `%L1` (the locale-aware form) or `%n` (the plural count), so a numerus string that loses its count passes. The example below reproduces both failures and the fix: a tokenizer that knows the Qt forms, and a comparison of counts rather than sets.

```python
import re
from collections import Counter

NAIVE = re.compile(r"%\d+")                # the research corpus's Qt pattern
QT    = re.compile(r"%L?(?:\d{1,2}|n)")    # %1 to %99, %L1, %n, %Ln

def same_set(pattern, s, t):
    return set(pattern.findall(s)) == set(pattern.findall(t))

def same_count(pattern, s, t):
    return Counter(pattern.findall(s)) == Counter(pattern.findall(t))

s, t = "Replace %1 with %2 in %1 and its components", "Ersetze %1 durch %2 in allen Komponenten"
print(same_set(NAIVE, s, t), same_count(QT, s, t))    # True False

s, t = "%n glyphs selected", "Glyphen ausgewählt"
print(same_set(NAIVE, s, t), same_count(QT, s, t))    # True False
```

vexy-localizzy's default Qt policy works this way: exact multiplicity of `%1`, `%L1`, `%n` and `%Ln` through a shared tokenizer, so losing one of two repeated tokens is an error. Numbered arguments may move, since Qt substitutes by number, and so may the mnemonic letter after `&`. A doubled `&&` is a literal ampersand, not a mnemonic.

There is a nuance the strict count hides. The FontLab message-contract guidance says that reordering or repeating a value can be valid when the parser permits it, while changing its identity or meaning is not. A translator who needs a value once where English uses it twice therefore has a legitimate case. Under a strict count, that case needs a reviewed exception or a changed source string, not a quiet override of the check.

## Each syntax has its own rules

Placeholders are not one syntax, and a validator that treats them as one will either miss errors or report false ones. The toolkit chooses a policy per catalog format, and per entry where the format says more:

| Format | What is checked | Notes |
|---|---|---|
| Qt TS | `%1`, `%L1`, `%n`, `%Ln` by count; `&` mnemonics; common HTML tags | numbered arguments and mnemonic letters may move |
| gettext PO | from each entry's flags: `c-format` through `msgfmt --check-format`, `python-brace-format` by comparing `{name}` fields, `qt-format` as Qt | an unflagged entry gets no placeholder check, as with `msgfmt` itself |
| i18next JSON | `{{name}}` | |
| Android XML | Java and C printf conversions through `msgfmt`, for strings that contain one | the research corpus notes Android's `<xliff:g>` wrapper for protected spans |
| XLIFF, TMX | the style detected in each unit's own source | XLIFF 2.1 marks inline codes as `<ph>` and `<pc>` |
| HTML fragments | ordered tags, protected attributes, valid nesting | `alt` and `title` text may be translated; attribute order and quote style may differ |

Two choices in that table are worth copying. The toolkit does not vendor its own printf parser; it delegates C printf checking to GNU `msgfmt`, the tool that defines the behavior, and treats a missing tool or a timeout as an error rather than a pass. And it runs a negative control, so that a malformed source format cannot silently switch the check off. A validator that passes because it could not run is worse than no validator, because it produces evidence of a check that did not happen.

Markup has its own edge cases. An empty visible translation fails even when every tag survived, because `<b></b>` is not a translation. Inside HTML, an ampersand in an attribute or a character entity does not introduce a mnemonic, so a check that counts `&` naively would report false errors in every link.

The gate does not only guard the engine. In vexy-localizzy's browser reviewer, both saving a draft and approving a message reject structural QA failures, so a reviewer who deletes a placeholder while rephrasing is stopped exactly as a model would be. Humans drop tokens too, usually while making a sentence read better.

The Python brace policy uses Python's own format-string parser, so field names, repeated fields, conversions and format specifications are all compared. The documentation warns against applying it to CSS or to ICU message syntax, which also use braces and mean something else.

## Repair or refuse

The sources agree that a failed string must not reach the catalog as a translation. They disagree about how hard to try before giving up.

The toolkit design re-prompts **once**, quoting the exact discrepancy. If the second answer is still wrong, it marks the unit `needs_review` and emits a critical finding.

vexy-localizzy allows **at most three attempts per model** for output that is malformed or rejected by the QA gate, then falls back to the next model in its ordered list. If every model fails, the batch is pending: nothing is written for it, completed batches stay cached, and a later run resumes. The validator runs again on cache hits, so a rule tightened after a response was cached still applies to it.

Both designs refuse to write a broken string, which is the requirement. The difference is cost and latency against the chance of a clean answer. A retry that quotes the discrepancy gives the model the one piece of information it lacked the first time. A string that fails repeatedly on the same token often points to a source problem instead, such as a placeholder whose role nobody explained, and further attempts at the same model will not supply the missing explanation.

Automatic repair by inserting the missing token is tempting and rarely safe. The pipeline knows that `%2` is missing, but not where in the German sentence it belongs. Appending it produces a string that passes validation and reads wrongly, which is the worst of both outcomes.

## What the gate cannot see

A placeholder check proves the tokens survived. It does not prove the message is complete or correct.

- **Plural coverage is a separate check.** A catalog-level check must visit every native plural and length variant and confirm the target language's required forms exist. vexy-localizzy's catalog check takes the exact native positions for the locale and never substitutes CLDR categories for Qt's integer plural positions ([505](../5-interface/505-plurals-in-practice.md)). The FontLab Polish catalog passed a three-form plural gate for exactly this reason.
- **Agreement around a placeholder** is linguistic. A check confirms `%1` is present; it cannot confirm that the adjective before it agrees with the noun a program will insert ([506](../5-interface/506-placeholders-and-agreement.md)).
- **An unchanged target** is reported as a minor finding, not blocked, because *Größe* for *Größe* or a product name can be correct. Approving it needs a reason on record.
- **A defect already in the source**, such as badly nested markup, is reported separately, so the translation is not blamed for it.

Accelerators sit halfway between the two worlds: the gate can count them, but choosing a letter that does not collide in its menu is a layout question ([504](../5-interface/504-mnemonics-shortcuts-and-keys.md)). Validation belongs in the deterministic first layer of the quality gate described in [704](../7-process/704-the-qa-gate.md), before any score or judge is consulted.

## Sources

- [docs/quality.md](../8-toolkit/quality.md), [docs/memories.md](../8-toolkit/memories.md), [docs/translation.md](../8-toolkit/translation.md) and [docs/review.md](../8-toolkit/review.md) in the vexy-localizzy repository
- [localization/message-contracts](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/message-contracts/) and [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/) in the vexy-fontlab-writing-styleguide repository
- The changelog of the FontLab localization project (the Polish plural and markup gates)
