# this_file: tests/test_catalog_translation_regressions.py
"""Independent review regressions for cache policy and approved native shapes."""

from collections import Counter

import pytest
from catalog_translation_fixtures import cache, template

from vexy_localizzy.catalog import Catalog, Unit
from vexy_localizzy.qa.text import TextPolicy
from vexy_localizzy.translate.catalog import translate_catalog
from vexy_localizzy.translate.types import TranslationResult


def test_translate_when_catalog_policy_stricter_then_fallback_before_pinning(tmp_path):
    calls = Counter()
    source = Catalog(
        source_lang="en",
        target_lang="pl",
        units=[Unit(key="k", context="C", source="Open {name}", target="")],
    )

    def request(model, batch):
        calls[model] += 1
        return TranslationResult(
            targets={
                batch.items[0].id: "Otwórz" if model == "first" else "Otwórz {name}"
            },
            requested_model=model,
            reported_model=model,
        )

    for _ in range(2):
        with cache(tmp_path / "responses.sqlite", request) as saved:
            result = translate_catalog(
                source, saved, policy=TextPolicy(placeholder_styles=("python_brace",))
            )
            assert result.ready and result.providers[0].reported_model == "second"
    assert calls == {"first": 3, "second": 1}, (
        "Invalid policy output must never be pinned before fallback"
    )


def test_translate_when_reviewed_aliases_conflict_then_never_rewrite_and_approve(
    tmp_path,
):
    source = template().model_copy(update={"units": [template().units[2]]})
    reviewed = source.model_copy(
        update={
            "units": [
                source.units[0].model_copy(
                    update={
                        "target": "Approved width",
                        "variants": ["Different width", "Short"],
                        "state": "approved",
                    }
                )
            ]
        }
    )
    with cache(
        tmp_path / "responses.sqlite",
        lambda *_: pytest.fail("No provider calls before reviewed preflight"),
    ) as saved:
        with pytest.raises(ValueError, match="Reviewed"):
            translate_catalog(source, saved, reviewed=reviewed)
