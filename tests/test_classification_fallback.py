# this_file: tests/test_classification_fallback.py
"""Unavailable providers must not discard work, duplicate votes, or stall peers."""

import sqlite3
import threading
from collections import Counter

import pytest

from vexy_localizzy.classification import Entry
from vexy_localizzy.classification_cache import CachedClassifier
from vexy_localizzy.translate.provider_errors import ProviderUnavailable, retry_delay


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


def test_fallback_when_quota_exhausted_then_one_attempt_durable_cooldown_and_actual_votes(
    tmp_path,
):
    calls = Counter()
    now = [1000.0]

    def request(model, *_):
        calls[model] += 1
        if model == "three":
            raise ProviderUnavailable("quota", retry_after=600000)
        return "300 B" if model == "alternate" else "300 A"

    path = tmp_path / "cache.sqlite"
    for entry in (Entry(1, "Alpha", ()), Entry(1, "Alpha", ()), Entry(2, "Beta", ())):
        with classifier(
            path, request, fallbacks={"three": ("alternate",)}, clock=lambda: now[0]
        ) as cache:
            result = cache.classify_detailed([entry])
            assert result.models == ("one", "two", "alternate")
            assert result.votes[entry.id] == ["A", "A", "B"]
    assert calls == {"one": 2, "two": 2, "three": 1, "alternate": 2}
    with sqlite3.connect(path) as db:
        assert (
            db.execute("SELECT until FROM cooldowns WHERE model='three'").fetchone()[0]
            == 601000
        )
    now[0] = 700000
    with classifier(
        path, request, fallbacks={"three": ("alternate",)}, clock=lambda: now[0]
    ) as cache:
        cache.classify([Entry(1, "Alpha", ())])
        assert calls["three"] == 1, (
            "A saved fallback selection must stay reproducible after cooldown expiry"
        )
        cache.classify([Entry(3, "Gamma", ())])
    assert calls["three"] == 2, "New batches should reconsider a recovered primary"


def test_fallback_when_primary_vote_cached_then_quota_does_not_replace_it(tmp_path):
    path = tmp_path / "cache.sqlite"
    with classifier(path, lambda *_: "300 A") as cache:
        cache.classify([Entry(1, "Alpha", ())])
        cache.defer("three", 600000, "quota")
    with classifier(
        path,
        lambda *_: pytest.fail("Cached votes must avoid transport"),
        fallbacks={"three": ("alternate",)},
    ) as cache:
        result = cache.classify_detailed([Entry(1, "Alpha", ())])
        assert result.models == ("one", "two", "three")


def test_fallback_when_all_candidates_fail_then_pending_and_good_votes_remain(tmp_path):
    calls = Counter()

    def request(model, *_):
        calls[model] += 1
        if model in ("three", "alternate"):
            raise ProviderUnavailable("offline", retry_after=60)
        return "300 A"

    with classifier(
        tmp_path / "cache.sqlite", request, fallbacks={"three": ("one", "alternate")}
    ) as cache:
        for _ in range(2):
            with pytest.raises(RuntimeError, match="three"):
                cache.classify([Entry(1, "Alpha", ())])
        assert cache.db.execute("SELECT COUNT(*) FROM responses").fetchone()[0] == 2
        assert cache.db.execute("SELECT COUNT(*) FROM selections").fetchone()[0] == 0
    assert calls == {"one": 1, "two": 1, "three": 1, "alternate": 1}


def test_fallback_when_two_slots_share_alternatives_then_three_distinct_actual_models(
    tmp_path,
):
    def request(model, *_):
        if model in ("two", "three"):
            raise ProviderUnavailable("quota", retry_after=100)
        return "300 A"

    with classifier(
        tmp_path / "cache.sqlite",
        request,
        fallbacks={"two": ("spare", "other"), "three": ("spare", "other")},
    ) as cache:
        result = cache.classify_detailed([Entry(1, "Alpha", ())])
    assert result.models == ("one", "spare", "other")


def test_fallback_when_malformed_primary_then_bounded_retries_and_valid_alternative(
    tmp_path,
):
    calls = Counter()

    def request(model, *_):
        calls[model] += 1
        return "invalid" if model == "three" else "300 B"

    with classifier(
        tmp_path / "cache.sqlite", request, fallbacks={"three": ("alternate",)}
    ) as cache:
        assert (
            cache.classify_detailed([Entry(1, "Alpha", ())]).models[-1] == "alternate"
        )
    assert calls["three"] == 3


@pytest.mark.parametrize("reply", [[], {}, ["300 A"], {"content": "300 A"}, None])
def test_fallback_when_custom_transport_returns_non_text_then_resume_uses_good_votes(
    tmp_path, reply
):
    calls = Counter()

    def request(model, *_):
        calls[model] += 1
        return reply if model == "three" else "300 B"

    path = tmp_path / "cache.sqlite"
    for _ in range(2):
        with classifier(path, request, fallbacks={"three": ("alternate",)}) as cache:
            result = cache.classify_detailed([Entry(1, "Alpha", ())])
            assert result.models == ("one", "two", "alternate"), (
                "Malformed transport results must reach the configured fallback"
            )
            assert result.votes == {1: ["B", "B", "B"]}
    assert calls == {"one": 1, "two": 1, "three": 3, "alternate": 1}, (
        "Retries must be bounded and completed votes reused after reopening"
    )


@pytest.mark.parametrize(
    "fallbacks",
    [{"unknown": ("spare",)}, {"three": ("",)}, {"three": ("spare", "spare")}],
)
def test_fallback_when_policy_invalid_then_no_requests(tmp_path, fallbacks):
    with pytest.raises(ValueError):
        classifier(
            tmp_path / "cache.sqlite",
            lambda *_: pytest.fail("Invalid policy"),
            fallbacks=fallbacks,
        )


@pytest.mark.parametrize(
    "headers,body,expected",
    [
        ({"retry-after": "598850"}, {}, 598850),
        ({"retry-after-ms": "1500"}, {}, 1.5),
        ({}, {"reset_seconds": 300}, 300),
        ({"retry-after": "Thu, 01 Jan 1970 00:02:00 GMT"}, {}, 20),
        ({"retry-after": "nan"}, {}, 60),
        ({"retry-after": "-5"}, {}, 60),
        ({}, {"error": {"reset_seconds": 598850}}, 598850),
        (
            {"retry-after": "Thu, 01 Jan 1970 00:02:00 GMT"},
            {"reset_seconds": 1},
            20,
        ),
        ({}, {"reset_seconds": 10**1000}, 60),
    ],
)
def test_provider_when_retry_information_present_then_respect_it(
    headers, body, expected
):
    assert retry_delay(headers, body, now=100) == expected


def test_cache_when_v2_migrated_then_existing_responses_are_reused(tmp_path):
    path = tmp_path / "cache.sqlite"
    with classifier(path, lambda *_: "300 A") as cache:
        cache.classify([Entry(1, "Alpha", ())])
        previous = cache.db.execute("SELECT * FROM responses ORDER BY key").fetchall()
        cache.db.execute("DROP TABLE cooldowns")
        cache.db.execute("DROP TABLE selections")
        cache.db.execute("DROP TABLE response_models")
        cache.db.execute("PRAGMA user_version=2")
    with classifier(
        path,
        lambda *_: pytest.fail("Migration must retain successful votes"),
        fallbacks={"three": ("spare",)},
    ) as cache:
        assert cache.classify([Entry(1, "Alpha", ())])[1] == ["A", "A", "A"]
        assert (
            cache.db.execute("SELECT * FROM responses ORDER BY key").fetchall()
            == previous
        )
        assert cache.db.execute("PRAGMA user_version").fetchone()[0] == 5


def test_fallback_when_greedy_choice_would_starve_another_slot_then_find_valid_assignment(
    tmp_path,
):
    def request(model, *_):
        if model in ("two", "three"):
            raise ProviderUnavailable("quota", retry_after=60)
        return "300 A"

    with classifier(
        tmp_path / "cache.sqlite",
        request,
        fallbacks={"two": ("shared", "other"), "three": ("shared",)},
    ) as cache:
        assert cache.classify_detailed([Entry(1, "Alpha", ())]).models == (
            "one",
            "other",
            "shared",
        )


def test_fallback_when_route_never_returns_then_deadline_cools_and_uses_alternate(
    tmp_path,
):
    release = threading.Event()

    def request(model, *_):
        if model == "three":
            release.wait()
        return "300 A"

    try:
        with classifier(
            tmp_path / "cache.sqlite", request, fallbacks={"three": ("alternate",)}
        ) as cache:
            cache._FETCH_DEADLINE = 0.01
            assert cache.classify_detailed([Entry(1, "Alpha", ())]).models == (
                "one",
                "two",
                "alternate",
            )
            assert (
                cache.db.execute(
                    "SELECT count(*) FROM attempts WHERE model='three' AND error='request_deadline'"
                ).fetchone()[0]
                == 1
            )
    finally:
        release.set()
