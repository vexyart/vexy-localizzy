---
this_file: src_docs/md/8-toolkit/quality.md
---
# Translation content QA

The checks below run from Python or as `localizzy qa`; the command and its
optional layers are described at the end of this page.

`qa.check_text(source, target, policy=TextPolicy(), unit_key=...)` returns typed
findings without modifying either string. `qa.validate_batch(batch, result)` is
a `TranslationCache` callback: it rejects major/critical findings before caching
and on cache reopen. Version `validation_identity` whenever a rule or policy changes.

The default policy is Qt: exact `%1`, `%L1`, `%n` and `%Ln` token multiplicity,
ampersand mnemonics, and automatic recognition of common HTML tags. Numbered
arguments and mnemonic letters can move. `&&` is a literal ampersand. In HTML,
attribute ampersands and character entities do not introduce mnemonics.

HTML checks compare ordered tags and protected attributes, validate nesting, and
preserve stylesheet/script contents. Attribute order, quote style, tag case and
void-tag serialization may differ. `alt` and `title` text may be translated.
Empty visible translations fail even when tags remain. An existing source nesting
defect is reported separately; an identical retained defect is a review finding.
Optional HTML closing tags are not inferred. Choose `markup="html"` for explicit
HTML fragments or `markup="none"` for literal angle-bracket examples; automatic
recognition is a convenience, not a complete HTML-versus-prose classifier.

Choose formatting styles explicitly. `TextPolicy(placeholder_styles=("python_brace",))`
uses Python's `Formatter.parse`, retaining fields, repeated occurrences, conversion
and format specifications, including nested widths and implicit indices. It does
not evaluate field expressions. Do not apply it to CSS or ICU message syntax.
`TextPolicy(placeholder_styles=("printf",), accelerators=False)` delegates C printf
checking to installed GNU `msgfmt`, supporting positional parameters, star widths
and length modifiers. A negative control ensures malformed source formats cannot
silently disable checking. Missing tools/timeouts are errors. This is native
argument compatibility checking, not byte-identical formatting or Python `%` syntax.
No printf parser is vendored; Qt-only checks require no external executable.

`qa.catalog.check_catalog(catalog, policy=..., required_plural_forms=("0", "1"))`
checks every active nonblank-source message, even if it is marked untranslated.
Every native plural and length variant is visited. Missing/extra plural forms,
empty targets and inconsistent primary/variant aliases fail. Supply the exact
native positions or categories for the target locale; absence of a plural rule
is an explicit finding. The API never substitutes CLDR decimal categories for
Qt integer plural positions. Determine these using the target application's rules
and verify candidates using its native compiler.

`TARGET-UNCHANGED` and `SOURCE-MARKUP` remain visible review findings. They do not
automatically approve an invariant or prove a translation correct. The final
catalog pipeline must reconcile these findings, message eligibility, reviewed
invariants, locale coverage and native compilation separately. These checks do
not implement ICU semantic validation or linguistic quality scoring.

## The `qa` command

```sh
localizzy qa i18n/app_de.ts --plural-forms auto --format table
localizzy qa i18n/app_de.ts --plural-forms auto --fail-on critical --format sarif --out qa-de.sarif
localizzy qa i18n/app_xx.ts --plural-forms 0,1
```

The command loads any supported catalog, runs `check_catalog` with the Qt
policy and changes nothing. `--plural-forms` names the required native forms;
`auto` derives them from the target language: positions `0` to `n-1` from Qt's
numerus count for TS and PO (falling back to the gettext table where Qt has no
rule), CLDR categories for category-keyed catalogs. A language with no known
rule, such as the `xx-pseudo` of a [pseudo catalog](pseudo.md), needs the forms
spelled out; `auto` stops there with exit 2. Without the flag, a plural message is reported as needing a rule.

Every active message counts, so a freshly extracted catalog fails with one
`TARGET-EMPTY` critical finding per empty slot. Gate a catalog once it is
supposed to be complete.

`--fail-on` sets the lowest blocking severity: `info`, `minor`, `major`
(default) or `critical`. `--format table`, `json` or `sarif` renders the
findings, to `--out` when given (an `--out` that is the catalog itself is
refused); SARIF maps critical to `error`, major to
`warning`, the rest to `note`, and gives every result the catalog file as its
location, so code scanning accepts it. Without `--format` the command returns one
object with the catalog, unit count, findings and blocking count.

## Optional layers

The deterministic checks always run. `--layers` adds the ones that cost
something, in any combination; each raises an error when its dependency is
missing and never skips silently.

| Layer | Needs | Reports |
|---|---|---|
| `pofilter` | the `pofilter` extra and the `pofilter` command | `POFILTER-<TEST>` (major) from Translate Toolkit's `variables`, `xmltags`, `escapes`, `printf`, `nplurals`, `newlines` and `accelerators` tests, run with `--gnome` on a PO projection with the correct `Plural-Forms` header, mapped back to messages by context and source |
| `qe` | `unbabel-comet`, installed by hand; downloads a model on first use | `QE-LOW-SCORE` (major) where the reference-free COMET score is below `--qe-threshold` (0.7) |
| `judge` | the `llm` extra, `--endpoint`, `--model` and the key in `--api-key-env` | `MQM-LOW-SCORE` where a model's MQM score is below `--mqm-threshold` (80); below 50 it is critical |

The PO projection takes its `Plural-Forms` rule from the gettext table. For a
language the table lacks, a one-form or two-form catalog gets the common rule;
any other count exits 2 and asks for the declaration.

The judge scores a seeded sample (`--judge-sample`, default 0.1) of translated
messages that are not yet approved, skips `--ignore-keys`, and tells the model
not to count `--brand-terms` left in the source language as errors. Its
findings carry `confidence: "heuristic"` and the model's error list. Use it
nightly on a sample, not as a merge gate: a judge also makes mistakes, and its
findings send a message to a person, not to the bin.

| Exit | Meaning |
|---|---|
| 0 | No finding at or above `--fail-on` |
| 1 | Blocking findings |
| 2 | Unknown layer, the judge without endpoint, model or key, no plural rule for `auto`, a catalog a layer cannot convert |
| 3 | A layer's dependency is missing |

Implementation references: [Python Formatter](https://docs.python.org/3/library/string.html#string.Formatter),
[HTMLParser](https://docs.python.org/3/library/html.parser.html),
[GNU msgfmt checks](https://www.gnu.org/software/gettext/manual/html_node/msgfmt-Invocation.html),
and [Qt plural rules](https://doc.qt.io/qt-6/i18n-plural-rules.html).
