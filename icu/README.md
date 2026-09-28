---
this_file: icu/README.md
---
# ICU MessageFormat QA

An optional Node component for complete ICU strings, using published
`@messageformat/parser` 5.1.1. Install with `npm ci` here; `npm test` exercises
the parser and CLI. This package is not published yet.

`checkMessage(source, target, locale)` returns structural findings. It preserves
argument names, repetitions, types, number/date format parameters, plural offsets,
exact-number selectors and select keys. Target plural/ordinal categories come
from the installed Node runtime's `Intl.PluralRules`; pin Node/ICU in production.
Added categories inherit the source `other` branch's argument contract. Omitted
source categories are allowed when unnecessary in the target locale. Each
selector must have unique cases, at most one offset and `other`. Repeated selector
headers are matched by compatible branch contracts, allowing reordering.

This is a structural gate, not translation approval. It does not check terminology,
custom formatter runtime support or rendered UI. Use the caller's
markup checks and native compiler too. Messages and branches may reorder distinct
arguments; fixed format parameters remain protected. Invalid checker configuration
throws; invalid messages return findings.

For numbered rich-text component placeholders, use
`checkMessage(source, target, locale, {components: 'numbered'})`, or append
`--components=numbered` to the CLI argument list (including Python bridge calls).
This opt-in policy protects compact `<0>…</0>` and `<1/>` tags, their IDs, counts,
ancestry, and argument ownership within each ICU branch. Siblings may reorder;
nonempty component labels cannot become empty, even if outside prose remains.
added plural categories inherit the source `other` branch contract. Tags may
span selectors if every branch leaves the same nesting state. Processing walks
the parsed tree without expanding combinations of selector branches.
Attribute-bearing or malformed numbered tags and tags assembled across ICU-token
boundaries are rejected before comparison. Named HTML/component tags require
separate caller QA. This is strict structural preservation; moving
components across selector boundaries is not treated as an equivalent rewrite.
Numbered tag syntax follows the published Lingui 5.9.5 React renderer; spaces
inside `<0 />` are not accepted as self-closing component syntax.

The CLI consumes a JSON array of at most 100 objects with `source`, `target`,
and `locale`, and emits an equally sized array of finding arrays. Findings do
not change exit status; malformed input/configuration exits 2 with no JSON output.

Python callers can use `qa_icu.check_pairs()` or pass
`functools.partial(qa_icu.validate_batch, command=["node", "/installed/cli.mjs"])`
as a `TranslationCache` validator. Version the cache's `validation_identity` with
the checker artifact and Node/ICU versions. Structural failures reject candidates
and allow provider fallback; missing/broken tooling raises `RuntimeError` and
stops requests. The bridge has an explicit subprocess timeout and no shell.

Upstream API: https://messageformat.github.io/messageformat/api/parser/
