---
this_file: src_docs/md/8-toolkit/json-files.md
---
# Translating JSON text files

Help panels, tips and similar files are not catalogs: they are flat JSON
objects of Markdown texts, with no context, plurals or Qt state.
`localizzy translate_json` translates them through an OpenAI-compatible
endpoint, checks every item, and writes the output only when it is complete.

```sh
localizzy translate_json help_en.json de help_de.json \
    --endpoint https://api.openai.com/v1 --model MODEL \
    --product "a font editor" --style-file style-de.md \
    --glossary-memory i18n/memories/de-core.tmx
localizzy translate_json tips_en.json de tips_de.json --titles \
    --endpoint https://api.openai.com/v1 --model MODEL --fallback-models OTHER
```

It needs the `translation` extra. SOURCE must be one JSON object whose values
are all strings.

## Two layouts

A **keyed** file maps a stable key to its text, and the output keeps the keys:

```json
{"kerning.help": "Use **Window > Kerning** to edit pairs.", "guides.help": "Drag from the ruler."}
```

A **titles** file uses the English title as its key, as a list of tips often
does. With `--titles` the keys are translated too, and the output's keys are
the translated titles in the source order. Two items that come back with the
same translated title are reported as `title_clashes`; the output is not
written, and the next run requests those items again.

## Requests and checks

Items go in small batches (`--batch-size`, default 5) over `--workers`
parallel requests (default 3), at `--temperature` 0.2. The instructions name
the source and target languages (`--source-lang`, default `en`), the product
(`--product`, default "a software application"), say to keep Markdown, HTML
tags, keyboard shortcuts, code and placeholders exactly, and to translate the
words of a menu path such as **File > Save** with the glossary, because the
interface is translated too. The style sheet from `--style-file` follows. From
`--glossary-memory`, each batch gets the terms of the selected statuses
(`--glossary-status`, default approved and do-not-translate) that its texts
mention.

A reply must return every item of the batch exactly once with non-blank text
(and title); anything else is retried, then the batch fails. Every item then
passes the text checks: markup and Qt placeholders as in
[content QA](quality.md), without accelerator checks because help text uses
`&` as prose, plus two Markdown checks: link targets must match the source and
inline code spans must keep their count. A batch with a major or critical
finding is rejected as a whole. Output is a draft for review, like any engine
output.

A text that several keys share is one item: it is requested once, under its
first key, and the translation is written under every key that has it. A key
added later with a text that is already translated takes that translation
without a request. With `--titles` the title is part of the item, so two
titles over the same text are two items.

`--fallback-models b,c` names further models, tried in that order after
`--model`, as in `localizzy translate`. The next model gets the request when
the one before it fails (an outage, a quota, a reply that stays malformed) or
its answer is rejected by the checks.

## Items that fail in their batch

One long article with heavy inline HTML can fail its markup check on every
attempt, and it takes its whole batch with it. So after the batches, every
item of a failed batch gets requests of its own, in three steps:

1. **Whole.** The item alone, in one request. Its batch neighbours usually
   pass here. An item that already went alone and was rejected skips this step.
2. **Paragraphs.** The text is split at blank lines and each paragraph goes
   in its own request. A `<pre>…</pre>` block is not sent: it stays as it is,
   untranslated. Blank lines and indentation are kept. In titles mode the
   title is one more piece.
3. **Masked.** A paragraph that still fails is sent with its markup replaced
   by numbered tokens: every HTML tag and comment, inline code span and
   Markdown link target becomes `[[1]]`, `[[2]]` and so on, and the
   instructions say that each token must appear exactly once. The markup is
   put back afterwards. A paragraph whose reply misses, repeats or invents a
   token is rejected.

The reassembled item then passes the same checks as any other item, or it is
rejected and waits for the next run. Only an answer that cannot be used leads
to the next step; while the provider is unavailable an item is tried alone
once and no paragraph requests are made. `--norescue` (or `--rescue=False`)
turns all of this off: the items of a failed batch then wait for the next run.

## Resume and provenance

The output file is written only when every item is translated. Until then the
finished items wait in `<out stem>.partial.json` beside it, rewritten after
every accepted batch; the output is left untouched and the command exits 1.
Ctrl+C cancels the queued batches, keeps the partial file and exits 130. Run
it again to request only what is missing. An output whose path, partial file or
sidecar would overwrite an input is refused.

A complete run also writes `<out stem>.localizzy.json`: the source file name,
the model (and `fallback_models` when there were any), and for every English
key the SHA-256 of its English text (the title included in titles mode), the
model that answered, the state, the QA findings and the `path` that filled
the item: `whole`, `paragraphs`, or `masked` when at least one paragraph
needed masking. Keys that share a text are all listed, with the same
provenance. Resume goes by English key, never by position. An item whose English text
changed is translated again; the others are kept. A translation found in an
existing output without a sidecar entry is kept as `adopted`; new ones are
`machine`. In titles mode an output without a sidecar can only be paired with
the English file by position, which is refused when their lengths differ.

| Exit | Meaning |
|---|---|
| 0 | Every item translated; output and sidecar written |
| 1 | Not complete; finished items are in the partial file |
| 2 | Missing endpoint or model, a missing or malformed file, a bad language tag or status |
| 3 | The `translation` extra is missing |
| 130 | Interrupted with Ctrl+C; the partial file keeps the finished batches |

The same files can then go through [editorial review](editorial.md) with
`--source-json`, and a flat [vocabulary](vocabulary.md) export becomes a
benchmark this way.
