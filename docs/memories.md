---
this_file: docs/memories.md
---
# Translating with memories

`localizzy translate` fills a catalog from what is already known before it asks
a model. Each eligible message is decided in this order:

1. **kept**: the catalog is already in the target language and the message has
   a complete translation that passes QA;
2. **memory**: a direct-memory or glossary hit that passes the QA gate;
3. **engine**: a validated, cached model batch;
4. **pending**: no engine was configured, or no model returned a valid result.

```sh
localizzy translate app_de.ts --target de --out app_de.new.ts \
    --direct-memory de-fontlab-ui.tmx --glossary-memory de-core.tmx --memory-only
```

The Python entry point is `vexy_localizzy.translate.translate_file`.

## Direct memory

A direct memory holds reviewed messages of the same product as TMX 1.4. Each
TU has the tuid `Context|Source[:form]` and the props `x-context`, `x-comment`,
`x-numerus-form` and, optionally, `x-message-id`.

`localizzy tm build-ui CATALOG OUT --exclude-memory core.tmx` builds one from a
finished TS catalog. Every numerus form gets its own TU with `x-numerus-form`,
even in one-form languages such as Chinese. The target tag is the catalog's
`language` (or `--lang`), never the glossary's. A message is left out only when
the glossary's whole-string term tier would fill it: a plain message whose
source equals a term after the tier's own normalization, and whose term
rendering passes the accelerator and placeholder checks. `&Kerning`,
`Kerning %1` and plural messages therefore stay in the project memory.

Sources match verbatim. Only Unicode NFC and CRLF-to-LF normalization apply, so
case, spacing, punctuation, `&` accelerators and placeholders all count. Among
the TUs with the same source, the match classes are:

| Class | Condition | Written as (default) |
|---|---|---|
| `id` | `x-message-id` equals the message's TS `id` | finished |
| `context` | same context and comment | finished |
| `source` | every context gives the same target | unfinished |

Targets that disagree give no hit and a `MEMORY-CONFLICT` finding. A numerus
message needs TUs for exactly forms `0` to `n-1`, where `n` is the target
language's Qt form count. Other coverage gives a `MEMORY-PLURAL-SHAPE`
finding. Messages with length variants never hit. With several files, a higher
class wins, and for an equal class the first file listed wins.

## Glossary memory

A glossary TMX has the tuids `term:<id>` with the props `x-term-id`,
`x-translatable` and `x-status`. Its terms serve two purposes:

- **Prompt terms.** Each engine batch gets only the terms that occur in its
  messages, matched on word boundaries after tags, single `&` accelerators and
  placeholders are removed. At most 60 terms are sent, longest first. They are
  sorted by source, so the same batch always has the same cache key. A
  do-not-translate term maps to itself.
- **`term` hits.** A message whose whole text is a term, ignoring case, tags
  and accelerators, takes the term's rendering. If the label starts with a
  capital letter and the term does not, the first letter is capitalized.

By default only `approved` and `do-not-translate` terms are used. Pass
`--glossary-status approved,proposed,do-not-translate` to include proposed ones.

Precedence between the two memories is `id` > `context` > `term` > `source`.
`--finish-on` picks the classes that are written finished; the default is
`id,context,term`. The other classes are written unfinished (Qt
`type="unfinished"`) for review.

## The QA gate

Before a memory hit is used, every form goes through `qa.check_text` with the
Qt placeholder policy. A major or critical finding, such as a missing `%1`, a
changed tag or a lost accelerator, drops the hit and records
`MEMORY-QA-REJECT`. The next candidate is then tried; if none is left, the
message goes to the engine. An unchanged target, such as `Größe` for `Größe`,
is only a minor finding and does not block.

## Language matching

Catalog tags such as `de_DE` or `es_MX` rarely equal memory tags such as `de` or
`es-419`. The memory language is the exact canonical tag if present. Otherwise
it is the unique closest variant with the same primary language, by
`langcodes.tag_distance`, among the variants that:

- use the same script once both tags are maximized, so `zh-Hans` never answers
  `zh_TW` and `sr-Latn` never answers `sr_Cyrl`;
- do not cross Brazilian and European Portuguese, so `pt-BR` never answers
  `pt_PT`, and bare `pt` counts as Brazilian;
- are at distance 4 or less, so `de` answers `de_CH` and `es-419` answers
  `es_MX`, but `es-ES` does not answer `es_MX` and `en` does not answer `en_GB`.

The same rule applies when the memory has only one variant of the language. A
tie or no acceptable variant is a configuration error; pass
`--memory-lang es-419` to choose explicitly. Catalogs such as `zh_HK` with a
`zh-Hant` memory, or `en_GB` with an `en` memory, now need `--memory-lang`.
TMX files tagged bare `pt` are read as Brazilian. If they hold European
Portuguese, re-extract them (the extractors now write `pt-PT`) or pass
`--memory-lang pt`.

`--target de` counts as the same language as a `de_DE` catalog. The catalog
keeps its own tag, and its complete translations are kept, unless you pass
`--nokeep-existing` (or `--keep-existing=False`). An existing translation that
fails QA, or is only partly filled, is left exactly as it is and reported as
`KEPT-QA-FAIL` or `KEPT-INCOMPLETE`. For a new language, only TS catalogs can be
prepared. The target's plural count comes from Qt's numerus table, or from
`--plural-count`.

`--out` may be left out only when a TS catalog keeps its language, in which
case the input is overwritten. A different language never overwrites the input.

## Provenance

Every run writes a JSON report (schema `localizzy-translate/1`) to `--report`,
or by default to `OUT.localizzy.json`. It holds:

- the input digest and the language pair;
- the memory files with their SHA-256 and TU counts;
- `counts`: `kept`, `memory_id`, `memory_context`, `memory_source`,
  `memory_term`, `engine`, `pending` and `excluded`, which sum to the number of
  messages, plus `memory_rejected_qa` and `memory_conflict`;
- one row per message with its origin, match class, memory file, TU ids,
  glossary terms, requested and reported model, and request digest;
- all findings, and `ready`.

`--provenance=extra` also writes an
`<extra-localizzy-origin>memory:de-fontlab-ui.tmx#Menu|Save;match=context</extra-localizzy-origin>`
element into each memory- or engine-filled TS message. Qt keeps `extra-*`
elements as message extras. The default is the sidecar only, so shipped
catalogs carry no extra diff.

## Engine and cache

`--endpoint URL --model M [--fallback-models a,b]` sends the remaining messages
through abersetz to an OpenAI-compatible endpoint. The API key is read from the
variable named by `--api-key-env` (default `OPENAI_API_KEY`). Batches are cached
in `--cache` (default `.localizzy/translation-cache.sqlite` next to the output).
The cache key includes the endpoint, the abersetz transport version, the
temperature, the QA policy and the full batch, including its glossary. A
repeated run is served from the cache. Models are tried in order. See
[translation](translation.md) for retries, cooldowns and validation.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Every eligible message has a translation or candidate. |
| 1 | Some messages are still pending (for example after `--memory-only`). |
| 2 | Usage or configuration error: no `--endpoint` without `--memory-only`, a missing `--out`, an unknown match class, an unmatched memory language. |
| 3 | The `translation` extra is not installed. |

List flags take comma-separated values, for example `--direct-memory a.tmx,b.tmx`.
Repeating a flag keeps only its last value.
