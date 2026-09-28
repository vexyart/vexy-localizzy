# this_file: tests/test_catalog_translation.py
"""Complete catalog form coverage with durable batch reuse and review dispositions."""

from collections import Counter

import pytest
from catalog_translation_fixtures import cache, response, template

from vexy_localizzy.catalog import compute_source_hash
from vexy_localizzy.catalog_translation import translate_catalog
from vexy_localizzy.catalog_translation_types import InvariantApproval, PromptContext
from vexy_localizzy.provider_errors import ProviderUnavailable
from vexy_localizzy.translation_types import TranslationResult


def test_translate_when_all_native_forms_then_complete_candidates_and_zero_call_resume(
    tmp_path,
):
    calls = Counter()

    def request(model, batch):
        calls[model] += 1
        assert batch.style == "Brief labels"
        assert batch.glossary == {"point": "punkt"}
        assert all(i.context == "C" and i.form for i in batch.items)
        return response(model, batch)

    options = dict(
        plural_forms={"0": "n=1", "1": "n=2", "2": "n=5"},
        batch_size=3,
        context=lambda items: PromptContext(
            style="Brief labels", glossary={"point": "punkt"}
        ),
    )
    for _ in range(2):
        with cache(tmp_path / "responses.sqlite", request) as saved:
            result = translate_catalog(template(), saved, **options)
        assert len(result.dispositions) == 6 and result.pending_messages == 0
        assert result.ready
        assert result.catalog.units[1].plural.forms["2"] == "PL %n items"
        assert result.catalog.units[1].plural.variants["2"] == [
            "PL %n items",
            "PL %n items",
        ]
        assert result.catalog.units[2].variants == ["PL Width", "PL Width"]
        assert all(u.state == "needs_review" for u in result.catalog.units[:4])
        assert result.catalog.units[4:] == template().units[4:]
        assert all(p.reported_model == "first" for p in result.providers)
    assert calls == {"first": 3}, (
        "Eight scalar requests must use three batches, then only cache hits"
    )


def test_translate_when_all_providers_unavailable_then_preserve_completed_batches_and_resume(
    tmp_path,
):
    calls = Counter()
    online = [False]

    def request(model, batch):
        calls[model] += 1
        if batch.items[0].source == "%n items" and not online[0]:
            raise ProviderUnavailable("offline", retry_after=1)
        return response(model, batch)

    with cache(tmp_path / "responses.sqlite", request) as saved:
        saved.clock = lambda: 100
        partial = translate_catalog(
            template(),
            saved,
            plural_forms={"0": "one", "1": "few", "2": "many"},
            batch_size=1,
        )
        assert partial.pending_messages > 0 and not partial.ready
        assert partial.catalog.units[0].target == "PL Open %1"
    online[0] = True
    with cache(tmp_path / "responses.sqlite", request) as saved:
        saved.clock = lambda: 200
        complete = translate_catalog(
            template(),
            saved,
            plural_forms={"0": "one", "1": "few", "2": "many"},
            batch_size=1,
        )
    assert complete.pending_messages == 0 and complete.ready
    assert calls["first"] == 9, "One successful first batch must not be requested again"


def test_translate_when_reviewed_and_invariant_verified_then_no_provider_calls(
    tmp_path,
):
    source = template().model_copy(
        update={"units": [template().units[0], template().units[3]]}
    )
    reviewed = source.model_copy(
        update={
            "units": [
                source.units[0].model_copy(
                    update={"target": "Otwórz %1", "state": "approved"}
                )
            ]
        }
    )
    approval = InvariantApproval(
        source_hash=compute_source_hash(source.units[1]),
        reason="Mathematical plus symbol",
    )
    with cache(
        tmp_path / "responses.sqlite",
        lambda *_: pytest.fail("Reviewed output must not call models"),
    ) as saved:
        result = translate_catalog(
            source, saved, reviewed=reviewed, invariants={"symbol": approval}
        )
    assert result.ready and result.catalog.units[0].target == "Otwórz %1"
    assert result.catalog.units[1].target == "+"
    assert [d.status for d in result.dispositions] == ["reviewed", "invariant"]


def test_translate_when_unchanged_response_then_explicit_invariant_review_needed(
    tmp_path,
):
    source = template().model_copy(update={"units": [template().units[3]]})

    def same(model, batch):
        return TranslationResult(
            targets={i.id: i.source for i in batch.items},
            requested_model=model,
            reported_model=model,
        )

    with cache(tmp_path / "responses.sqlite", same) as saved:
        result = translate_catalog(source, saved)
    assert not result.ready and result.pending_messages == 0
    assert result.dispositions[0].status == "review_required"
