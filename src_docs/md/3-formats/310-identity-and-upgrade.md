---
this_file: src_docs/md/3-formats/310-identity-and-upgrade.md
---

# 310. Identity and upgrade: matching messages across versions, retired strings, fresh catalogs

Software is localized in versions. Esselink (2000) observed that most localization projects are updates to a previous version of a product, and that translation often starts while the source is still changing, so vendors process several updates before the final one. Continuous delivery made the updates smaller and more frequent; it did not change the question each one asks. The code now contains a new set of messages. Which of them are the messages that were already translated and reviewed, which are near relatives, and which are new? And what happens to the reviewed translations that no longer match anything?

This chapter treats that question as a problem of identity. It describes how each format identifies a message, the classic ways of carrying translations forward, and the upgrade design the FontLab project adopted, which separates extraction from merging and keeps every reviewed translation it cannot place.

## What makes a message the same message

Each format answers the identity question differently, and the answer decides what survives an edit to the English text:

| Format | Identity | A source typo fix creates |
|---|---|---|
| Qt TS | explicit `id`, else context, source and disambiguation | a new message |
| Gettext PO | `msgctxt` and `msgid`, plus `msgid_plural` for plurals | a new message |
| XLIFF | the unit `id` | nothing new, if the id is stable |
| Android, i18next, Apple | the resource name or key path | nothing new |
| TMX | `tuid`, or the source text for matching | a miss in exact lookup |

Formats keyed by source text, TS and PO, make every English edit a new message. Formats keyed by a stable name keep the translation attached but hide the change: the German text still describes the old English. The research on web localization states the trade-off from the key-based side. Structured keys survive content rewrites and let a translation management system keep history, while natural-language keys are readable but brittle, since any source edit decouples them from their translations and translation memory has to recover the link. Neither choice removes the work. One makes the upgrade find the old translation; the other makes the review notice that the English moved.

The FontLab guide adds a rule that no identity scheme can enforce: a source change that alters the behavior, values or audience of a message reopens review even when the words match. Identity says which translation to carry forward. It does not say the translation is still right.

## Two classic ways to carry translations forward

Esselink describes the choice by size. If version 3.2 of a resource file adds ten words to version 3.1, compare the two sources, keep the translated 3.1 file and paste in the new translations. If 20 percent of the text changed, start from the 3.2 file and import as many translations as possible from 3.1, so that the unchanged 80 percent is pretranslated automatically. He adds that software localization tools could carry over hot keys and dialog resizing along with the text, and that a vendor receiving many updates may do better to accumulate them and process them in a batch.

The Qt toolchain automates the second approach inside `lupdate`. Given an existing `.ts` file, `lupdate` keeps translations whose messages still exist, marks messages that disappeared as vanished or drops them with `-no-obsolete`, and uses heuristics to carry translations across small source changes ([chapter 302](302-qt-ts.md)). Gettext's `msgmerge` does the same for PO with fuzzy matching ([chapter 303](303-gettext-po.md)).

Both tools merge in place. The vexy-localizzy documentation lists what that costs a reviewed catalog: `lupdate -ts APPROVED.ts` rewrites the file, writes no retired file and no report, and cannot use memories. For a single developer that is convenient. For a catalog of ten thousand reviewed messages, it means nobody can say afterwards which translations were matched exactly, which by a heuristic, and which reviewed translations disappeared.

## An upgrade with three outputs

The FontLab design keeps `lupdate` as the extractor and moves the merge into a separate step. `lupdate` writes a FRESH catalog containing exactly the messages the code now has. The reviewed translations live in the APPROVED catalog. The `upgrade` command ports APPROVED's translations onto FRESH and writes three files: NEW, which is FRESH's bytes with only the changed messages re-rendered; RETIRED, a valid TS file holding every approved message that nothing used; and a JSON report with one outcome per FRESH message.

Every active FRESH message gets exactly one category. The categories are tried as global passes in a fixed order, so an early message's fuzzy pairing cannot take a later message's exact partner:

| Order | Category | Rule | Written as |
|---|---|---|---|
| 1 | `exact` | same identity, same plural shape, APPROVED has text | APPROVED's state |
| 2 | `shape_changed` | same identity, plural flag changed | engine, with the old text as an example |
| 3 | `plural_count_changed` | APPROVED has a different number of forms than the target needs | the forms that fit, unfinished |
| 4 | `memory_id`, `memory_context` | a direct-memory hit by id or context | finished if allowed |
| 5 | `relocated` | same source and comment in exactly one other context | unfinished |
| 6 | `fuzzy_exact_loose` | same context, equal after normalization | unfinished, with the old source |
| 7 | `fuzzy_similar` | same context, similarity at or above the threshold and clearly ahead of the runner-up | unfinished, with the old source |
| 8 | `memory_term`, `memory_source` | a whole-string glossary term, then a direct-memory source hit | finished if allowed |
| 9 | `machine` | engine translation | unfinished |
| 10 | `pending`, `untranslated` | engine failed, or no engine | unfinished, empty |

The normalization in tier 6 is spelled out, because it decides what counts as the same string. It applies Unicode NFC, collapses whitespace, turns three dots into an ellipsis, drops trailing colons, ellipses, periods and spaces, drops single `&` accelerators, maps Qt placeholders `%1`, `%L1`, `%n` and `%Ln` to one token and `{name}` to another, and folds case. Tier 7 compares these normalized forms with a similarity ratio; the default threshold is 0.92, and the best candidate must lead the runner-up by at least 0.02, so that a choice between two near-equal candidates goes to a person instead of a coin toss.

Several rules protect reviewed work. An approved message consumed by a tier is ported once and only once. When porting would drop reviewed plural forms, because the target needs fewer forms than APPROVED has, the candidate is reserved: NEW gets the forms that fit, marked unfinished, and RETIRED keeps the complete original. FRESH never owns translations; tier 10 writes an empty translation even if the fresh file carried text, because text in a fresh extraction has not been reviewed. And the command writes nothing unless two invariants hold: every FRESH message was classified, and every APPROVED message was either consumed or retired.

## Retired strings are kept, not deleted

A retired message is a reviewed translation the current code does not use. It may belong to a feature that was removed, a string that was rephrased beyond recognition, or a context that was renamed. The last case is the reason to keep them: a renamed class moves every one of its strings to a new context, and a person reviewing the RETIRED file can see that at once.

RETIRED is written as a valid TS file grouped by context in APPROVED's order, and each message keeps its translation state, so harvesting the file into a memory still picks up its finished translations. Relative locations are resolved to absolute ones with explicit file names, using the rule Qt's own reader applies; the documentation records that this resolution matches `lconvert -locations absolute` on all 10,587 messages of a real FontLab catalog. The fl10n project stores the files by language and by the two catalog revisions they bridge, as `retired/fontlab_<code>-<fresh>-<approved>.ts`.

## Worked example: the German catalog

The first real run of the upgrade used German, with no memories and no engine, and left the project's own catalogs untouched. The command has this shape:

```sh
localizzy upgrade fresh_de.ts approved_de.ts --out de.ts --retired de-retired.ts --no-engine
```

| Measurement | Result |
|---|---|
| FRESH messages | 10,474 |
| APPROVED messages | 10,587 |
| `exact` | 10,448 |
| `fuzzy_similar` | 11 |
| `untranslated` | 15 |
| Retired | 128 |
| Running time | about 0.9 seconds |

The eleven fuzzy matches were typo fixes in the English, such as *Horizonal* corrected to *Horizontal*. They were ported as unfinished with the old source attached, so a reviewer confirms each in seconds instead of retranslating it. Two of the fifteen untranslated messages had text in the fresh file, and the command emptied it by design. Upgrading a catalog against itself returned identical bytes, which is the check that the command changes nothing it has no reason to change.

The exit code carries the result for automation: 0 when every active message has text in NEW, 1 when at least one is empty or partly empty, 2 for a usage error such as an output that is also an input. A pipeline can stop on 1 and hand the report to a translator. Later passes add the other tiers: with a direct memory and a glossary memory, tiers 4 and 8 fill messages from reviewed work in other catalogs, and with an engine, tier 9 drafts the rest. When the September 2026 corrections were synced, the corrected fresh catalogs became the approved catalogs, and 63 messages per language moved into RETIRED files. Nothing reviewed was lost; it moved to a file where a person can decide whether it is still needed.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 4, processing updates)
- `research/02-localizing-qt-cpp-applications.md` and `research/03-localizing-web-javascript-applications.md` in the fl10n repository
- `WORK.md` in the fl10n repository
- `README.md`, [docs/upgrade.md](../8-toolkit/upgrade.md), [docs/cli.md](../8-toolkit/cli.md) and `WORK.md` in the vexy-localizzy repository
- [localization/memories](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/memories/) in the vexy-fontlab-writing-styleguide repository
