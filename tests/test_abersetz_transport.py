# this_file: tests/test_abersetz_transport.py
"""Published abersetz + real SDK contracts without provider network requests."""

import json

import httpx
import openai
import pytest
from translation_fixtures import batch

from vexy_localizzy.translate.abersetz_transport import translate_batch
from vexy_localizzy.translate.provider_errors import ProviderUnavailable


def install_transport(monkeypatch, handle):
    original = openai.OpenAI
    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: original(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handle))
        ),
    )


def response(content=None, model="reported-route"):
    content = (
        content
        if content is not None
        else '<output>[{"id":"first","target":"Przesuń %1."},{"id":"second","target":"Linia bazowa"}]</output><voc>{"point":"punkt"}</voc>'
    )
    return httpx.Response(
        200,
        json={
            "id": "test",
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
        },
    )


@pytest.mark.parametrize("temperature", [0.0, 0.2, 0.7])
def test_published_adapter_passes_context_and_retains_reported_model(
    monkeypatch, temperature
):
    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        return response()

    install_transport(monkeypatch, handle)
    result = translate_batch(
        batch(),
        "preferred",
        base_url="https://example.test/v1",
        api_key="synthetic",
        temperature=temperature,
    )
    assert (
        result.requested_model == "preferred"
        and result.reported_model == "reported-route"
    )
    assert result.targets == {"first": "Przesuń %1.", "second": "Linia bazowa"}
    assert result.vocabulary["point"] == "punkt"
    assert len(calls) == 1
    assert calls[0]["temperature"] == temperature
    messages = json.dumps(calls[0]["messages"], ensure_ascii=False)
    for text in (
        "Dialog",
        "Menu",
        "Use concise commands.",
        "linia bazowa",
        "Zaznacz punkt.",
        "memory:7",
        "first",
    ):
        assert text in messages


@pytest.mark.parametrize(
    "failure", ["quota", "google-quota", "connection", "server", "envelope-quota"]
)
def test_provider_failure_is_not_retried_inside_abersetz_or_sdk(monkeypatch, failure):
    calls = []

    def handle(request):
        calls.append(request)
        if failure == "connection":
            raise httpx.ConnectError("Offline", request=request)
        if failure == "google-quota":
            return httpx.Response(
                429,
                json={
                    "error": {
                        "details": [
                            {
                                "@type": "type.googleapis.com/google.rpc.RetryInfo",
                                "retryDelay": "604800s",
                            }
                        ]
                    }
                },
            )
        return httpx.Response(
            200 if failure == "envelope-quota" else 429 if failure == "quota" else 503,
            headers={"retry-after": "604800"},
            json={"error": {"message": "Unavailable"}},
        )

    install_transport(monkeypatch, handle)
    with pytest.raises(ProviderUnavailable) as caught:
        translate_batch(
            batch(),
            "preferred",
            base_url="https://example.test/v1",
            api_key="synthetic",
        )
    assert len(calls) == 1
    assert caught.value.retry_after == (30 if failure == "connection" else 604800)


@pytest.mark.parametrize(
    "text",
    [
        "commentary",
        "<output>[]</output>",
        '<output>[{"id":"first","target":"x"}]</output>',
    ],
)
def test_incomplete_or_malformed_output_is_rejected(monkeypatch, text):
    install_transport(monkeypatch, lambda _: response(text))
    with pytest.raises(ValueError):
        translate_batch(
            batch(),
            "preferred",
            base_url="https://example.test/v1",
            api_key="synthetic",
        )


def test_oversize_request_fails_before_network(monkeypatch):
    install_transport(
        monkeypatch, lambda _: pytest.fail("Oversized input must not reach network")
    )
    with pytest.raises(ValueError, match="budget"):
        translate_batch(
            batch(),
            "preferred",
            base_url="https://example.test/v1",
            api_key="synthetic",
            max_request_bytes=10,
        )


def test_missing_reported_model_is_rejected(monkeypatch):
    install_transport(monkeypatch, lambda _: response(model=""))
    with pytest.raises(ValueError, match="model"):
        translate_batch(
            batch(),
            "preferred",
            base_url="https://example.test/v1",
            api_key="synthetic",
        )


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), 0, -1])
def test_timeout_must_be_finite_positive_before_network(monkeypatch, timeout):
    install_transport(monkeypatch, lambda _: pytest.fail("Invalid timeout"))
    with pytest.raises(ValueError, match="timeout"):
        translate_batch(
            batch(),
            "preferred",
            base_url="https://example.test/v1",
            api_key="synthetic",
            timeout=timeout,
        )


@pytest.mark.parametrize("temperature", [-1, 3, float("inf"), float("nan")])
def test_temperature_when_invalid_then_no_network(monkeypatch, temperature):
    install_transport(monkeypatch, lambda _: pytest.fail("Invalid temperature"))
    with pytest.raises(ValueError, match="Temperature"):
        translate_batch(
            batch(),
            "preferred",
            base_url="https://example.test/v1",
            api_key="synthetic",
            temperature=temperature,
        )
