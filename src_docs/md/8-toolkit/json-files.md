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
    --endpoint https://api.openai.com/v1 --model MODEL
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
finding is rejected as a whole and tried again on the next run. Output is a
draft for review, like any engine output.

## Resume and provenance

The output file is written only when every item is translated. Until then the
finished items wait in `<out stem>.partial.json` beside it, rewritten after
every accepted batch; the output is left untouched and the command exits 1.
Ctrl+C cancels the queued batches, keeps the partial file and exits 130. Run
it again to request only what is missing. An output whose path, partial file or
sidecar would overwrite an input is refused.

A complete run also writes `<out stem>.localizzy.json`: the source file name,
the model, and for every English key the SHA-256 of its English text (the
title included in titles mode), the model, the state and the QA findings.
Resume goes by English key, never by position. An item whose English text
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
