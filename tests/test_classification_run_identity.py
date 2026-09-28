# this_file: tests/test_classification_run_identity.py
"""Bounded transport concurrency and source/model provenance during resume."""

import json
from threading import Barrier, Lock

import pytest
from classification_run_fixtures import options, response, write_inputs

from vexy_localizzy.classification_results import validated_results
from vexy_localizzy.classification_run import run_classification


def test_run_when_two_workers_then_at_most_six_model_requests_in_flight(tmp_path):
    inputs, run = write_inputs(tmp_path / "input.jsonl"), tmp_path / "run"
    config = options(tmp_path)
    lock = Lock()
    barrier = Barrier(6)
    active = peak = 0

    def request(model, prompt, payload):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            if json.loads(payload)["entries"][0]["source"] != "Source 200":
                barrier.wait(timeout=5)
            return response(model, prompt, payload)
        finally:
            with lock:
                active -= 1

    result = run_classification(
        inputs, run, **{**config, "request": request, "workers": 2}
    )
    assert result["complete"] and peak == 6 and active == 0


def test_run_when_cached_reports_unknown_then_explicit_identity_map_allows_new_run_without_calls(
    tmp_path,
):
    inputs = write_inputs(tmp_path / "input.jsonl", 1)
    config = options(tmp_path)
    calls = []

    def request(*args):
        calls.append(args[0])
        return "300 A"

    config["request"] = request
    assert not run_classification(inputs, tmp_path / "unknown", **config)["complete"]
    config["model_identities"] = {model: model for model in config["models"]}
    assert run_classification(inputs, tmp_path / "resolved", **config)["complete"]
    assert len(calls) == 3
    with validated_results(tmp_path / "resolved", inputs) as results:
        assert results.report["fully_reported_entries"] == 0


def test_run_when_input_changes_during_request_then_no_completion_until_original_restored(
    tmp_path,
):
    inputs, run = write_inputs(tmp_path / "input.jsonl", 1), tmp_path / "run"
    original = inputs.read_bytes()
    config = options(tmp_path)
    calls = []

    def request(model, prompt, payload):
        calls.append(model)
        if model == "one":
            inputs.write_bytes(original.replace(b"Source 0", b"Changed!"))
        return response(model, prompt, payload)

    config["request"] = request
    with pytest.raises(ValueError, match="input"):
        run_classification(inputs, run, **config)
    assert not (run / "complete.json").exists()
    inputs.write_bytes(original)
    assert run_classification(inputs, run, **config)["complete"]
    assert len(calls) == 3


def test_run_when_input_changes_after_preflight_then_no_poisoned_checkpoint_and_resume_works(
    tmp_path, monkeypatch
):
    from vexy_localizzy import classification_run

    inputs, run = write_inputs(tmp_path / "input.jsonl", 1), tmp_path / "run"
    original_input = inputs.read_bytes()
    config = options(tmp_path)
    calls = []

    def request(*args):
        calls.append(args[0])
        return response(*args)

    config["request"] = request
    schedule = classification_run.run_batches

    def changed_input(*args, **kwargs):
        inputs.write_bytes(original_input.replace(b"Source 0", b"Changed!"))
        return schedule(*args, **kwargs)

    monkeypatch.setattr(classification_run, "run_batches", changed_input)
    with pytest.raises(ValueError):
        run_classification(inputs, run, **config)
    assert calls == [], "A changed payload must be rejected before it reaches any model"
    inputs.write_bytes(original_input)
    monkeypatch.setattr(classification_run, "run_batches", schedule)
    assert run_classification(inputs, run, **config)["complete"]


def test_run_when_entry_exceeds_batch_target_but_fits_request_then_singleton_without_truncation(
    tmp_path,
):
    inputs, run = write_inputs(tmp_path / "input.jsonl", 3), tmp_path / "run"
    rows = [json.loads(line) for line in inputs.read_text().splitlines()]
    rows[2]["text"] = "Long source " + ("x" * 54300)
    inputs.write_text("".join(json.dumps(row) + "\n" for row in rows))
    seen = []
    config = options(tmp_path)

    def request(model, prompt, payload):
        entries = json.loads(payload)["entries"]
        if model == "one":
            seen.append([row["source"] for row in entries])
        assert len(prompt.encode()) + len(payload.encode()) <= 64000
        return response(model, prompt, payload)

    assert run_classification(inputs, run, **{**config, "request": request})["complete"]
    assert seen == [["Source 0"], [rows[2]["text"]], ["Source 2"]]
