---
this_file: src_docs/md/8-toolkit/vocabulary.md
---
# Vocabulary corpus

A vocabulary corpus is a small, dense set of reviewed strings for one domain:
menu commands, terms, messages with placeholders and plurals, and the same
English word in two senses. It is not a translation memory. It serves as a
reference for how strings should be keyed and annotated, as test fixtures with
known-good translations, and as a golden set against which a model or a prompt
is measured. A source checkout ships an example corpus of 200 typographic
entries in English, German, French and Japanese under `examples/vocabulary/`,
with a small browser viewer.

## Format

The corpus is one object keyed by message key. It is read from a `.json` file,
or from a JavaScript data file of the form `const name = {...};` with `//`
comments, which a static page can load directly.

```js
const vocabulary = {
  "menu.file.open": {
    "en": "&Open Font...",
    "de": "Schriftart &öffnen...",
    "context": "File menu action to open an existing font file"
  },
  "label.disambig.kern.verb": {
    "en": "Kern",
    "de": "Unterschneiden",
    "context": "Verb: adjust the space between a pair of glyphs"
  },
  "msg.selectedGlyphs": {
    "en": "{count, plural, one {# glyph selected} other {# glyphs selected}}",
    "de": "{count, plural, one {# Glyphe ausgewählt} other {# Glyphen ausgewählt}}",
    "context": "Status bar; count is the number of selected glyphs"
  }
};
```

An entry holds one field per language (codes of up to five characters, such as
`de` or `pt-BR`) plus `context`, or a single `translation` plus `context` for
metadata such as language names. The part of a key after `.disambig.` becomes
the disambiguation (`kern verb`). ICU plurals are parsed into categories, and
placeholders are detected as in any catalog. The first segment of the key is
its family (`menu`, `msg`, `vocab`), which `stats` counts.

## Commands

```sh
localizzy vocab stats corpus.js
localizzy vocab list corpus.js --locale de
localizzy vocab validate corpus.js --format sarif --out vocab.sarif
localizzy vocab export corpus.js --locale de --out vocab_de.json
localizzy vocab compare corpus.js --candidate candidate_de.json --locale de --min-exact 0.95
```

The corpus path is always explicit, and no command writes to it; edit the file
itself.

`stats` counts entries, families, placeholder kinds, plural and disambiguated
entries, and the entries that have each language. `list` prints one line per
entry: key, the text in `--locale` (or the source), context.

`validate` is a QA pass over the fixtures themselves: every entry must have a
context (`VOCAB-CONTEXT`), every ICU plural an `other` category
(`VOCAB-PLURAL`). It renders as `table`, `json` or `sarif` and exits 1 on any
finding, because a broken fixture quietly weakens every test that reads it.

`export` writes the corpus as canonical catalog JSON: a source-only catalog,
or a bilingual one with `--locale`. Other commands, and tests, read that file
like any catalog. With `--flat` it writes a plain `{key: text}` object instead
(the sources, or the `--locale` texts), the input of
[`translate_json`](json-files.md).

## The corpus as a golden set

`compare` scores a candidate, a catalog or a flat `{key: translation}` JSON
file, against the corpus references for one language. Only entries with a reference in that language count. The result
gives the total, the number and rate of exact matches, the keys the candidate
lacks, and every differing pair with both texts, so a run shows what changed
and not only a number. With `--min-exact`, a rate below it exits 1.

Messages are matched by key, so the candidate must keep the corpus keys. The
flat export and `translate_json` do that:

```sh
localizzy vocab export corpus.js --out en.json --flat
localizzy translate_json en.json de de.json --endpoint https://api.openai.com/v1 --model MODEL
localizzy vocab compare corpus.js --locale de --candidate de.json --min-exact 0.6
```

A round trip through Qt TS does not work: it replaces the keys with Qt's
context and source, and every entry then counts as missing.

Run the comparison whenever the model, the prompt or the style guidance
changes. An exact-match rate is a blunt measure, since many differences are
legitimate alternatives, which is why the differing pairs are listed for a
person to read. A falling rate is the signal to look, not the verdict.
