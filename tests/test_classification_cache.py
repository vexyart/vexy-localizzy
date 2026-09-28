# this_file: tests/test_classification_cache.py
"""Model response caching must preserve complete votes and retry only failures."""

from collections import Counter

import pytest

from vexy_localizzy.experimental.classification import Entry
from vexy_localizzy.experimental.classification_cache import CachedClassifier


def test_classifier_when_resumed_then_reuses_exact_prompt_model_coverage(tmp_path):
    calls = Counter()

    def request(model, system, data):
        calls[model] += 1
        return "300 A"

    path = tmp_path / "votes.sqlite"
    for coverage in ({"pl": 1}, {"pl": 1}, {"pl": 2}):
        with CachedClassifier(
            path,
            models=("one", "two", "three"),
            prompt="Rubric",
            coverage=coverage,
            request=request,
            endpoint_identity="synthetic",
        ) as classifier:
            assert classifier.classify([Entry(1, "Moon", ("pl",))])[1] == [
                "A",
                "A",
                "A",
            ]
    assert calls == {"one": 2, "two": 2, "three": 2}


def test_classifier_when_one_model_fails_then_preserves_other_votes(tmp_path):
    calls = Counter()

    def request(model, system, data):
        calls[model] += 1
        return "invalid" if model == "three" and calls[model] <= 3 else "300 B"

    with CachedClassifier(
        tmp_path / "votes.sqlite",
        models=("one", "two", "three"),
        prompt="Rubric",
        coverage={},
        request=request,
        endpoint_identity="synthetic",
    ) as classifier:
        with pytest.raises(RuntimeError, match="three"):
            classifier.classify([Entry(1, "Moon", ("pl",))])
        assert classifier.classify([Entry(1, "Moon", ("pl",))])[1] == ["B", "B", "B"]
        assert calls == {"one": 1, "two": 1, "three": 4}
        assert classifier.db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 6
