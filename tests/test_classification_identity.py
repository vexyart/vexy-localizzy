# this_file: tests/test_classification_identity.py
"""Saved model selections must remain reproducible under concurrent callers."""

import pytest

from vexy_localizzy.classification import Entry
from vexy_localizzy.classification_cache import CachedClassifier
from vexy_localizzy.provider_errors import ModelResponse


def classifier(path, request, **kwargs):
    return CachedClassifier(
        path,
        models=("one", "two", "three"),
        prompt="Rubric",
        coverage={},
        request=request,
        endpoint_identity="endpoint",
        **kwargs,
    )


def test_cache_when_concurrent_selection_wins_then_return_the_durable_choice(
    tmp_path, monkeypatch
):
    path = tmp_path / "cache.sqlite"
    now = [100.0]
    entries = [Entry(1, "Alpha", ())]
    with classifier(
        path, lambda *_: "300 A", fallbacks={"three": ("spare",)}, clock=lambda: now[0]
    ) as first:
        first.defer("three", 10, "quota")
        resolve = first._resolve

        def interleaved(payload, count):
            selected = resolve(payload, count)
            assert selected == ("one", "two", "spare")
            now[0] = 120
            with classifier(
                path,
                lambda *_: "300 B",
                fallbacks={"three": ("spare",)},
                clock=lambda: now[0],
            ) as second:
                # Complete a primary request already in flight before the other
                # caller saved its alternate; both routes are now cached.
                second._fetch(["three"], payload, count)
                assert second.classify_detailed(entries).models == (
                    "one",
                    "two",
                    "three",
                )
            return selected

        monkeypatch.setattr(first, "_resolve", interleaved)
        result = first.classify_detailed(entries)
        assert result.models == ("one", "two", "three")
        assert result.votes[1] == ["A", "A", "B"]
        assert first.classify_detailed(entries) == result


def test_identity_when_three_aliases_report_same_backend_then_do_not_accept_three_votes(
    tmp_path,
):
    with classifier(
        tmp_path / "cache.sqlite", lambda *_: ModelResponse("300 A", "same-backend")
    ) as cache:
        with pytest.raises(RuntimeError, match="pending"):
            cache.classify_detailed([Entry(1, "Alpha", ())])


def test_identity_when_aliases_overlap_then_alternatives_supply_distinct_reported_models(
    tmp_path,
):
    def request(model, *_):
        return ModelResponse(
            "300 A",
            "same-backend" if model in ("one", "two", "three") else model + "-backend",
        )

    with classifier(
        tmp_path / "cache.sqlite",
        request,
        fallbacks={"two": ("spare",), "three": ("other",)},
    ) as cache:
        result = cache.classify_detailed([Entry(1, "Alpha", ())])
        assert result.models == ("one", "spare", "other")
        assert result.reported_models == (
            "same-backend",
            "spare-backend",
            "other-backend",
        )
        assert result.identity_verified


def test_identity_when_legacy_response_then_do_not_invent_reported_model(tmp_path):
    with classifier(tmp_path / "cache.sqlite", lambda *_: "300 A") as cache:
        result = cache.classify_detailed([Entry(1, "Alpha", ())])
        assert result.reported_models == (None, None, None)
        assert not result.identity_verified


def test_identity_when_configured_alias_map_then_validate_legacy_distinctness(tmp_path):
    with classifier(
        tmp_path / "cache.sqlite",
        lambda *_: "300 A",
        model_identities={"one": "backend-a", "two": "backend-a", "three": "backend-c"},
    ) as cache:
        with pytest.raises(RuntimeError, match="pending"):
            cache.classify_detailed([Entry(1, "Alpha", ())])
