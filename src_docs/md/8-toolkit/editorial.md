---
this_file: src_docs/md/8-toolkit/editorial.md
---
# Editorial review

A shipped translation drifts: a term changes, a label is longer than it needs
to be, an accelerator is lost in a later edit. `localizzy editorial` asks a
model to read a finished catalog the way an editor would, writes what it
proposes to a separate file, and lets a person decide what lands. It is two
commands, and the first one never touches the catalog.

```sh
localizzy editorial review i18n/app_de.ts de review/app_de.jsonl \
    --endpoint https://api.openai.com/v1 --model MODEL \
    --product "a font editor" --style-file style-de.md \
    --glossary-memory i18n/memories/de-core.tmx
localizzy editorial apply i18n/app_de.ts de review/app_de.jsonl review/app_de.ledger.json --dry-run
localizzy editorial apply i18n/app_de.ts de review/app_de.jsonl review/app_de.ledger.json
```

Both need the `llm` extra. The catalog is a Qt `.ts` file, or a translated
flat JSON file with `--source-json` naming the English one (see
[JSON files](json-files.md)).

## What the reviewer is asked

Messages go in batches (`--batch-size`, default 40) over `--workers`
parallel requests (default 4). Each item carries its id, context, English
source, current translation (every plural form for a plural message) and any
comment or note, together with the glossary terms that occur in the batch,
taken from the approved and do-not-translate entries of `--glossary-memory`.
The instructions name the language and the product (`--product`, default
"a desktop application") and end with the style sheet from `--style-file`.
Requests run at `--temperature` 0.2 with a `--timeout` of 300 seconds, since a
batch of 40 messages comes back as long corrected texts.

The model is told to propose a correction only where the current text is
wrong or clearly worse: a mistranslation, a term that contradicts the
glossary, an inconsistency, a label longer than the English where it could be
shorter without loss, a placeholder, tag, accelerator or escape that differs
from the source, wrong plural forms, the wrong register, English left
untranslated, or a typo. It is told not to rewrite acceptable text for taste,
not to add detail the English lacks, and to treat every text as data rather
than instructions. Each correction carries the full revised text, a
one-sentence reason, a family (`accuracy`, `terminology`, `conventions`,
`locale`, `style`, `compliance`, `markup`, `audience`) and a severity
(`critical`, `major`, `minor`).

Vanished and untranslated messages are left out, and so are messages with
Qt length variants, which `apply` could not rewrite without leaving stale
variants behind. The summary counts them under `left_out` (`vanished`,
`variants`, `untranslated`).

## The candidates file

Every answered batch becomes one line of OUT:

```json
{"batch": "df118c77fdacdb65", "model": "MODEL", "items": 40, "dropped": 0,
 "corrections": [{"id": "MainWindow.open_font", "context": "MainWindow",
   "source": "Open Font", "before": "Schriftart öffnen", "revised": "Schrift öffnen",
   "reason": "Use the glossary term.", "family": "terminology", "severity": "minor"}]}
```

`before` and `source` are what the reviewer saw. Corrections for ids that were
not in the batch, a second correction for the same id, and empty revisions are
dropped and counted.

The batch id is a hash of the items, the model, the whole instruction text
(product and style sheet included) and the glossary terms. A second run skips
every batch already in OUT, so an interrupted review resumes where it stopped;
change any of those inputs and the affected batches are reviewed again. A last
line cut off by an interrupted write is dropped on resume, and that batch is
reviewed again.
`--limit N` reviews only the next N pending batches, which is a cheap way to
judge a model or a style sheet first. Review exits 1 when a batch failed; run
it again to retry just those.

Read the candidates before applying them. To leave some out, list their ids
one per line in a file and pass it as `--reject-ids`; `--severity` and
`--family` keep only the named classes.

## What `apply` refuses

A correction lands only when all of these hold:

- the catalog still holds the English source and the translation the reviewer
  saw; otherwise it is **stale** (`source changed`, `translation changed` or
  `message missing`);
- the revision keeps the source's placeholders and tags, a trailing ellipsis
  or colon, the leading and trailing whitespace, and the count of newlines and
  literal `\n` escapes (**shape**);
- it keeps the current translation's number of `&` accelerators
  (**mnemonic**); in rich text, entities such as `&amp;` are not counted;
- a plural message gets a list with exactly its number of forms, and a scalar
  message a single string (**plural_forms**); no form is blank (**empty**);
- the message is not vanished and has no length variants (**variants**).

`--allow-markup-changes` lets a correction of the `markup` family change tags
and accelerators; placeholders, punctuation, whitespace and newlines still
hold. A candidates file that proposes the same id twice is refused as a
whole, because two proposals for one message have no safe winner. A
correction the catalog already holds counts as `already_applied`, so applying
the same file twice changes nothing; a revision equal to what the reviewer saw
counts as `unchanged`.

Accepted corrections go into the TS file through the byte-preserving writer,
so only the edited messages change. They keep their state (an unfinished
message stays unfinished) unless `--finish` records that a person accepted the
candidates, which marks them finished.

## The ledger

The catalog and the ledger are written together or not at all: both are
staged, then replaced, and the catalog is restored if the ledger cannot be
written. An existing LEDGER is refused unless `--force`, and a catalog or
ledger path that resolves to an input is refused.

`apply` writes LEDGER as JSON: `scope` (`--scope`, or a default naming the
catalog), `skipped` with a count for every reason (`rejected`, `severity`,
`family`, `plural_forms`, `empty`, `shape`, `mnemonic`, `vanished`,
`variants`, `format`, `already_applied`, `unchanged`, `stale`), `skipped_items` with the id, reason and refused
revision, `stale` with the expected and live source and translation, and
`changes`. A change records the language (TARGET), the id, context, source,
before, after, reason, family, severity, model, comment and the state before
and after. The command prints the same counts and the skipped ids by reason.

`--dry-run` prints that summary and writes nothing.

## Exit codes

| Exit | Meaning |
|---|---|
| 0 | Done |
| 1 | `review`: a batch failed; rerun to resume |
| 2 | Missing endpoint or model, a missing file, an unknown severity or family, a malformed or ambiguous candidates file, an existing ledger without `--force`, an output that is an input |
| 130 | Interrupted with Ctrl+C |
| 3 | The `llm` extra is missing |

Editorial review complements the [QA checks](quality.md) and the
[reviewer](review.md); it does not replace either. A model that edits its own
translation finds what it is told to look for, and the decision stays with a
person.
