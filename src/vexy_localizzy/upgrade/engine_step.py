# this_file: src/vexy_localizzy/upgrade/engine_step.py
"""Tier 9: machine-translate the messages no earlier tier could fill.

The remaining FRESH units form a sub-catalog that goes through the ordinary
``translate_catalog`` pipeline, so batching, cache reuse and content QA are the
same as for ``localizzy translate``. Each batch prompt carries only the glossary
terms that occur in that batch.
"""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.formats import qt_numerus
from vexy_localizzy.memory import Glossary
from vexy_localizzy.translate.cache import TranslationCache
from vexy_localizzy.translate.catalog import translate_catalog
from vexy_localizzy.translate.catalog_types import PromptContext
from vexy_localizzy.translate.types import TranslationExample, TranslationItem


@dataclass(frozen=True)
class EngineFill:
    unit: Unit | None  # filled unit, or None when the engine gave nothing
    model: str | None = None
    glossary_terms: tuple[str, ...] = ()


@dataclass
class BatchContext:
    """PromptContext callback: style, batch-relevant glossary terms, examples."""

    glossary: Glossary | None
    style: str = ""
    examples: Mapping[str, list[TranslationExample]] = field(default_factory=dict)
    limit: int = 60

    def __call__(self, items: list[TranslationItem]) -> PromptContext:
        keys = list(dict.fromkeys(json.loads(item.id)[0] for item in items))
        glossary = (
            self.glossary.relevant([i.source for i in items], limit=self.limit)
            if self.glossary is not None
            else {}
        )
        examples = [ex for key in keys for ex in self.examples.get(key, ())]
        return PromptContext(style=self.style, glossary=glossary, examples=examples)


def blank_unit(unit: Unit, form_count: int | None) -> Unit:
    """Clear every target slot; numerus units get the FRESH form count."""
    update: dict = {"state": "untranslated"}
    if unit.plural is not None:
        count = form_count or len(unit.plural.forms) or 1
        update["plural"] = PluralForms(
            indexing="index", forms={str(i): "" for i in range(count)}
        )
        update["target"] = None
    elif unit.variants is not None:
        update["variants"] = [""] * len(unit.variants)
        update["target"] = "" if unit.target is not None else None
    else:
        update["target"] = ""
    return unit.model_copy(update=update)


def _plural_count(target_lang: str, form_counts: Mapping[int, int]) -> int:
    try:
        return qt_numerus.count(target_lang)
    except qt_numerus.UnknownQtNumerus:
        return max(form_counts.values(), default=1) or 1


def run_engine(
    units: Mapping[int, Unit],
    form_counts: Mapping[int, int],
    *,
    source_lang: str,
    target_lang: str,
    cache: TranslationCache,
    glossary: Glossary | None = None,
    examples: Mapping[int, list[TranslationExample]] | None = None,
    style: str = "",
    batch_size: int = 50,
    glossary_limit: int = 60,
) -> dict[int, EngineFill]:
    """Translate units keyed by FRESH ordinal; return what the engine produced.

    Every numerus unit gets the same form count: the target's Qt count when
    known, else the largest FRESH count. The pipeline requires one plural rule
    per catalog.
    """
    if not units:
        return {}
    ordinals = list(units)
    plural_count = _plural_count(target_lang, form_counts)
    plural_forms = {str(i): f"Qt numerus form {i}" for i in range(plural_count)}
    template = Catalog(
        source_lang=source_lang,
        target_lang=target_lang,
        units=[blank_unit(units[o], plural_count) for o in ordinals],
        origin_format="ts",
    )
    by_key = {units[o].key: o for o in ordinals}
    context: Callable = BatchContext(
        glossary,
        style=style,
        examples={units[o].key: v for o, v in (examples or {}).items() if o in units},
        limit=glossary_limit,
    )
    has_plural = any(units[o].plural is not None for o in ordinals)
    result = translate_catalog(
        template,
        cache,
        plural_forms=plural_forms if has_plural else None,
        context=context,
        batch_size=batch_size,
    )
    models: dict[str, str] = {}
    for evidence in result.providers:
        for item in evidence.item_ids:
            models[json.loads(item)[0]] = evidence.reported_model
    fills: dict[int, EngineFill] = {}
    for unit, disposition in zip(
        result.catalog.units, result.dispositions, strict=True
    ):
        ordinal = by_key[unit.key]
        terms = (
            tuple(glossary.relevant([unit.source], limit=glossary_limit))
            if glossary is not None
            else ()
        )
        filled = disposition.status in ("candidate", "review_required")
        fills[ordinal] = EngineFill(
            unit=unit if filled else None,
            model=models.get(unit.key),
            glossary_terms=terms,
        )
    return fills
