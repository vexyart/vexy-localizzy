# this_file: tests/test_catalog_translation_boundaries.py
"""Complete catalog form coverage with durable batch reuse and review dispositions."""

from collections import Counter

import pytest
from catalog_translation_fixtures import cache, response, template

from vexy_localizzy.catalog import Catalog, Unit
from vexy_localizzy.catalog_translation import translate_catalog
from vexy_localizzy.catalog_translation_types import InvariantApproval
from vexy_localizzy.translation_types import TranslationResult


@pytest.mark.parametrize("change", ["locale", "source", "quality"])
def test_translate_when_reviewed_evidence_invalid_then_preserve_or_reject_explicitly(
    tmp_path, change
):
    source = template().model_copy(update={"units": [template().units[0]]})
    item = source.units[0].model_copy(
        update={"target": "Otwórz %1", "state": "approved"}
    )
    reviewed = source.model_copy(update={"units": [item]})
    if change == "locale":
        reviewed = reviewed.model_copy(update={"target_lang": "de"})
    if change == "source":
        reviewed = reviewed.model_copy(
            update={"units": [item.model_copy(update={"source": "Earlier %1"})]}
        )
    if change == "quality":
        reviewed = reviewed.model_copy(
            update={"units": [item.model_copy(update={"target": "Otwórz"})]}
        )
    with cache(tmp_path / "responses.sqlite", response) as saved:
        if change == "source":
            assert (
                translate_catalog(source, saved, reviewed=reviewed)
                .catalog.units[0]
                .target
                == "PL Open %1"
            )
        else:
            with pytest.raises(ValueError):
                translate_catalog(source, saved, reviewed=reviewed)


def test_translate_when_duplicate_keys_or_missing_rule_then_fail_before_provider(
    tmp_path,
):
    with cache(
        tmp_path / "responses.sqlite",
        lambda *_: pytest.fail("Preflight must precede requests"),
    ) as saved:
        with pytest.raises(ValueError, match="plural"):
            translate_catalog(template(), saved)
        duplicate = template().model_copy(update={"units": [template().units[0]] * 2})
        with pytest.raises(ValueError, match="distinct"):
            translate_catalog(duplicate, saved)


def test_translate_when_invariant_source_changed_then_reject_stale_approval(tmp_path):
    source = template().model_copy(update={"units": [template().units[3]]})
    with cache(tmp_path / "responses.sqlite", response) as saved:
        with pytest.raises(ValueError, match="invariant"):
            translate_catalog(
                source,
                saved,
                invariants={
                    "symbol": InvariantApproval(
                        source_hash="old", reason="old approval"
                    )
                },
            )


def test_translate_when_enriched_batch_exceeds_budget_then_split_deterministically(
    tmp_path,
):
    source = Catalog(
        source_lang="en",
        target_lang="pl",
        units=[
            Unit(key=str(i), context="C", source="Text " + "x" * 300, target="")
            for i in range(3)
        ],
    )
    calls = []

    def request(model, batch):
        calls.append(len(batch.items))
        assert len(batch.model_dump_json().encode()) <= 850
        return response(model, batch)

    with cache(tmp_path / "responses.sqlite", request) as saved:
        result = translate_catalog(source, saved, batch_size=3, max_batch_bytes=850)
    assert result.ready and calls == [1, 1, 1]


def test_translate_when_per_item_length_exceeded_then_fallback_before_caching(tmp_path):
    source = Catalog(
        source_lang="en",
        target_lang="pl",
        units=[Unit(key="k", context="C", source="Open", target="", max_length=5)],
    )
    calls = Counter()

    def request(model, batch):
        calls[model] += 1
        return TranslationResult(
            targets={batch.items[0].id: "Too long" if model == "first" else "Menu"},
            requested_model=model,
            reported_model=model,
        )

    with cache(tmp_path / "responses.sqlite", request) as saved:
        result = translate_catalog(source, saved)
    assert result.ready and result.catalog.units[0].target == "Menu"
    assert calls == {"first": 3, "second": 1}
