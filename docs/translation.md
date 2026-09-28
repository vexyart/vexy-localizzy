---
this_file: docs/translation.md
---
# Translation batches and cache

Install `vexy-localizzy[translation]` for the published abersetz 1.0.28 engine
and OpenAI-compatible SDK. The optional dependency has a larger transitive install
than the core toolkit. Credentials, endpoint, model choices and project guidance
belong to the calling application.

`TranslationBatch` contains source/target locales, 1–100 distinct message IDs,
exact source strings, context, comments, notes and optional form descriptions.
Include glossary terms, style guidance and retrieved source/target examples with
compact provenance. Every field participates in cache identity; changing a
reference's provenance, style or plural context invalidates reuse.

`abersetz_transport.translate_batch(batch, model, base_url=..., api_key=...)`
uses abersetz's prompt construction, terminology/examples and output extraction.
A small subclass invokes the published single-attempt implementation beneath its
Tenacity wrapper. The SDK also has retries disabled. The caller can immediately
try another provider on quota, connection or server failures. The adapter records
the provider-reported model and checks exact JSON message coverage, duplicate
fields, nonempty targets and input/output byte budgets. The default timeout is
60 seconds; it must be finite and positive.

## Accepting and caching results

`TranslationCache` requires an ordered model list, request callback, stable
endpoint/engine/validation identities and a content validator:

```python
from vexy_localizzy.abersetz_transport import TRANSPORT_ID, translate_batch
from vexy_localizzy.qa.text import validate_batch
from vexy_localizzy.translation_cache import TranslationCache

with TranslationCache(
    "translations.sqlite",
    models=[preferred_model, alternate_model],
    request=lambda model, batch: translate_batch(
        batch, model, base_url=endpoint, api_key=api_key
    ),
    endpoint_identity=endpoint,
    engine_identity=TRANSPORT_ID,
    validation_identity="project-content-qa:1",
    validate=validate_batch,
) as cache:
    result = cache.translate(batch)
```

The application supplies `batch` and endpoint/model configuration. The shared
`validate_batch` uses the default Qt policy; see [content QA](quality.md) for
other syntaxes, native plural checks and review findings. A custom validator must raise on invalid content,
return `None` on success, and leave its inputs unchanged. It runs on both new
responses and cache hits. Scalar content checks do not establish complete native
plural coverage or semantic translation quality. Use the catalog orchestration
below to expand and reconcile every native target slot.

`cache.translate_checked(batch, validation_identity=..., validate=...)` adds
acceptance rules before selecting or caching a provider result. Both the cache's
original validator and the additional validator must pass. The additional identity
isolates saved selections; it does not change the original cache configuration.
`catalog_translation.translate_catalog()` uses this path for its content policy,
so a rejected candidate receives bounded retries and then provider fallback.

Each successful batch records exact targets, requested model, actual reported
model and returned vocabulary. Responses and selected routes commit atomically.
Concurrent callers return the committed winner. Cooldowns persist by endpoint
and model, while completed responses remain reusable during an outage. Successful
fallback selections stay pinned after a primary recovers. New work may try the
recovered primary again. Malformed or QA-rejected output gets at most three
attempts per model; known provider outages get one attempt before fallback.

If all candidates fail, `TranslationPending` leaves completed batches intact.
Call again after recovery. Cache corruption, invalid cached content and unknown
database schemas fail explicitly. One thread owns each cache connection; separate
callers may use separate connections to the same file.

## Complete catalog candidates

`formats.ts_template.prepare_translation(raw, target_lang=..., plural_count=...)`
explicitly prepares an empty target catalog. Supply the target locale's native
Qt plural count. It retains source/context metadata and IDs, preserves excluded
empty-source and obsolete messages, and carries length alternatives into every
target plural position. Unknown XML within editable translations causes an error.
Ordinary `ts.dump()` does not implicitly change native plural shapes.

`catalog_translation.translate_catalog(template, cache, plural_forms=...)`
expands every eligible scalar, plural and length variant into stable request IDs.
`plural_forms` maps native positional keys such as `"0"` to descriptions of their
usage. The caller supplies these from its application's locale rules. Requests
split automatically when enriched batches exceed the byte budget; a single
oversized item fails explicitly without truncation.

```python
from vexy_localizzy.catalog_translation import translate_catalog
from vexy_localizzy.formats import ts
from vexy_localizzy.formats.ts_template import prepare_translation

template = prepare_translation(source_bytes, target_lang="de", plural_count=2)
result = translate_catalog(
    template,
    cache,
    plural_forms={"0": "n=1", "1": "all other numbers"},
    context=retrieve_context,
)
if result.ready:
    ts.dump(result.catalog, candidate_path)
```

`retrieve_context(items)` returns `catalog_translation_types.PromptContext` with
style guidance, glossary and retrieved examples with provenance. It must not
change the items. Retrieval and private application configuration remain caller
responsibilities; the complete returned context participates in cache identity.

The result contains exactly one disposition per source message, the input
template digest, request digests, actual model identities, QA findings and pending
message count. Completed batches remain cached if another batch fails. Repeat
with the same template/context/policy to resume. Partial native messages retain
completed slots and stay untranslated. Generated complete messages stay
`needs_review`, which writes as unfinished TS text.

Pass `reviewed=` to reuse approved targets only when source/context and native
shape match and current QA passes. Inconsistent target/variant aliases are
rejected. For intentional unchanged labels, supply `invariants={key:
InvariantApproval(source_hash=..., reason=...)}` using `compute_source_hash(unit)`.
Unchanged generated text otherwise receives a review finding.

`ready` requires all eligible messages to have acceptable candidates or explicit
reviewed/invariant dispositions. It is not semantic approval or proof of native
compilation. Run Qt validation and inspect representative translations before
integrating candidates. Save the full result as JSON when retaining the richer
review states, coverage and provider evidence alongside native output.

## Legacy literal-token checks

`qa_tokens.check_tokens(source, target, styles=..., unit_key=...)` preserves the
legacy `PH-MISS`, `PH-EXTRA`, `TAG-MISS` and `TAG-EXTRA` finding contracts for
consumer migration. It compares multiplicities, so losing one of two repeated
tokens is an error. Qt matching uses the shared `%1`/`%L1`/`%n`/`%Ln` tokenizer.
An absent target retains the legacy skip behavior; an empty target is checked.

This compatibility API uses the catalog's literal inventory for non-Qt styles.
It does not parse complete ICU messages or replace syntax-aware Python/printf
validation through `qa.check_text`. Structural HTML validation and native target
traversal are available through `qa.check_text` and `qa_catalog.scalar_targets`.
Consumers retain their own locale rules and choices about which states to check.

The abersetz adapter accepts `temperature` (default `0.2`, finite range 0–2).
When overriding it, include the value with `TRANSPORT_ID` in the cache
`engine_identity`; changed generation settings must not reuse earlier output.
