# this_file: tests/catalog_translation_fixtures.py
"""Complete catalog form coverage with durable batch reuse and review dispositions."""

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.qa.text import validate_batch
from vexy_localizzy.translate.cache import TranslationCache
from vexy_localizzy.translate.types import TranslationResult


def template():
    return Catalog(
        source_lang="en",
        target_lang="pl",
        units=[
            Unit(key="a", context="C", source="Open %1", target=""),
            Unit(
                key="n",
                context="C",
                source="%n items",
                plural=PluralForms(
                    indexing="index",
                    forms={"0": "", "1": "", "2": ""},
                    variants={"2": ["", ""]},
                ),
            ),
            Unit(key="v", context="C", source="Width", variants=["", ""]),
            Unit(key="symbol", context="C", source="+", target=""),
            Unit(key="empty", context="C", source="", target="keep"),
            Unit(key="old", context="C", source="Old", target="keep", state="vanished"),
        ],
    )


def cache(path, request):
    return TranslationCache(
        path,
        models=("first", "second"),
        request=request,
        endpoint_identity="synthetic",
        engine_identity="synthetic:1",
        validation_identity="qt:1",
        validate=validate_batch,
    )


def response(model, batch):
    return TranslationResult(
        targets={i.id: "PL " + i.source for i in batch.items},
        requested_model=model,
        reported_model=model,
    )
