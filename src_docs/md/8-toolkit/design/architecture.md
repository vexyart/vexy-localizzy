---
this_file: src_docs/md/8-toolkit/design/architecture.md
---
# Toolkit architecture

The toolkit takes a Qt application from English-only source to a reviewed,
continuously updated set of catalogs. It audits the source, extracts with Qt's
own tools, converts between formats without pretending the conversion is
lossless, fills catalogs from memories before models, checks the result and
puts people on whatever is left. This page records the decisions that shape
all of it.

## Three layers

| Layer | Owns | Never does |
|---|---|---|
| [abersetz](https://code.twardoch.com/abersetz/) | Text in, text out: engines, providers, chunking, vocabulary hints | Parse a catalog |
| vexy-localizzy | Catalogs, memories, upgrades, QA, review, Qt tooling | Choose your words for you |
| Your project | `localizzy.toml`, memories, style guidance, the reviewed catalogs | |

The toolkit calls the engine through its Python API and hands it bounded
batches; the engine never sees a file. Credentials, endpoints, models and
project guidance belong to the project.

## Tenets

**Parse at the boundary.** Raw bytes (TS, PO, XLIFF, i18next, Android, TMX,
`.ui`, C++ source, `localizzy.toml`) are parsed once, where they enter, into
typed, frozen records. Code past that point works with records whose existence
proves they are well formed. A malformed file fails at load, not three steps
later.

**Findings are data.** Scans, conversions, QA and validation return `Finding`
records: a rule id, a severity (`info`, `minor`, `major`, `critical`), a
message, a message key or source location, a confidence (`exact` or
`heuristic`) and rule-specific data. One renderer set serves them all as a
table, JSON or SARIF 2.1.0. Exceptions are kept for real boundary failures: a
missing file, a missing tool, a server that does not answer.

**Illegal states are hard to write.** A message state is one of
`untranslated`, `needs_review`, `translated`, `approved` and `vanished`; a
severity is one of four; configuration keys are a closed set. A misspelt key
is refused, not defaulted.

**No lossless universal converter.** Formats are not isomorphic. Every
catalog is normalized into one canonical model and keeps its original bytes
beside it, so an unchanged round trip restores the file exactly and an edit
touches only the messages it changes. A conversion that would change or drop
a field reports each loss as a finding and refuses to write until
`--allow-loss` acknowledges it. See [catalog formats](../formats.md).

**Native tools for native jobs.** Extraction uses `lupdate`, compilation
`lrelease`; the optional `pofilter` layer runs Translate Toolkit. They are
discovered on the machine, never bundled and never reimplemented.

**Small core, optional extras.** The core install reads, writes, scans,
pseudo-localizes and checks. The engine, the reviewer, libclang, Translate
Toolkit and the extra source readers are extras; quality estimation is a
separate install. A missing extra is a clear error with the command that
installs it; nothing installs itself.

**Memory before model, people before approval.** Reviewed memories fill what
they can, the model drafts the rest, deterministic checks reject what is
structurally broken, and only a person in the reviewer marks a message
approved.

## The canonical model

A `Catalog` carries a source language, an optional target language, its
units, its origin format and the retained original document. A `Unit` carries:

| Field | Holds |
|---|---|
| `key` | A stable identifier derived from context and source |
| `context`, `disambiguation` | Qt's context and comment, PO's `msgctxt`, and their equivalents |
| `source`, `source_plural` | The source text and, where the format has one, its plural |
| `target` | The translation of a scalar message |
| `plural` | Native forms, indexed positionally (Qt, gettext) or by CLDR category, an ICU string where one was parsed, and length variants per form |
| `variants` | Qt length variants of a scalar message |
| `placeholders` | Detected tokens with their style: Qt, printf, brace, ICU, i18next, markup |
| `notes`, `locations`, `max_length` | Comments, source references, a length budget |
| `state` | One of the five states above |
| `source_hash`, `record_id` | Identity used by caches and corpus records |

Plural forms stay in the convention of their format. Qt numerus forms are
positional and their count is Qt's, which is not always CLDR's; a converter
that must map positions to categories needs an explicit order and says so.

## The pipeline

```text
qt scan → qt extract → pseudo + qt release      (every change, no cost)
        → project upgrade / translate            (memories, then engine)
        → qa                                     (deterministic gate)
        → review                                 (people approve)
        → qt release                             (the build)
qa --layers judge, vocab compare                 (scheduled, informative)
```

Each step reads files and writes files, so any step can be rerun, replaced or
inspected in a diff, and the reviewed catalogs in version control remain the
record. [Continuous localization](../ci.md) wires the same steps into CI.

## Exit codes

Every command exits 0 when nothing blocks, 1 when the result is not clean or
not complete, 2 on a usage or input error, 3 when an extra or a tool is
missing, and 130 when interrupted. CI can tell "the translation has a
problem" from "the job is misconfigured" without parsing text. Bad input
prints one `localizzy:` line, never a traceback; an unexpected error, which is
a defect, still ends in a traceback and exit 1. See
[troubleshooting](../troubleshooting.md).
