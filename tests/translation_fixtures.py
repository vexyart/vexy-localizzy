# this_file: tests/translation_fixtures.py
"""Synthetic localization batches and a deterministic provider contract."""

from vexy_localizzy.translation_types import (
    TranslationBatch,
    TranslationItem,
    TranslationResult,
)


def batch():
    return TranslationBatch(
        source_lang="en",
        target_lang="pl",
        items=[
            TranslationItem(id="first", source="Move %1.", context="Dialog"),
            TranslationItem(id="second", source="Baseline", context="Menu"),
        ],
        style="Use concise commands.",
        glossary={"baseline": "linia bazowa"},
        examples=[
            {
                "source": "Select the point.",
                "target": "Zaznacz punkt.",
                "provenance": "memory:7",
            }
        ],
    )


def reply(model, request):
    return TranslationResult(
        targets={
            item.id: "Przesuń %1." if item.id == "first" else "Linia bazowa"
            for item in request.items
        },
        requested_model=model,
        reported_model=model,
    )
