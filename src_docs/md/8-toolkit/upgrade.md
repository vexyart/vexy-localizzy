---
this_file: src_docs/md/8-toolkit/upgrade.md
---
# Upgrading a Qt catalog

When the code changes, `lupdate` produces a FRESH `.ts` file with the messages
the code now contains. The reviewed translations live in the APPROVED catalog.
`upgrade` ports APPROVED's translations onto FRESH and writes three files:

- **NEW**: FRESH's bytes, with only the messages that changed re-rendered in
  FRESH's own style.
- **RETIRED**: the APPROVED messages nothing used, as a valid TS file.
- **Report**: JSON with one outcome per FRESH message.

```sh
localizzy upgrade FRESH.ts APPROVED.ts --out NEW.ts --retired RETIRED.ts \
    [--report NEW.ts.upgrade.json] [--target de] \
    [--direct-memory a.tmx,b.tmx] [--glossary-memory core.tmx] [--memory-lang es-419] \
    [--glossary-status approved,do-not-translate] [--finish-on id,context] \
    [--fuzzy-threshold 0.92] [--relocated-finished] \
    [--no-engine | --endpoint URL --model M [--fallback-models a,b] [--api-key-env VAR] [--cache PATH] [--temperature 0.2]]
```

With an engine, the cache defaults to `OUT_DIR/.localizzy/translation-cache.sqlite`,
the same file and engine identity that `translate` uses.

`lupdate -ts APPROVED.ts` also merges, but it rewrites the file in place. It
writes no retired file and no report, and it cannot use memories.

## Identity

A message's identity is `message/@id` when present. Otherwise it is
(context, source, comment). Locations never count.

- If a FRESH id does not occur in APPROVED, the FRESH message falls back to the
  key match against APPROVED messages without an id.
- Duplicate identities within one file pair in document order.
- An id match whose source or comment changed is never `exact`. The id pins the
  pair: it becomes `fuzzy_exact_loose` when the loose forms are equal, and
  `fuzzy_similar` otherwise. No threshold applies, and the similarity is
  recorded.

## Tiers

Active FRESH messages have a non-empty source and are not vanished or obsolete.
Each one gets exactly one category. The tiers run as global passes in the order
below. Within a pass, messages are handled in document order. An early
message's fuzzy pairing therefore cannot take a later message's exact partner.

| # | Category | Rule | NEW state |
|---|---|---|---|
| 1 | `exact` / `exact_unfinished` | identity match, same numerus, APPROVED has text | APPROVED's state |
| 2 | `shape_changed` | identity match, numerus differs | engine, with APPROVED's text as an example |
| 3 | `plural_count_changed` | identity match, APPROVED's form count differs from the target's | APPROVED's forms in the available slots, unfinished |
| 4 | `memory_id` / `memory_context` | direct-memory hit of class `id` or `context` | finished if the class is in `--finish-on` |
| 5 | `relocated` | same source and comment, other context, exactly one candidate | unfinished (`--relocated-finished`: APPROVED's own state) |
| 6 | `fuzzy_exact_loose` | same context, `loose()` equal, exactly one candidate | unfinished, with `<oldsource>` |
| 7 | `fuzzy_similar` | same context, best similarity ≥ threshold and at least 0.02 ahead of the runner-up | unfinished, with `<oldsource>` |
| 8 | `memory_term` / `memory_source` | whole-string glossary term, then direct-memory `source` hit | finished if the class is in `--finish-on` |
| 9 | `machine` | engine translation; each batch prompt carries only its own glossary terms | unfinished |
| 10 | `pending` / `untranslated` | engine failed / no engine | unfinished, empty |
| none | `excluded_empty` | empty source | FRESH bytes untouched |
| none | `excluded_vanished` | FRESH message is vanished or obsolete | FRESH bytes untouched |

- Tiers 1, 3, 5, 6 and 7 consume their APPROVED candidate, so no APPROVED
  message is ported twice. When a port would drop reviewed plural forms,
  because APPROVED has more forms than the target language, the candidate is
  reserved instead of consumed: NEW gets the forms that fit, unfinished, and
  RETIRED keeps the whole APPROVED message. Tier 2 reserves its candidate: it is neither ported
  nor offered to later tiers, and it ends up in RETIRED. Memory tiers consume
  nothing.
- Tiers 5 to 7 draw on unconsumed, active APPROVED messages that have text and
  the same numerus flag.
- An identity match whose APPROVED translation is empty consumes the candidate
  and skips tiers 5 to 7. The message then goes to the memory tiers, the
  engine or `pending`.
- A `shape_changed` message keeps its category whether or not the engine
  fills it. The report's `filled` field says which.
- Tier 10 writes an empty translation even if FRESH already carried text there.
  FRESH never owns translations.
- `loose()` applies NFC, collapses whitespace, turns `...` into `…`, and drops
  trailing `:`, `…`, `.` and spaces. It also drops single `&` accelerators,
  maps `%1`, `%L1`, `%n` and `%Ln` to `%#` and `{name}` to `{#}`, and casefolds.
  `similarity()` is difflib's ratio over the two loose forms.
- The engine step reuses `translate_catalog`, including its cache, batching and
  content QA.
- Every numerus message uses the target language's Qt form count, in ports,
  empty slots and engine output alike. FRESH's own slot count is used only when
  Qt has no rule for the target. lupdate output without a `language` attribute
  has 2 slots, which says nothing about the target.
- `filled` is true only when every `numerusform` and `lengthvariant` of the NEW
  translation has text. A plural with one empty form counts as unfilled.

## Element ownership

NEW starts from a copy of the FRESH `<message>`.

| Element | Owner |
|---|---|
| `@id`, `@numerus`, `<location>`, `<source>`, `<comment>`, `<extracomment>` | FRESH |
| `<translation>` with `@type`, `<numerusform>`, `<lengthvariant>`, byte refs | APPROVED, copied whole |
| `<translatorcomment>` | APPROVED, if FRESH has none |
| `<userdata>`, `<extra-*>` | APPROVED, if FRESH lacks the same tag |
| `<oldsource>`, `<oldcomment>` | APPROVED's source or comment, for tiers 5 to 7, when it differs |

- Inserted children follow Qt's order: `location`, `source`, `oldsource`,
  `comment`, `oldcomment`, `extracomment`, `translatorcomment`, `translation`,
  `userdata`, `extra-*`.
- A message is re-rendered only when its canonical XML changed. Upgrading a file
  against itself returns identical bytes.
- `<TS language>` takes APPROVED's raw value (for example `de_DE`), or
  `--target` when given. Both files must have the same `sourcelanguage`.

## RETIRED

RETIRED holds two kinds of APPROVED message: active messages nothing consumed,
and messages that were already vanished or obsolete.

- Messages are grouped by context in APPROVED order, with APPROVED's root
  attributes.
- Relative locations are resolved to absolute ones with explicit filenames.
  The rule matches Qt's TS reader: the filename carries over from the previous
  location, and `+N` is added to that file's running counter. An absolute line
  does not reset the counter.
- The resolution matches `lconvert -locations absolute` on all 10,587 messages
  of a real FontLab catalog, and on a synthetic mixed file in
  `tests/fixtures/upgrade`.
- Each message keeps its translation type, so harvesting RETIRED into a memory
  still picks up its finished translations.
- If nothing retires, the file is still written as a valid TS with no contexts.

## Report (`localizzy-upgrade/1`)

| Field | Content |
|---|---|
| `fresh`, `approved`, `out`, `retired` | `path`, `sha256`, `messages` |
| `target_lang` | the language written to NEW |
| `memories` | `summary()` of each memory, tagged `role`: `direct` or `glossary` |
| `options` | `UpgradeOptions`, plus whether an engine ran |
| `counts` | one key per category, plus `retired_active`, `retired_obsolete` and `unfilled` |
| `messages` | `fresh_ordinal`, `context`, `source`, `category`, `state` (`finished`, `unfinished` or `untouched`), `filled`, `approved_ordinal`, `approved_source` (tiers 5 to 7), `similarity`, `memory`, `tuids`, `glossary_terms`, `model` |
| `retired_ordinals` | the APPROVED ordinals written to RETIRED |
| `invariants` | `every_fresh_classified`, `approved_consumed_or_retired` |

`upgrade()` writes nothing unless both invariants hold. The CLI writes the
report to `OUT.upgrade.json` unless `--report` is given.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | every active message has text in NEW |
| 1 | at least one active message is empty or partly empty in NEW (`pending`, `untranslated`, an unfilled `shape_changed`, or a plural with an empty form) |
| 2 | usage error: a missing file, an output that is also an input, different source languages, a bad option, or no engine and no `--no-engine` |
| 3 | an engine was requested but the `translation` extra is not installed |

Fire spells the flag `--no-engine` or `--no_engine`. It reads `--noengine` as
`engine=False`, which this command does not accept.

## Python API

```python
from vexy_localizzy.upgrade import UpgradeOptions, upgrade, upgrade_ts

result = upgrade_ts(fresh_bytes, approved_bytes, direct=memory, glossary=terms,
                    cache=cache_or_None, options=UpgradeOptions(no_engine=True))
result.new_bytes, result.retired_bytes, result.report

report = upgrade(Path("fresh.ts"), Path("approved.ts"), out=Path("new.ts"),
                 retired=Path("retired.ts"), report=Path("new.upgrade.json"))
```
