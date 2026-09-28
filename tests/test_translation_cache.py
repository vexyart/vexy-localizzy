# this_file: tests/test_translation_cache.py
"""Validated translation caching, quota fallback and durable retry semantics."""

from collections import Counter

import pytest
from translation_fixtures import batch, reply

from vexy_localizzy.translate.cache import TranslationCache, TranslationPending
from vexy_localizzy.translate.provider_errors import ProviderUnavailable


def validate(request, result):
    if "%1" not in result.targets["first"]:
        raise ValueError("Missing placeholder")


def cache(path, request, **kwargs):
    return TranslationCache(
        path,
        models=["preferred", "alternate"],
        request=request,
        endpoint_identity="synthetic",
        engine_identity="engine:1",
        validation_identity="qa:1",
        validate=validate,
        **kwargs,
    )


def test_quota_falls_back_once_and_reopen_reuses_completed_translation(tmp_path):
    calls = Counter()

    def request(model, value):
        calls[model] += 1
        if model == "preferred":
            raise ProviderUnavailable("quota", retry_after=604800)
        return reply(model, value)

    for _ in range(2):
        with cache(tmp_path / "cache.sqlite", request, clock=lambda: 100) as store:
            assert store.translate(batch()).reported_model == "alternate"
    assert calls == {"preferred": 1, "alternate": 1}
    other = batch().model_copy(update={"style": "Different style"})
    with cache(tmp_path / "cache.sqlite", request, clock=lambda: 200) as store:
        store.translate(other)
    assert calls == {"preferred": 1, "alternate": 2}


def test_recovered_primary_does_not_replace_pinned_fallback(tmp_path):
    def unavailable(model, value):
        if model == "preferred":
            raise ProviderUnavailable("quota", retry_after=60)
        return reply(model, value)

    with cache(tmp_path / "cache.sqlite", unavailable, clock=lambda: 0) as store:
        store.translate(batch())
    with cache(
        tmp_path / "cache.sqlite",
        lambda *_: pytest.fail("Pinned cached route"),
        clock=lambda: 100,
    ) as store:
        assert store.translate(batch()).requested_model == "alternate"


def test_bad_translation_retries_are_bounded_and_good_fallback_is_cached(tmp_path):
    calls = Counter()

    def request(model, value):
        calls[model] += 1
        result = reply(model, value)
        if model == "preferred":
            result.targets["first"] = "Wrong"
        return result

    with cache(tmp_path / "cache.sqlite", request) as store:
        assert store.translate(batch()).reported_model == "alternate"
    assert calls == {"preferred": 3, "alternate": 1}


def test_all_providers_unavailable_remains_pending_until_recovery(tmp_path):
    calls = []

    def offline(model, _):
        calls.append(model)
        raise ProviderUnavailable("offline", retry_after=30)

    with cache(tmp_path / "cache.sqlite", offline, clock=lambda: 0) as store:
        for _ in range(2):
            with pytest.raises(TranslationPending):
                store.translate(batch())
    assert calls == ["preferred", "alternate"]
    with cache(tmp_path / "cache.sqlite", reply, clock=lambda: 31) as store:
        assert store.translate(batch()).requested_model == "preferred"


def test_cache_hit_runs_validation_again(tmp_path):
    with cache(tmp_path / "cache.sqlite", reply) as store:
        store.translate(batch())
        store.validate = lambda *_: (_ for _ in ()).throw(ValueError("New QA finding"))
        with pytest.raises(ValueError, match="New QA"):
            store.translate(batch())


def test_mutated_request_never_poisoned_cache(tmp_path):
    original = batch()

    def request(model, value):
        value.items[0].notes.append("Changed context")
        return reply(model, value)

    with cache(tmp_path / "cache.sqlite", request) as store:
        with pytest.raises(TranslationPending):
            store.translate(original)
        assert store.db.execute("SELECT COUNT(*) FROM responses").fetchone()[0] == 0
    assert original.items[0].notes == []


def test_reference_provenance_changes_invalidate_cache(tmp_path):
    calls = []

    def request(model, value):
        calls.append(model)
        return reply(model, value)

    first = batch()
    second = batch()
    second.examples[0] = second.examples[0].model_copy(
        update={"provenance": "memory:8"}
    )
    with cache(tmp_path / "cache.sqlite", request) as store:
        store.translate(first)
        store.translate(second)
    assert calls == ["preferred", "preferred"]


def test_corrupt_cache_is_rejected_without_provider_calls(tmp_path):
    with cache(tmp_path / "cache.sqlite", reply) as store:
        store.translate(batch())
        store.db.execute("UPDATE responses SET result='{}'")
        store.db.commit()
        store.request = lambda *_: pytest.fail("Corruption must be explicit")
        with pytest.raises(ValueError, match="checksum"):
            store.translate(batch())


def test_interruption_keeps_prior_batches_reusable(tmp_path):
    with cache(tmp_path / "cache.sqlite", reply) as store:
        store.translate(batch())
        store.request = lambda *_: (_ for _ in ()).throw(KeyboardInterrupt())
        with pytest.raises(KeyboardInterrupt):
            store.translate(batch().model_copy(update={"style": "new"}))
        assert store.translate(batch()).requested_model == "preferred"


def test_validator_cannot_mutate_response_before_cache_commit(tmp_path):
    with cache(tmp_path / "cache.sqlite", reply) as store:

        def corrupt(_request, result):
            result.targets["first"] = "Wrong"

        store.validate = corrupt
        with pytest.raises(TranslationPending):
            store.translate(batch())
        assert store.db.execute("SELECT COUNT(*) FROM responses").fetchone()[0] == 0


def test_concurrent_callers_return_the_same_committed_model(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    barrier = Barrier(2)

    def worker(index):
        def request(model, value):
            barrier.wait(timeout=10)
            return reply(model, value).model_copy(
                update={"reported_model": f"actual-{index}"}
            )

        with cache(tmp_path / "cache.sqlite", request) as store:
            return store.translate(batch())

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, range(2)))
    assert results[0] == results[1], "Both callers must report the committed winner"


def test_blank_reported_model_is_never_cached(tmp_path):
    def blank(model, value):
        return reply(model, value).model_copy(update={"reported_model": " "})

    with cache(tmp_path / "cache.sqlite", blank) as store:
        with pytest.raises(TranslationPending):
            store.translate(batch())
        assert store.db.execute("SELECT COUNT(*) FROM responses").fetchone()[0] == 0
