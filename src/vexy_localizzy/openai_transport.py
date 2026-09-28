# this_file: src/vexy_localizzy/openai_transport.py
"""Optional OpenAI-compatible transport with explicit provider failure timing."""

from contextlib import contextmanager

from vexy_localizzy.provider_errors import (
    ModelResponse,
    ProviderUnavailable,
    retry_delay,
)


@contextmanager
def provider_failures():
    """Normalize SDK failures without logging credentials or sleeping for reset."""
    from openai import APIConnectionError, APIStatusError

    try:
        yield
    except APIStatusError as error:
        delay = retry_delay(
            error.response.headers,
            error.body,
            default=300 if error.status_code in (401, 402, 403, 404) else 60,
        )
        raise ProviderUnavailable(
            f"http:{error.status_code}", retry_after=delay
        ) from error
    except APIConnectionError as error:
        raise ProviderUnavailable(type(error).__name__, retry_after=30) from error


def completion_request(api, **kwargs):
    """Reject proxy error envelopes even on HTTP success, retaining retry headers."""
    raw = api.chat.completions.with_raw_response.create(**kwargs)
    response = raw.parse()
    body = getattr(response, "model_extra", None)
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, (dict, str)) and error:
        # Keep provider text out of persistent error logs; it may echo input/secrets.
        raise ProviderUnavailable(
            "response:error", retry_after=retry_delay(raw.headers, body)
        )
    return response


def chat_request(model, system, payload, *, base_url, api_key, timeout=60):
    """One bounded SDK attempt; the caller controls retries and model selection."""
    from openai import OpenAI

    with (
        provider_failures(),
        OpenAI(
            base_url=base_url, api_key=api_key, timeout=timeout, max_retries=0
        ) as api,
    ):
        response = completion_request(
            api,
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": payload},
            ],
        )
        return ModelResponse(response.choices[0].message.content or "", response.model)
