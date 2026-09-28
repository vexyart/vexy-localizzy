# this_file: src/vexy_localizzy/translate/catalog.py
"""Translate every eligible native form through the durable validated batch cache."""

from collections.abc import Callable, Mapping
from functools import partial

from vexy_localizzy.catalog import Catalog
from vexy_localizzy.qa.catalog import check_catalog, scalar_targets
from vexy_localizzy.qa.text import TextPolicy, validate_batch
from vexy_localizzy.translate.batches import batches
from vexy_localizzy.translate.cache import TranslationCache, TranslationPending
from vexy_localizzy.translate.catalog_types import (
    CatalogTranslation,
    Disposition,
    Prefill,
    PromptContext,
    ProviderEvidence,
)
from vexy_localizzy.translate.frozen_contexts import FrozenContexts
from vexy_localizzy.translate.inputs import fill_unit, item_id, prepare_units
from vexy_localizzy.translate.store import digest
from vexy_localizzy.translate.types import TranslationItem


def translate_catalog(
    template: Catalog,
    cache: TranslationCache | None,
    *,
    plural_forms: dict[str, str] | None = None,
    reviewed: Catalog | None = None,
    invariants=None,
    context: Callable[[list[TranslationItem]], PromptContext] | None = None,
    policy: TextPolicy = TextPolicy(),
    batch_size: int = 50,
    max_batch_bytes: int = 48000,
    prefilled: Mapping[str, Prefill] | None = None,
) -> CatalogTranslation:
    """Return a candidate and exact dispositions; never publish or approve generated text.

    Each batch commits through TranslationCache. Repeating with the same template,
    context and policy resumes saved batches; incomplete native units stay pending.
    The context callback supplies private style/glossary/RAG evidence as data.
    ``prefilled`` supplies memory hits and kept targets (dispositions ``memory`` and
    ``kept``); they count as decided, like reviewed units. With ``cache=None`` no
    provider is called and every remaining eligible unit stays pending.
    """
    if type(batch_size) is not int or not 1 <= batch_size <= 100:
        raise ValueError("batch_size must be an integer from one through 100")
    if type(max_batch_bytes) is not int or max_batch_bytes <= 0:
        raise ValueError("max_batch_bytes must be positive")
    template = Catalog.model_validate_json(template.model_dump_json())
    if not template.target_lang or template.target_lang == template.source_lang:
        raise ValueError("Translation requires a distinct target locale")
    plural_forms = dict(plural_forms or {})
    fixed, dispositions, items = prepare_units(
        template, reviewed, invariants or {}, plural_forms, policy, prefilled=prefilled
    )
    if cache is not None and isinstance(context, FrozenContexts):
        context.validate_for(template, items, batch_size, max_batch_bytes)
    values, providers = {}, []
    work = (
        batches(items, template, context, batch_size, max_batch_bytes)
        if cache is not None
        else ()
    )
    for batch in work:
        try:
            result = cache.translate_checked(
                batch,
                validation_identity="catalog-content-qa:1:" + policy.model_dump_json(),
                validate=partial(validate_batch, policy=policy),
            )
        except TranslationPending:
            continue
        values.update(result.targets)
        providers.append(
            ProviderEvidence(
                item_ids=[i.id for i in batch.items],
                request_sha256=digest(batch.model_dump()),
                requested_model=result.requested_model,
                reported_model=result.reported_model,
            )
        )
    units = list(template.units)
    for index, unit in enumerate(units):
        if index in fixed:
            units[index] = fixed[index]
            continue
        slots = {form: item_id(unit, form) for form, _, _ in scalar_targets(unit)}
        complete = all(key in values for key in slots.values())
        units[index] = fill_unit(
            unit,
            {form: values[key] for form, key in slots.items() if key in values},
            "needs_review" if complete else "untranslated",
        )
        dispositions[index] = Disposition(
            key=unit.key, status="candidate" if complete else "pending"
        )
    catalog = template.model_copy(update={"units": units})
    findings = check_catalog(
        catalog, policy=policy, required_plural_forms=tuple(plural_forms) or None
    )
    indices = {u.key: i for i, u in enumerate(units)}
    for finding in findings:
        index = indices[finding.unit_key]
        if dispositions[index].status == "candidate":
            dispositions[index] = Disposition(
                key=units[index].key, status="review_required"
            )
    pending = sum(d.status == "pending" for d in dispositions.values())
    ready = not any(
        d.status in ("pending", "review_required") for d in dispositions.values()
    )
    return CatalogTranslation(
        template_sha256=digest(template.model_dump()),
        catalog=catalog,
        dispositions=[dispositions[i] for i in range(len(units))],
        providers=providers,
        findings=findings,
        pending_messages=pending,
        ready=ready,
    )
