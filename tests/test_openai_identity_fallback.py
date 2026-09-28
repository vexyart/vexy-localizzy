# this_file: tests/test_openai_identity_fallback.py
"""Malformed provider responses cannot break fallback or become cached votes."""

import json
from collections import Counter

import httpx
import openai
import pytest

from vexy_localizzy.classification import Entry
from vexy_localizzy.classification_cache import CachedClassifier
from vexy_localizzy.openai_transport import chat_request


@pytest.mark.parametrize(
    "reported_model,reported_content",
    [
        ("   ", "300 A"),
        (123, "300 A"),
        ("primary", ["300 A"]),
        ("primary", {"text": "300 A"}),
        ("primary", 123),
        ("primary", True),
    ],
)
def test_fallback_when_provider_response_invalid_then_alternative_is_cached(
    tmp_path, monkeypatch, reported_model, reported_content
):
    calls = Counter()
    client = openai.OpenAI

    def handle(request):
        model = json.loads(request.content)["model"]
        calls[model] += 1
        return httpx.Response(
            200,
            json={
                "id": "synthetic",
                "object": "chat.completion",
                "created": 0,
                "model": reported_model if model == "primary" else model,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": reported_content
                            if model == "primary"
                            else "300 A",
                        },
                    }
                ],
            },
        )

    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: client(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handle))
        ),
    )

    def request(model, system, payload):
        return chat_request(
            model,
            system,
            payload,
            base_url="https://example.test/v1",
            api_key="synthetic",
        )

    for _ in range(2):
        with CachedClassifier(
            tmp_path / "cache.sqlite",
            models=("one", "two", "primary"),
            prompt="Rubric",
            coverage={},
            request=request,
            endpoint_identity="https://example.test/v1",
            fallbacks={"primary": ("alternate",)},
        ) as cache:
            result = cache.classify_detailed([Entry(1, "Alpha", ())])
            assert result.models == ("one", "two", "alternate"), (
                "A malformed provider response must not count as a distinct vote"
            )
            assert result.reported_models == result.models
            assert result.identity_verified
    assert calls == {"one": 1, "two": 1, "primary": 3, "alternate": 1}, (
        "Malformed responses have bounded retries; reopening reuses all valid votes"
    )
