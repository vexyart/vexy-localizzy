# this_file: tests/test_distillation_cache.py
"""Distillation reuses durable provider routing without manufacturing missing votes."""

import json
from collections import Counter

import numpy as np
import pytest

from vexy_localizzy.distillation import DistillationEntry
from vexy_localizzy.distillation_cache import CachedSelector, DistillationPending
from vexy_localizzy.translate.provider_errors import ModelResponse, ProviderUnavailable


def inputs():
    return [
        DistillationEntry(
            id=11, source="Open", targets={"de": "Öffnen"}, criticality="A", quality=3
        ),
        DistillationEntry(
            id=22,
            source="Open it",
            targets={"de": "Öffnen"},
            criticality="B",
            quality=1,
        ),
    ]


RESPONSE = json.dumps(
    {
        "keep": [300],
        "drop": [
            {
                "id": 301,
                "representative": 300,
                "equivalent": True,
                "reason": "Same action",
            }
        ],
    }
)


@pytest.mark.parametrize("fenced", [False, True])
def test_selector_when_quota_exhausted_then_fallback_and_cache_survive_reopen(
    tmp_path, fenced
):
    calls = Counter()

    def request(model, prompt, payload):
        calls[model] += 1
        data = json.loads(payload)
        assert data["format"] == "localizzy-distillation-2"
        assert [item["id"] for item in data["entries"]] == [300, 301]
        assert [item["source_id"] for item in data["entries"]] == [11, 22]
        assert [item["target_locales"] for item in data["entries"]] == [["de"], ["de"]]
        assert all("targets" not in item for item in data["entries"])
        assert "equivalent" in prompt
        if model == "three":
            raise ProviderUnavailable("quota", retry_after=600000)
        content = (
            "```json\n" + RESPONSE + "\n```" if fenced and model == "four" else RESPONSE
        )
        return ModelResponse(content, model)

    for _ in range(2):
        with CachedSelector(
            tmp_path / "cache.sqlite",
            models=("one", "two", "three"),
            request=request,
            endpoint_identity="synthetic",
            fallbacks={"three": ("four",)},
        ) as selector:
            result = selector.select(
                inputs(),
                np.array([[1, 0], [1, 0]], dtype=np.float32),
                rare_locales=set(),
            )
            assert result["kept"] == [11]
            assert result["routed_models"] == ["one", "two", "four"]
            assert result["reported_models"] == ["one", "two", "four"]
            assert result["requested_models"] == ["one", "two", "three"]
            if fenced:
                assert (
                    selector.db.execute(
                        "SELECT response FROM responses WHERE model='four'"
                    ).fetchone()[0]
                    == "```json\n" + RESPONSE + "\n```"
                ), "Retain the exact provider response in cache"
    assert calls == {"one": 1, "two": 1, "three": 1, "four": 1}


def test_selector_when_all_alternatives_fail_then_keep_successful_responses(tmp_path):
    calls = Counter()

    def request(model, prompt, payload):
        calls[model] += 1
        if model == "three":
            raise ProviderUnavailable("offline", retry_after=30)
        return ModelResponse(RESPONSE, model)

    with CachedSelector(
        tmp_path / "cache.sqlite",
        models=("one", "two", "three"),
        request=request,
        endpoint_identity="test",
    ) as selector:
        for _ in range(2):
            with pytest.raises(DistillationPending):
                selector.select(
                    inputs(),
                    np.array([[1, 0], [1, 0]], dtype=np.float32),
                    rare_locales=set(),
                )
        assert selector.db.execute("SELECT COUNT(*) FROM responses").fetchone()[0] == 2
    assert calls == {"one": 1, "two": 1, "three": 1}


def test_selector_when_identity_unverified_then_no_approved_decision(tmp_path):
    with CachedSelector(
        tmp_path / "cache.sqlite",
        models=("one", "two", "three"),
        request=lambda *_: RESPONSE,
        endpoint_identity="test",
    ) as selector:
        with pytest.raises(DistillationPending, match="identity"):
            selector.select(
                inputs(),
                np.array([[1, 0], [1, 0]], dtype=np.float32),
                rare_locales=set(),
            )


def test_selector_when_payload_oversized_then_no_calls(tmp_path):
    calls = []
    with CachedSelector(
        tmp_path / "cache.sqlite",
        models=("one", "two", "three"),
        request=lambda *args: calls.append(args),
        endpoint_identity="test",
        max_request_bytes=100,
    ) as selector:
        with pytest.raises(ValueError, match="budget"):
            selector.select(
                inputs(),
                np.array([[1, 0], [1, 0]], dtype=np.float32),
                rare_locales=set(),
            )
    assert calls == []


def test_selector_when_rare_coverage_changes_then_models_receive_new_context(tmp_path):
    requests = []

    def request(model, prompt, payload):
        requests.append(json.loads(payload))
        return ModelResponse(RESPONSE, model)

    with CachedSelector(
        tmp_path / "cache.sqlite",
        models=("one", "two", "three"),
        request=request,
        endpoint_identity="test",
    ) as selector:
        for rare in (set(), {"de"}, {"de"}):
            selector.select(
                inputs(),
                np.array([[1, 0], [1, 0]], dtype=np.float32),
                rare_locales=rare,
            )
    assert len(requests) == 6, (
        "Changed locale rarity must invalidate the model response cache"
    )
    assert [item["rare_locales"] for item in requests] == [
        [],
        [],
        [],
        ["de"],
        ["de"],
        ["de"],
    ]


def test_selector_when_threshold_changes_then_cached_votes_reapply_policy(tmp_path):
    calls = []

    def request(model, *_):
        calls.append(model)
        return ModelResponse(RESPONSE, model)

    with CachedSelector(
        tmp_path / "cache.sqlite",
        models=("one", "two", "three"),
        request=request,
        endpoint_identity="test",
    ) as selector:
        vectors = np.array([[1, 0], [0.8, 0.6]], dtype=np.float32)
        first = selector.select(inputs(), vectors, rare_locales=set(), threshold=0.7)
        second = selector.select(inputs(), vectors, rare_locales=set(), threshold=0.9)
    assert first["kept"] == [11]
    assert second["kept"] == [11, 22]
    assert len(calls) == 3, (
        "A deterministic similarity change must reuse paid model votes"
    )


def test_selector_when_output_malformed_then_bounded_retry_and_fallback(tmp_path):
    calls = Counter()

    def request(model, *_):
        calls[model] += 1
        return ModelResponse(
            '{"keep":[300],"drop":[]}' if model == "three" else RESPONSE, model
        )

    with CachedSelector(
        tmp_path / "cache.sqlite",
        models=("one", "two", "three"),
        request=request,
        endpoint_identity="test",
        fallbacks={"three": ("four",)},
    ) as selector:
        result = selector.select(
            inputs(), np.array([[1, 0], [1, 0]], dtype=np.float32), rare_locales=set()
        )
        assert result["resolved_models"] == ["one", "two", "four"]
        assert (
            selector.db.execute(
                "SELECT COUNT(*) FROM attempts WHERE error IS NOT NULL"
            ).fetchone()[0]
            == 3
        )
    assert calls == {"one": 1, "two": 1, "three": 3, "four": 1}


def test_selector_when_provider_recovers_then_resume_only_missing_vote(tmp_path):
    calls = Counter()
    now = [1000]

    def request(model, *_):
        calls[model] += 1
        if model == "three" and now[0] == 1000:
            raise ProviderUnavailable("quota", retry_after=600000)
        return ModelResponse(RESPONSE, model)

    for tick in (1000, 601001):
        now[0] = tick
        with CachedSelector(
            tmp_path / "cache.sqlite",
            models=("one", "two", "three"),
            request=request,
            endpoint_identity="test",
            clock=lambda: now[0],
        ) as selector:
            if tick == 1000:
                with pytest.raises(DistillationPending):
                    selector.select(
                        inputs(),
                        np.array([[1, 0], [1, 0]], dtype=np.float32),
                        rare_locales=set(),
                    )
            else:
                result = selector.select(
                    inputs(),
                    np.array([[1, 0], [1, 0]], dtype=np.float32),
                    rare_locales=set(),
                )
                assert result["resolved_models"] == ["one", "two", "three"]
    assert calls == {"one": 1, "two": 1, "three": 2}


@pytest.mark.parametrize(
    "vectors", [[[1, 0]], [[1, 0], [0, 0]], [[1, 0], [float("nan"), 0]]]
)
def test_selector_when_vectors_invalid_then_no_paid_calls(tmp_path, vectors):
    calls = []
    with CachedSelector(
        tmp_path / "cache.sqlite",
        models=("one", "two", "three"),
        request=lambda *args: calls.append(args),
        endpoint_identity="test",
    ) as selector:
        with pytest.raises(ValueError):
            selector.select(
                inputs(), np.array(vectors, dtype=np.float32), rare_locales=set()
            )
    assert calls == []
