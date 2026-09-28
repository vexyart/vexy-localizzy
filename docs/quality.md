---
this_file: docs/quality.md
---
# Translation content QA

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

`qa_catalog.check_catalog(catalog, policy=..., required_plural_forms=("0", "1"))`
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

Implementation references: [Python Formatter](https://docs.python.org/3/library/string.html#string.Formatter),
[HTMLParser](https://docs.python.org/3/library/html.parser.html),
[GNU msgfmt checks](https://www.gnu.org/software/gettext/manual/html_node/msgfmt-Invocation.html),
and [Qt plural rules](https://doc.qt.io/qt-6/i18n-plural-rules.html).
