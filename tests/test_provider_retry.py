# this_file: tests/test_provider_retry.py
"""Structured provider delays must survive normalization and malformed hints."""

import pytest

from vexy_localizzy.provider_errors import retry_delay


def retry_info(value):
    return {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": value}


@pytest.mark.parametrize("wrapped", [False, True])
@pytest.mark.parametrize("value,expected", [("604800s", 604800), ("1.250s", 1.25)])
def test_google_delay_when_structured_then_preserve_duration(wrapped, value, expected):
    body = {"details": [retry_info(value)]}
    if wrapped:
        body = {"error": body}
    assert retry_delay({}, body) == expected, "Google reset duration must be honored"


@pytest.mark.parametrize("value", [None, [], {}, True, "nan", "-1", "0"])
def test_invalid_header_when_body_has_reset_then_use_body(value):
    assert retry_delay({"retry-after": value}, {"reset_seconds": 604800}) == 604800


@pytest.mark.parametrize(
    "value",
    [None, [], {}, True, "nans", "infs", "-1s", "0s", "1", "1e3s", "1.1234567890s"],
)
def test_invalid_google_delay_when_later_hint_valid_then_continue(value):
    body = {"details": [None, retry_info(value), retry_info("604800s")]}
    assert retry_delay({}, body) == 604800, "Bad metadata must not break fallback"


@pytest.mark.parametrize(
    "details", [None, {}, "604800s", [None, {}, {"retryDelay": "604800s"}]]
)
def test_unknown_details_when_no_valid_hint_then_use_default(details):
    assert retry_delay({}, {"details": details}) == 60


def test_timing_when_multiple_formats_then_keep_existing_precedence():
    body = {"reset_seconds": 300, "details": [retry_info("604800s")]}
    assert retry_delay({}, body) == 300
    assert retry_delay({"Retry-After": "120"}, body) == 120
    assert retry_delay({"retry-after-ms": "1500", "retry-after": "120"}, body) == 1.5


def test_boolean_reset_when_google_hint_exists_then_ignore_boolean():
    body = {"reset_seconds": True, "details": [retry_info("604800s")]}
    assert retry_delay({}, body) == 604800
