# this_file: tests/test_fallback_partial_resume.py
"""Resume incomplete panels without replacing already accepted fallback votes."""

from collections import Counter

import pytest

from vexy_localizzy.classification import Entry, request_text
from vexy_localizzy.classification_cache import CachedClassifier, ClassificationPending
from vexy_localizzy.provider_errors import ModelResponse, ProviderUnavailable


def classifier(path, request, **kwargs):
    return CachedClassifier(
        path,
        prompt="Rubric",
        coverage={},
        request=request,
        endpoint_identity="endpoint",
        **kwargs,
    )


def test_partial_panel_when_primary_recovers_then_reuse_saved_fallback(tmp_path):
    calls, now = Counter(), [1000]
    path = tmp_path / "votes.sqlite"
    entries = [Entry(1, "Alpha", ())]

    def request(model, *_):
        calls[model] += 1
        if now[0] == 1000 and model in ("two", "three"):
            raise ProviderUnavailable("quota", retry_after=30)
        return ModelResponse("300 B" if model == "alternate" else "300 A", model)

    policy = dict(
        models=("one", "two", "three"),
        fallbacks={"three": ("alternate",)},
        clock=lambda: now[0],
    )
    with classifier(path, request, **policy) as cache:
        with pytest.raises(ClassificationPending):
            cache.classify_detailed(entries)
        saved = cache.db.execute("SELECT * FROM responses ORDER BY key").fetchall()
        assert len(saved) == 2, "Accepted primary and alternate votes must survive"

    now[0] += 31
    for _ in range(2):
        with classifier(path, request, **policy) as cache:
            result = cache.classify_detailed(entries)
            assert (
                result.models == result.reported_models == ("one", "two", "alternate")
            )
            assert result.votes == {1: ["A", "A", "B"]}
            assert result.identity_verified, "Keep actual model provenance on resume"
            rows = cache.db.execute("SELECT * FROM responses ORDER BY key").fetchall()
            assert all(row in rows for row in saved), (
                "Existing responses remain identical"
            )
    assert calls == {"one": 1, "two": 2, "three": 1, "alternate": 1}, (
        "Only the missing vote needs a request after recovery"
    )


def test_complete_cached_panel_when_routes_overlap_then_reassign_without_requests(
    tmp_path,
):
    path = tmp_path / "votes.sqlite"
    entries = [Entry(1, "Alpha", ())]
    with classifier(
        path,
        lambda model, *_: ModelResponse("300 A", model),
        models=("spare", "shared", "third"),
    ) as cache:
        cache.classify_detailed(entries)

    with classifier(
        path,
        lambda *_: pytest.fail("A complete cached panel must avoid all HTTP requests"),
        models=("one", "two", "three"),
        fallbacks={
            "one": ("shared", "spare"),
            "two": ("shared", "new"),
            "three": ("third",),
        },
    ) as cache:
        result = cache.classify_detailed(entries)
        assert result.models == result.reported_models == ("spare", "shared", "third")
        assert result.identity_verified, (
            "Cached assignments still require distinct identities"
        )


@pytest.mark.parametrize("cached_models", [("shared", "spare"), ("shared",)])
def test_partial_panel_when_routes_overlap_then_only_request_missing_votes(
    tmp_path, cached_models
):
    path = tmp_path / "votes.sqlite"
    entries = [Entry(1, "Alpha", ())]
    calls = Counter()

    def request(model, *_):
        calls[model] += 1
        return ModelResponse("300 A", model)

    policy = dict(
        models=("one", "two", "three"),
        fallbacks={"one": ("shared", "spare"), "two": ("shared", "new")},
        clock=lambda: 1000,
    )
    with classifier(path, request, **policy) as cache:
        cache._fetch(cached_models, request_text(entries, {}), 1)
        for model in policy["models"]:
            cache.defer(model, 604800, "quota")
        saved = cache.db.execute("SELECT * FROM responses ORDER BY key").fetchall()
    calls.clear()

    for _ in range(2):
        with classifier(path, request, **policy) as cache:
            with pytest.raises(ClassificationPending, match="three"):
                cache.classify_detailed(entries)
            rows = cache.db.execute("SELECT * FROM responses ORDER BY key").fetchall()
            assert all(row in rows for row in saved), "Preserve accepted votes"
            assert len(rows) == 2, "Retain the largest available partial panel"
    assert sum(calls.values()) == 2 - len(cached_models), (
        "Reassign cached votes before requesting replacements during an outage"
    )


def test_partial_panel_when_cached_slot_must_move_then_finish_with_distinct_models(
    tmp_path,
):
    calls = Counter()
    entries = [Entry(1, "Alpha", ())]

    def request(model, *_):
        calls[model] += 1
        return ModelResponse("300 A", model)

    with classifier(
        tmp_path / "votes.sqlite",
        request,
        models=("one", "two", "three"),
        fallbacks={"one": ("shared", "spare"), "two": ("shared",)},
    ) as cache:
        cache._fetch(["shared"], request_text(entries, {}), 1)
        for model in ("one", "two"):
            cache.defer(model, 604800, "quota")
        for _ in range(2):
            result = cache.classify_detailed(entries)
            assert (
                result.models == result.reported_models == ("spare", "shared", "three")
            )
            assert result.identity_verified, (
                "Reassignment must preserve model provenance"
            )
    assert calls == {"shared": 1, "spare": 1, "three": 1}, (
        "Extending the cached assignment must still find a complete distinct panel"
    )
