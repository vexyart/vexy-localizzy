# this_file: tests/test_icu_bridge.py
"""The ICU subprocess boundary must fail closed without retrying broken tooling."""

import sys

import pytest
from translation_fixtures import batch, reply

from vexy_localizzy.qa.icu import check_pairs, validate_batch


def command(output):
    return [sys.executable, "-c", f"print({output!r})"]


def test_pairs_when_valid_then_return_ordered_findings():
    assert check_pairs([("{x}", "{x}", "pl")], command=command("[[]]")) == [[]]


@pytest.mark.parametrize("output", ["[]", "{}", "[null]", "[[1]]", "invalid"])
def test_pairs_when_bridge_output_invalid_then_tooling_error(output):
    with pytest.raises(RuntimeError, match="ICU"):
        check_pairs([("{x}", "{x}", "pl")], command=command(output))


def test_pairs_when_tool_missing_then_tooling_error():
    with pytest.raises(RuntimeError, match="ICU"):
        check_pairs([("a", "b", "pl")], command=["/missing-localizzy-icu"])


def test_pairs_when_tool_timeout_then_tooling_error():
    with pytest.raises(RuntimeError, match="ICU"):
        check_pairs(
            [("a", "b", "pl")],
            command=[sys.executable, "-c", "import time; time.sleep(10)"],
            timeout=0.01,
        )


def test_validation_when_mismatch_then_candidate_rejected():
    with pytest.raises(ValueError, match="first.*argument"):
        validate_batch(
            batch(),
            reply("test", batch()),
            command=command('[["argument mismatch"],[]]'),
        )


def test_validation_when_valid_then_cache_callback_accepts():
    assert (
        validate_batch(batch(), reply("test", batch()), command=command("[[],[]]"))
        is None
    )


def test_pairs_when_empty_then_no_tool_required():
    assert check_pairs([], command=["/missing-localizzy-icu"]) == []
