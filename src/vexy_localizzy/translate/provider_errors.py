# this_file: src/vexy_localizzy/translate/provider_errors.py
"""Portable provider failures and HTTP retry timing, without SDK coupling."""

import math
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass
from email.utils import parsedate_to_datetime


@dataclass(frozen=True)
class ModelResponse:
    """Content and the model identity reported by the serving provider."""

    content: str
    reported_model: str

    def __post_init__(self):
        if not isinstance(self.content, str):
            raise ValueError("Provider response content must be text")
        if not isinstance(self.reported_model, str) or not self.reported_model.strip():
            raise ValueError("A provider-reported model identity is required")


class ProviderUnavailable(RuntimeError):
    """Transport reports a temporary outage or exhausted provider quota."""

    def __init__(self, reason: str, *, retry_after: float = 60):
        if not math.isfinite(retry_after) or retry_after <= 0:
            raise ValueError("Provider retry delay must be finite and positive")
        self.reason = reason
        self.retry_after = retry_after
        super().__init__(reason)


def _google_delays(body: dict) -> Iterator[str]:
    """Read RetryInfo's ProtoJSON Duration without interpreting free-form messages."""
    details = body.get("details")
    if not isinstance(details, list):
        return
    for detail in details:
        if not isinstance(detail, dict) or detail.get("@type") != (
            "type.googleapis.com/google.rpc.RetryInfo"
        ):
            continue
        value = detail.get("retryDelay")
        if isinstance(value, str) and re.fullmatch(r"[0-9]+(?:\.[0-9]{1,9})?s", value):
            yield value[:-1]


def retry_delay(headers, body=None, *, now=None, default=60) -> float:
    """Prefer retry headers, then gateway reset_seconds, then Google RetryInfo."""
    headers = {key.lower(): value for key, value in headers.items()}
    now = time.time() if now is None else now
    candidates = [
        (headers.get("retry-after-ms"), 0.001, False),
        (headers.get("retry-after"), 1, True),
    ]
    if isinstance(body, dict):
        envelopes = [body]
        if isinstance(body.get("error"), dict):
            envelopes.append(body["error"])
        candidates.extend((item.get("reset_seconds"), 1, False) for item in envelopes)
        candidates.extend(
            (value, 1, False) for item in envelopes for value in _google_delays(item)
        )
    for value, multiplier, allow_date in candidates:
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            continue
        try:
            seconds = float(value) * multiplier
        except (ValueError, TypeError, OverflowError):
            if not allow_date or not isinstance(value, str):
                continue
            try:
                seconds = parsedate_to_datetime(value).timestamp() - now
            except (ValueError, TypeError, OverflowError):
                continue
        if math.isfinite(seconds) and seconds > 0:
            return seconds
    return default
