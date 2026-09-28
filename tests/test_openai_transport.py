# this_file: tests/test_openai_transport.py
"""Exercise the installed SDK against deterministic HTTP failures."""

import json
from collections import Counter

import pytest

from vexy_localizzy.classification import Entry
from vexy_localizzy.classification_cache import CachedClassifier
from vexy_localizzy.translate.openai_transport import chat_request
from vexy_localizzy.translate.provider_errors import ModelResponse, ProviderUnavailable

openai = pytest.importorskip("openai")
httpx = pytest.importorskip("httpx")


@pytest.mark.parametrize(
    "status,headers,body,delay",
    [
        (429, {"retry-after": "600000"}, {"error": {"code": "quota"}}, 600000),
        (503, {"retry-after": "120"}, {"error": {"message": "Unavailable"}}, 120),
        (402, {}, {"error": {"message": "Billing"}}, 300),
    ],
)
def test_transport_when_provider_unavailable_then_one_sdk_attempt_with_retry_timing(
    monkeypatch, status, headers, body, delay
):
    calls = []
    real_client = openai.OpenAI

    def handle(request):
        calls.append(request)
        return httpx.Response(status, headers=headers, json=body)

    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: real_client(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handle))
        ),
    )
    with pytest.raises(ProviderUnavailable) as error:
        chat_request(
            "model",
            "rubric",
            "payload",
            base_url="https://example.test/v1",
            api_key="synthetic",
        )
    assert error.value.retry_after == delay
    assert error.value.reason == f"http:{status}"
    assert len(calls) == 1, "The SDK must not sleep/retry before fallback selection"


def test_transport_when_connection_fails_then_bounded_cooldown(monkeypatch):
    real_client = openai.OpenAI

    def handle(request):
        raise httpx.ConnectError("Offline", request=request)

    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: real_client(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handle))
        ),
    )
    with pytest.raises(ProviderUnavailable) as error:
        chat_request(
            "model",
            "rubric",
            "payload",
            base_url="https://example.test/v1",
            api_key="synthetic",
        )
    assert error.value.retry_after == 30


def test_transport_when_successful_then_exact_content_returned(monkeypatch):
    real_client = openai.OpenAI
    response = {
        "id": "synthetic",
        "object": "chat.completion",
        "created": 0,
        "model": "model",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "300 A"},
            }
        ],
    }
    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: real_client(
            **kwargs,
            http_client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda _: httpx.Response(200, json=response)
                )
            ),
        ),
    )
    assert chat_request(
        "model",
        "rubric",
        "payload",
        base_url="https://example.test/v1",
        api_key="synthetic",
    ) == ModelResponse("300 A", "model")


@pytest.mark.parametrize(
    "headers,body",
    [
        ({"retry-after": "598850"}, {"code": "model_cooldown"}),
        ({}, {"code": "model_cooldown", "reset_seconds": 598850}),
        (
            {},
            {
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.RetryInfo",
                        "retryDelay": "598850s",
                    }
                ]
            },
        ),
    ],
)
@pytest.mark.parametrize("status", [200, 429])
def test_quota_when_http_transport_falls_back_then_reopen_reuses_votes_and_cooldown(
    tmp_path, monkeypatch, headers, body, status
):
    calls = Counter()
    real_client = openai.OpenAI

    def handle(request):
        model = json.loads(request.content)["model"]
        calls[model] += 1
        if model == "preferred":
            return httpx.Response(
                status,
                headers=headers,
                json={"error": body},
            )
        return httpx.Response(
            200,
            json={
                "id": "synthetic",
                "object": "chat.completion",
                "created": 0,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "300 A"},
                    }
                ],
            },
        )

    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: real_client(
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

    for entry in (Entry(1, "Alpha", ()), Entry(1, "Alpha", ()), Entry(2, "Beta", ())):
        with CachedClassifier(
            tmp_path / "cache.sqlite",
            models=("one", "two", "preferred"),
            prompt="Rubric",
            coverage={},
            request=request,
            endpoint_identity="https://example.test/v1",
            fallbacks={"preferred": ("alternate",)},
            clock=lambda: 1000,
        ) as cache:
            result = cache.classify_detailed([entry])
            assert result.models == ("one", "two", "alternate")
            assert result.reported_models == result.models
            assert result.identity_verified
            assert result.votes == {entry.id: ["A", "A", "A"]}
            assert (
                cache.db.execute(
                    "SELECT until FROM cooldowns WHERE model='preferred'"
                ).fetchone()[0]
                == 599850
            )
    assert calls == {"one": 2, "two": 2, "preferred": 1, "alternate": 2}, (
        "Resume must reuse completed votes; new work must skip the exhausted provider"
    )
