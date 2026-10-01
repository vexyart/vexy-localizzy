# this_file: src/vexy_localizzy/editorial/review_request.py
"""Send one review batch to an OpenAI-compatible endpoint and parse the corrections.

``endpoint_request`` is the seam: it returns a ``(system, user) -> ModelResponse``
callable, and tests substitute their own. It follows the abersetz transport:
an ``OpenAI`` client per attempt, no SDK retries, provider failures normalized
by ``provider_failures`` and proxy error envelopes refused by
``completion_request``. ``chat_request`` is not reused because it takes no
temperature. The ``openai`` package comes with the ``llm`` or ``translation``
extra and is imported when a request is built.
"""

import math
import os
import time
from collections.abc import Callable

from vexy_localizzy.editorial.review_prompt import parse_corrections, user_message
from vexy_localizzy.translate.provider_errors import ModelResponse

Request = Callable[[str, str], ModelResponse]

ATTEMPTS = 3
RETRY_DELAYS = (2.0, 5.0)


def endpoint_request(
    endpoint: str, model: str, *, api_key_env: str, temperature: float, timeout: float
) -> Request:
    """A single-attempt request to ``model`` at ``endpoint``; ValueError on bad settings."""
    import openai  # noqa: F401 - fail now, not once per batch, without the extra

    api_key = os.environ.get(api_key_env, "")
    if not api_key.strip():
        raise ValueError(f"Set the {api_key_env} environment variable")
    if not math.isfinite(temperature) or not 0 <= temperature <= 2:
        raise ValueError("Temperature must be finite and between zero and two")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Timeout must be a positive number of seconds")

    def request(system: str, user: str) -> ModelResponse:
        from openai import OpenAI

        from vexy_localizzy.translate.openai_transport import (
            completion_request,
            provider_failures,
        )

        with (
            provider_failures(),
            OpenAI(
                base_url=endpoint, api_key=api_key, timeout=timeout, max_retries=0
            ) as api,
        ):
            response = completion_request(
                api,
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            content = response.choices[0].message.content or ""
            return ModelResponse(content, response.model or model)

    return request


def review_batch(
    request: Request,
    system: str,
    rows: list[dict],
    terms: dict[str, str],
    language: str,
    *,
    sleep: Callable[[float], None] | None = None,
) -> tuple[list, str]:
    """Corrections for one batch and the reported model; RuntimeError after ATTEMPTS.

    Short fixed delays only: a provider asking for minutes is better served by
    re-running later, since finished batches are skipped on resume.
    """
    user = user_message(rows, terms, language)
    last: Exception | None = None
    for attempt in range(ATTEMPTS):
        if attempt:
            (sleep or time.sleep)(RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)])
        try:
            response = request(system, user)
            return parse_corrections(response.content), response.reported_model
        except Exception as error:  # noqa: BLE001 - retried, then reported
            last = error
    raise RuntimeError(f"batch failed after {ATTEMPTS} attempts: {last}")
