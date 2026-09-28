# this_file: tests/test_malformed_provider_fallback.py
"""Malformed successful HTTP responses must not abort translation fallback."""

import json
from collections import Counter

import httpx
import pytest
from test_abersetz_transport import install_transport, response
from translation_fixtures import batch

from vexy_localizzy.translate.abersetz_transport import translate_batch
from vexy_localizzy.translate.cache import TranslationCache


@pytest.mark.parametrize(
    "body",
    [
        {"model": "preferred", "choices": choices}
        for choices in (
            None,
            [],
            [{}],
            [{"message": None}],
            [{"message": {"content": ["invalid"]}}],
        )
    ]
    + [None, [], "Service unavailable", 123, True],
)
def test_malformed_envelope_when_primary_fails_then_fallback_and_cached_resume(
    tmp_path, monkeypatch, body
):
    calls = Counter()

    def handle(request):
        model = json.loads(request.content)["model"]
        calls[model] += 1
        if model == "alternate":
            return response(model=model)
        return httpx.Response(
            200, content=json.dumps(body), headers={"content-type": "application/json"}
        )

    install_transport(monkeypatch, handle)

    def request(model, value):
        return translate_batch(
            value, model, base_url="https://example.test/v1", api_key="synthetic"
        )

    for _ in range(2):
        with TranslationCache(
            tmp_path / "cache.sqlite",
            models=("preferred", "alternate"),
            request=request,
            endpoint_identity="https://example.test/v1",
            engine_identity="synthetic",
            validation_identity="synthetic",
            validate=lambda *_: None,
        ) as cache:
            result = cache.translate(batch())
            assert result.requested_model == "alternate", "Use a valid alternative"
    assert calls == {"preferred": 3, "alternate": 1}, (
        "Malformed retries must be bounded and completed fallback must be reused"
    )
