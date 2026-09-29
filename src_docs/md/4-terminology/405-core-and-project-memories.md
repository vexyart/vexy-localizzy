---
this_file: src_docs/md/4-terminology/405-core-and-project-memories.md
---

# 405. Core and project memories: glossaries versus whole strings, and why a term lives in one place

A translation memory stores pairs of source and target text so that the work done once need not be done again. A glossary stores pairs of source and target terms so that the same concept gets the same word everywhere. Both can be written in TMX, both are consulted during translation, and teams routinely mix them up. This chapter separates the two jobs, shows how a toolkit uses each, and explains why a term must live in exactly one of them.

## Two kinds of reuse

Translation memory is old technology. Esselink (2000) describes it as a database of translated sentences, matched against new source text by segment, with a percentage score for near misses: a stored "To search for text" retrieved as a fuzzy match for "To search for and replace text", with the difference highlighted. The same chapter describes terminology tools as separate systems that store terms, equivalents, definitions and context, and that insert the approved term into the translation environment on lookup. In Esselink's workflow the project glossary is linked to the memory tool so that the translator sees both at once.

The distinction Esselink draws is the one that still matters. A memory reuses *text*. A glossary governs *words inside text*. A memory answers "have we translated this string before?" A glossary answers "how do we say this concept, in whatever sentence it appears?"

The FontLab localization keeps the two as separate files per language, both in TMX 1.4:

| | Core memory, `<code>-core.tmx` | Project memory, `<code>-fontlab-ui.tmx` |
|---|---|---|
| One unit per | glossary term | reviewed interface message |
| Unit id | `term:<id>` | `Context\|Source[:form]` |
| Maintained | by hand, by decision | generated from the reviewed catalog |
| Changes | slowly, with a recorded reason | with every review |
| Used as | a glossary: a hint for any sentence | a cache: a verbatim answer for one string |
| A language without a reviewed catalog has | a core memory | nothing yet |

### The core memory fixes concepts

The core memory holds one unit per glossary term, with the English term, the target term, the status, the English definition as a note and, where useful, a translator's note in the target language. A translation engine receives the relevant units as a glossary: the term must be rendered this way, inflected as the sentence requires.

The `vexy-localizzy` toolkit uses the core memory in two ways when it translates a catalog:

- **Prompt terms.** Each batch sent to a model gets only the terms that occur in its messages, matched on word boundaries after tags, single `&` accelerators and placeholders are stripped. At most 60 terms are sent, longest first, and sorted by source so that the same batch always produces the same cache key. A do-not-translate term maps to itself.
- **Term hits.** A message whose whole text is a term, ignoring case, tags and accelerators, takes the term's rendering directly, with the first letter capitalized if the label starts with a capital.

By default only approved and do-not-translate units are used. A proposed translation stays out of the prompt until someone approves it, which is the difference between a glossary and a list of guesses.

### The project memory recycles strings

The project memory holds one unit per reviewed message: `Menu|Save`, `DlgKerning|Pair`, or, for a plural message, one unit per numerus form. Its sources match verbatim; `vexy-localizzy` normalizes only Unicode NFC and line endings, so case, spacing, punctuation, accelerators and placeholders all count. Among units with the same source, a match is classified:

| Class | Condition | Written as by default |
|---|---|---|
| `id` | same message id | finished |
| `context` | same context and comment | finished |
| `source` | same source in other contexts, all with one target | unfinished, for review |

If units with the same source disagree, there is no hit and the toolkit reports a memory conflict. Between the two memories, precedence runs from `id` to `context` to `term` to `source`. A term hit ignores context and case, so a glossary *open* meant as an adjective could fill a menu verb *Open*; that is why term hits are written unfinished unless you ask otherwise.

```sh
localizzy translate app_de.ts --target de --out app_de.new.ts \
    --direct-memory de-fontlab-ui.tmx --glossary-memory de-core.tmx --memory-only
```

Every hit, from either memory, passes the same quality gate as a model draft: a missing `%1`, a changed tag or a lost accelerator rejects it, and the next candidate is tried.

## Why a term lives in one place

If *Kerning* appears as a source in both memories, the two answers can diverge. A reviewer changes the core memory; the project memory, generated from last month's catalog, still says the old word; and the next upgrade fills the string from the project memory because a verbatim match outranks a term. Two answers for one string is how a memory starts contradicting itself.

The FontLab data enforces the separation from both sides. The styleguide's `check_tm.py` fails the build when an English source of a core memory appears, compared without regard to case, in the same language's project memory. And when `vexy-localizzy` builds a project memory from a finished catalog, it leaves out exactly the messages that the glossary's whole-string tier would fill:

```sh
localizzy tm build-ui fontlab_de.ts de-fontlab-ui.tmx --exclude-memory de-core.tmx
```

The exclusion is narrow on purpose. `&Kerning` with its accelerator, `Kerning %1` with its placeholder, and every plural message stay in the project memory, because the term tier would not fill them correctly. Only a bare label identical to a term moves out.

## What a match is worth

A verbatim match in the same context is reused. Everything else is a proposal, and the FontLab memory guidance explains why in terms the older books would recognize.

**A fuzzy match is a draft.** Roturier (2015) shows four English sentences about *Save as* in the *File* menu. Three say the same thing in different words; the fourth shares most of the words and means something else. A character-based score ranks the fourth close to the first. The editing effort, Roturier notes, grows when segments differ in meaning rather than punctuation, and grows again in languages with case inflection, where the same English phrase needs a different ending as subject or object. German and Polish are such languages.

**A source match in another context is a proposal.** *Close* on a button and *Close* as the state of a path are different German words.

**A sentence match needs its neighbours.** Esselink (2000) observed that sentence-level segmentation yields more full matches than paragraph-level, but that those matches must be checked because the surrounding sentences may have changed. For help text, prefer a match whose neighbours also match.

**Only today's quality is worth reusing.** When an old translation is bad, retranslating costs less than repairing it. A memory that is not fed the final, corrected text goes stale.

## Keeping memories useful

Memories decay. Roturier (2015) recommends exporting metadata with each unit: creation date, the authors of source and target, and the number of times it was reused. That metadata is what lets someone prune a memory without rereading it. The FontLab practice regenerates the project memory from the reviewed catalog after every review, rather than editing it, so it cannot contain a string the catalog no longer has.

The core memory is edited only through the decision process ([chapter 410](410-ledgers-and-decisions.md)), and a changed decision is pushed into it the same day. After issue 146 changed 51 Polish terms, the core memory was updated, the Polish catalog and help were rewritten, and the project memory was rebuilt from the rewritten catalog. The order matters: the concept changes first, the strings follow, and the cache is regenerated last.

## A worked example: one label, two memories

A new FontLab build adds the message `MainWindow|Power Brush`. The German catalog is upgraded with both memories.

1. The project memory has no unit with this source in `MainWindow`, but it has `DlgBrushes|Power Brush` with *Power-Pinsel*. That is a `source` match: written unfinished, for review.
2. The core memory has the term `power-brush`, approved, *Power-Pinsel*. The whole label is the term, so it is also a term hit.
3. Precedence puts `term` above `source`. The string gets *Power-Pinsel* from the core memory, unfinished unless term hits are configured as finished.
4. The reviewer confirms it in the running application, and the next project memory build leaves this bare label out, because the term tier fills it.

The same message in Polish gets *Pędzel mocy* from the Polish core memory. Nothing in the project memory had to know that the Polish term changed in September 2026.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 11: translation memory tools, segmentation, fuzzy matching; chapter 12: reference materials)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 5.3: translation memory)
- `src_docs/md/localization/principles.md`, `src_docs/md/localization/memories.md` and `scripts/check_tm.py` in the vexy-fontlab-writing-styleguide repository
- `docs/memories.md` in the vexy-localizzy repository
- `CHANGELOG.md` in the fl10n repository
