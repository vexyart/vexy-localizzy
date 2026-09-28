# this_file: tests/test_classification_model_health.py
"""Warm routes serve work while cooled routes receive bounded health probes."""

import threading
from collections import Counter

from vexy_localizzy.classification import Entry
from vexy_localizzy.classification_cache import CachedClassifier
from vexy_localizzy.provider_errors import ProviderUnavailable


def test_pool_when_route_cools_then_uses_warm_routes_and_probes_once_due(tmp_path):
    calls, now = Counter(), [0.0]
    pool = ("first", "second", "third", "fourth")

    def request(model, _prompt, _payload):
        calls[model] += 1
        if model == "first" and calls[model] == 1:
            raise ProviderUnavailable("http:429", retry_after=3600)
        return "300 A"

    fallbacks = {
        primary: tuple(model for model in pool if model != primary)
        for primary in pool[:3]
    }
    with CachedClassifier(
        tmp_path / "responses.sqlite",
        models=pool[:3],
        prompt="rubric",
        coverage={},
        request=request,
        endpoint_identity="synthetic",
        fallbacks=fallbacks,
        clock=lambda: now[0],
    ) as classifier:
        classifier.classify([Entry(1, "one", ())])
        assert calls == {"first": 1, "second": 1, "third": 1, "fourth": 1}
        health = dict(classifier.db.execute("SELECT model,state FROM model_health"))
        assert health == {
            "first": "cool",
            "second": "warm",
            "third": "warm",
            "fourth": "warm",
        }

        classifier.classify([Entry(2, "two", ())])
        assert calls["first"] == 1, "A cooled route must not displace warm work"

        now[0] = 300.0
        classifier.classify([Entry(3, "three", ())])
        assert calls["first"] == 2, "One due health probe should test the cooled route"
        assert (
            classifier.db.execute(
                "SELECT state FROM model_health WHERE model='first'"
            ).fetchone()[0]
            == "warm"
        )


def test_deadline_when_route_hangs_then_cooldown_defers_retries_until_probe(tmp_path):
    calls, now, release = Counter(), [0.0], threading.Event()

    def request(model, _prompt, _payload):
        calls[model] += 1
        if model == "third":
            release.wait()
        return "300 A"

    try:
        with CachedClassifier(
            tmp_path / "responses.sqlite",
            models=("first", "second", "third"),
            prompt="rubric",
            coverage={},
            request=request,
            endpoint_identity="synthetic",
            fallbacks={"third": ("fourth",)},
            clock=lambda: now[0],
        ) as classifier:
            classifier._FETCH_DEADLINE = 0.01
            classifier.classify([Entry(1, "one", ())])
            assert calls["third"] == 1

            now[0] = 299.0
            classifier.classify([Entry(2, "two", ())])
            assert calls["third"] == 1

            now[0] = 300.0
            classifier.classify([Entry(3, "three", ())])
            assert calls["third"] == 2
    finally:
        release.set()
