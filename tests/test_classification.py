# this_file: tests/test_classification.py
"""Strict numbered classification and conservative rare-language consensus."""

import pytest

from vexy_localizzy.experimental.classification import (
    Entry,
    batches,
    consensus,
    parse_votes,
    request_text,
)


@pytest.mark.parametrize(
    "response",
    ["300 A\n300 B", "300 A\n302 B", "300 A\n301 D", "300 A\n301 B\nDone.", "300 A"],
)
def test_votes_when_invalid_numbering_or_text_then_rejects(response):
    with pytest.raises(ValueError):
        parse_votes(response, 2)


def test_votes_when_exact_complete_then_accepts():
    assert parse_votes("301 B\n300 A", 2) == ["A", "B"]


def test_batches_when_hundred_limit_then_restarts_numbering():
    items = [Entry(i, f"item{i}", ("pl",)) for i in range(101)]
    groups = list(batches(items))
    assert [len(group) for group in groups] == [100, 1]
    assert '"number":300' in request_text(groups[1], {"pl": 10})


def test_batches_when_entry_exceeds_budget_then_does_not_truncate():
    with pytest.raises(ValueError, match="budget"):
        list(batches([Entry(1, "x" * 1000, ("pl",))], max_bytes=100))


@pytest.mark.parametrize(
    ("votes", "locales", "expected"),
    [
        (["A", "B", "C"], ("de",), "A"),
        (["C", "C", "B"], ("cy",), "B"),
        (["C", "C", "C"], ("cy",), "C"),
        (["C", "C", "B"], ("de",), "C"),
    ],
)
def test_consensus_when_disagreement_then_protects_useful_rare_coverage(
    votes, locales, expected
):
    assert consensus(votes, locales, {"cy"})["class"] == expected


def test_consensus_when_vote_missing_then_leaves_decision_pending():
    with pytest.raises(ValueError):
        consensus(["A", "B"], ("pl",), set())
