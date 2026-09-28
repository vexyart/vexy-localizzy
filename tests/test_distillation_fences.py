# this_file: tests/test_distillation_fences.py
"""A complete JSON code block is presentation; the selection contract stays strict."""

import pytest

from vexy_localizzy.experimental.distillation import parse_selection

VOTE = '{"keep":[300,301],"drop":[]}'


@pytest.mark.parametrize(
    "response",
    [
        "```json\n" + VOTE + "\n```",
        "```\n" + VOTE + "\n```",
        " \n```json\r\n" + VOTE + "\r\n```\t ",
    ],
)
def test_selection_when_one_json_code_block_then_validate_complete_vote(response):
    assert parse_selection(response, 2).keep == [300, 301]


@pytest.mark.parametrize(
    "response",
    [
        "Explanation\n```json\n" + VOTE + "\n```",
        "```json\n" + VOTE + "\n```\nExplanation",
        "```javascript\n" + VOTE + "\n```",
        "```json\n" + VOTE + "\n```\n```json\n" + VOTE + "\n```",
        '```json\n{"keep":[300],"keep":[300,301],"drop":[]}\n```',
        '```json\n{"keep":[300],"drop":[]}\n```',
        '```json\n{"keep":[300,301],"drop":[],"extra":true}\n```',
        '```json\n{"keep":[300],"drop":[{"id":301,"representative":999,"equivalent":true,"reason":"Same"}]}\n```',
        "```json\n" + VOTE,
    ],
)
def test_selection_when_wrapper_or_vote_invalid_then_refuse(response):
    with pytest.raises(ValueError):
        parse_selection(response, 2)


def test_selection_when_fence_pushes_response_over_limit_then_refuse():
    response = "```json\n" + " " * 32000 + VOTE + "\n```"
    with pytest.raises(ValueError, match="byte budget"):
        parse_selection(response, 2)
