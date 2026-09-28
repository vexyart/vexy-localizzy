# this_file: tests/test_classification_run.py
"""Bounded scheduling, graceful pending batches and sealed zero-call resume."""

import json
import sqlite3
from collections import Counter
from threading import Lock

import pytest
from classification_run_fixtures import options, response, write_inputs

from vexy_localizzy.classification_results import validated_results
from vexy_localizzy.classification_run import run_classification
from vexy_localizzy.provider_errors import ProviderUnavailable


def test_run_when_all_batches_finish_then_sealed_complete_and_zero_call_resume(
    tmp_path,
):
    inputs, run = write_inputs(tmp_path / "input.jsonl"), tmp_path / "run"
    config = options(tmp_path)
    calls = Counter()
    mutex = Lock()

    def request(model, prompt, payload):
        with mutex:
            calls[model] += 1
        return response(model, prompt, payload)

    config.update(request=request, workers=2)
    result = run_classification(inputs, run, **config)
    assert result["complete"] and result["entries"] == 201
    assert calls == {"one": 3, "two": 3, "three": 3}
    with validated_results(run, inputs) as checked:
        assert list(checked.selected_ids()) == list(range(1, 202))
        assert checked.report["decision_sha256"] == result["decision_sha256"]
    assert run_classification(inputs, run, **config) == result
    assert calls == {"one": 3, "two": 3, "three": 3}, (
        "Complete reopen must not request votes"
    )


def test_run_when_one_batch_malformed_then_others_finish_and_only_missing_vote_retried(
    tmp_path,
):
    inputs, run = write_inputs(tmp_path / "input.jsonl"), tmp_path / "run"
    config = options(tmp_path)
    calls = Counter()
    broken = [True]

    def request(model, prompt, payload):
        first = json.loads(payload)["entries"][0]["source"]
        calls[model, first] += 1
        if model == "three" and first == "Source 100" and broken[0]:
            return "malformed"
        return response(model, prompt, payload)

    config["request"] = request
    result = run_classification(inputs, run, **config)
    assert (
        not result["complete"]
        and result["entries"] == 101
        and result["pending_entries"] == 100
    )
    assert not (run / "complete.json").exists()
    before = calls.copy()
    broken[0] = False
    result = run_classification(inputs, run, **config)
    assert result["complete"] and result["entries"] == 201
    assert calls - before == {("three", "Source 100"): 1}
    with sqlite3.connect(run / "decisions.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM pending_batches").fetchone()[0] == 0
    assert not (run / "pending.json").exists()


def test_run_when_primary_quota_exhausted_then_fallback_all_batches_without_sleep(
    tmp_path,
):
    inputs, run = write_inputs(tmp_path / "input.jsonl"), tmp_path / "run"
    config = options(tmp_path)
    calls = Counter()

    def request(model, prompt, payload):
        calls[model] += 1
        if model == "three":
            raise ProviderUnavailable("quota", retry_after=600000)
        return response(model, prompt, payload)

    config.update(request=request, fallbacks={"three": ["spare"]})
    result = run_classification(inputs, run, **config)
    assert result["complete"] and calls["three"] == 1 and calls["spare"] == 3
    with sqlite3.connect(run / "decisions.sqlite") as db:
        models = {
            tuple(json.loads(row[0]))
            for row in db.execute("SELECT models FROM decision_models")
        }
    assert models == {("one", "two", "spare")}


def test_run_when_interrupted_then_completed_batch_and_cached_votes_survive(tmp_path):
    inputs, run = write_inputs(tmp_path / "input.jsonl"), tmp_path / "run"
    config = options(tmp_path)
    interrupted = [True]
    calls = Counter()

    def request(model, prompt, payload):
        first = json.loads(payload)["entries"][0]["source"]
        calls[model, first] += 1
        if model == "three" and first == "Source 100" and interrupted[0]:
            raise KeyboardInterrupt
        return response(model, prompt, payload)

    config["request"] = request
    with pytest.raises(KeyboardInterrupt):
        run_classification(inputs, run, **config)
    assert not (run / "complete.json").exists()
    with sqlite3.connect(run / "decisions.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 100
    before = calls.copy()
    interrupted[0] = False
    result = run_classification(inputs, run, **config)
    assert result["complete"]
    assert all(calls[k] == v for k, v in before.items() if k[1] == "Source 0")


@pytest.mark.parametrize("count", [0, 1, 100, 101])
def test_run_when_input_boundary_then_exact_completion(tmp_path, count):
    inputs, run = write_inputs(tmp_path / "input.jsonl", count), tmp_path / "run"
    result = run_classification(inputs, run, **options(tmp_path))
    assert result["complete"] and result["entries"] == count
    with validated_results(run, inputs) as checked:
        assert checked.report["entries"] == count
