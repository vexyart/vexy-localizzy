# this_file: tests/test_quota_envelope_fallback.py
"""HTTP-success quota errors still defer providers and preserve resumable work."""

import json
from collections import Counter

import httpx
import pytest
from test_abersetz_transport import install_transport, response
from translation_fixtures import batch

from vexy_localizzy.translate.abersetz_transport import translate_batch
from vexy_localizzy.translate.cache import TranslationCache, TranslationPending
from vexy_localizzy.translate.provider_errors import ProviderUnavailable


@pytest.mark.parametrize("alternate_down", [False, True])
def test_quota_envelope_when_routes_fail_then_cooldown_and_cached_recovery(
    tmp_path, monkeypatch, alternate_down
):
    calls = Counter()
    now = [1000]

    def handle(request):
        model = json.loads(request.content)["model"]
        calls[model] += 1
        if model == "preferred" or alternate_down and now[0] == 1000:
            return httpx.Response(
                200,
                json={
                    "error": {
                        "code": "model_cooldown",
                        "message": "Private provider diagnostic must not be logged",
                        "reset_seconds": 604800 if model == "preferred" else 30,
                    }
                },
            )
        return response(model=model)

    install_transport(monkeypatch, handle)

    def request(model, value):
        return translate_batch(
            value, model, base_url="https://example.test/v1", api_key="synthetic"
        )

    def cache():
        return TranslationCache(
            tmp_path / "cache.sqlite",
            models=("preferred", "alternate"),
            request=request,
            endpoint_identity="https://example.test/v1",
            engine_identity="synthetic",
            validation_identity="synthetic",
            validate=lambda *_: None,
            clock=lambda: now[0],
        )

    for _ in range(2):
        with cache() as store:
            if alternate_down:
                with pytest.raises(TranslationPending):
                    store.translate(batch())
                assert (
                    store.db.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
                    == 0
                )
            else:
                assert store.translate(batch()).requested_model == "alternate"
            assert (
                store.db.execute(
                    "SELECT until FROM cooldowns WHERE model='preferred'"
                ).fetchone()[0]
                == 605800
            ), "Retain the full seven-day cooldown"
            assert {
                row[0] for row in store.db.execute("SELECT error FROM attempts")
            } == {"response:error"}, "Do not persist private provider diagnostics"
    assert calls == {"preferred": 1, "alternate": 1}, "No retries during cooldown"

    now[0] += 31
    for _ in range(2):
        with cache() as store:
            result = store.translate(batch())
            assert result.requested_model == result.reported_model == "alternate"
    assert calls == {"preferred": 1, "alternate": 1 + int(alternate_down)}, (
        "Recover only missing work and reuse the accepted fallback on reopen"
    )


@pytest.mark.parametrize("error", [None, False, "", {}])
def test_success_when_error_field_empty_then_accept_translation(monkeypatch, error):
    body = response().json()
    body["error"] = error
    install_transport(monkeypatch, lambda _: httpx.Response(200, json=body))
    result = translate_batch(
        batch(), "preferred", base_url="https://example.test/v1", api_key="synthetic"
    )
    assert result.reported_model == "reported-route", (
        "Empty error fields are not outages"
    )


@pytest.mark.parametrize("error", ["Quota exhausted", {"reset_seconds": "nan"}])
def test_error_when_reset_missing_or_invalid_then_use_default_cooldown(
    monkeypatch, error
):
    install_transport(monkeypatch, lambda _: httpx.Response(200, json={"error": error}))
    with pytest.raises(ProviderUnavailable) as caught:
        translate_batch(
            batch(),
            "preferred",
            base_url="https://example.test/v1",
            api_key="synthetic",
        )
    assert caught.value.retry_after == 60, "Bad timing must use the bounded default"
    assert caught.value.reason == "response:error", "Do not echo upstream diagnostics"
