# this_file: tests/test_classification_run_failures.py
"""Fail before requests on bad input; preserve atomic checkpoints through faults."""

import json
import sqlite3
from pathlib import Path

import pytest
from classification_run_fixtures import options, response, write_inputs
from filelock import FileLock, Timeout

from vexy_localizzy.experimental.classification_run import run_classification


@pytest.mark.parametrize(
    "damage", ["count", "coverage", "duplicate_id", "huge_entry", "zero_workers"]
)
def test_run_when_input_invalid_then_no_model_calls(tmp_path, damage):
    inputs, run = write_inputs(tmp_path / "input.jsonl", 2), tmp_path / "run"
    rows = [json.loads(s) for s in inputs.read_text().splitlines()]
    config = options(tmp_path)
    calls = []
    if damage == "count":
        rows[0]["entries"] = 3
    elif damage == "coverage":
        rows[0]["coverage"]["pl"] = 3
    elif damage == "duplicate_id":
        rows[2]["id"] = 1
    elif damage == "huge_entry":
        rows[1]["text"] = "x" * 65000
    else:
        config["workers"] = 0
    inputs.write_text("".join(json.dumps(r) + "\n" for r in rows))
    config["request"] = lambda *args: calls.append(args)
    with pytest.raises(ValueError):
        run_classification(inputs, run, **config)
    assert calls == [] and not (run / "complete.json").exists()
    assert not config["cache_path"].exists()


@pytest.mark.parametrize(
    "change",
    [
        {"prompt": "Changed rubric"},
        {"batch_bytes": 47000},
        {"models": ["one", "two", "spare"]},
    ],
)
def test_run_when_policy_changes_then_existing_directory_refused(tmp_path, change):
    inputs, run = write_inputs(tmp_path / "input.jsonl", 1), tmp_path / "run"
    config = options(tmp_path)
    run_classification(inputs, run, **config)
    before = (run / "complete.json").read_bytes()
    config.update(change)
    with pytest.raises(ValueError, match="identity changed"):
        run_classification(inputs, run, **config)
    assert (run / "complete.json").read_bytes() == before


def test_run_when_batch_save_fails_then_no_partial_decisions_and_cached_votes_survive(
    tmp_path, monkeypatch
):
    from vexy_localizzy.experimental import classification_schedule

    inputs, run = write_inputs(tmp_path / "input.jsonl", 1), tmp_path / "run"
    config = options(tmp_path)
    calls = []

    def request(*args):
        calls.append(args[0])
        return response(*args)

    config["request"] = request
    original = classification_schedule.save_batch

    def fail_save(db, *args):
        db.execute(
            "CREATE TEMP TRIGGER fail_model BEFORE INSERT ON decision_models BEGIN SELECT RAISE(ABORT,'injected failure'); END"
        )
        return original(db, *args)

    monkeypatch.setattr(classification_schedule, "save_batch", fail_save)
    with pytest.raises(sqlite3.IntegrityError, match="injected failure"):
        run_classification(inputs, run, **config)
    with sqlite3.connect(run / "decisions.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM completed_batches").fetchone()[0] == 0
    monkeypatch.setattr(classification_schedule, "save_batch", original)
    result = run_classification(inputs, run, **config)
    assert result["complete"] and len(calls) == 3


def test_run_when_marker_publication_fails_then_resume_seals_without_requests(
    tmp_path, monkeypatch
):
    from vexy_localizzy.experimental import classification_run_store

    inputs, run = write_inputs(tmp_path / "input.jsonl", 1), tmp_path / "run"
    config = options(tmp_path)
    calls = []

    def request(*args):
        calls.append(args[0])
        return response(*args)

    config["request"] = request
    original = classification_run_store.os.replace

    def replace(source, target):
        if Path(target).name == "complete.json":
            raise OSError("injected publication failure")
        return original(source, target)

    monkeypatch.setattr(classification_run_store.os, "replace", replace)
    with pytest.raises(OSError, match="publication"):
        run_classification(inputs, run, **config)
    assert not (run / "complete.json").exists()
    monkeypatch.setattr(classification_run_store.os, "replace", original)
    assert run_classification(inputs, run, **config)["complete"]
    assert len(calls) == 3


def test_run_when_partial_decisions_corrupted_consistently_then_checkpoint_refuses(
    tmp_path,
):
    inputs, run = write_inputs(tmp_path / "input.jsonl", 101), tmp_path / "run"
    config = options(tmp_path)

    def request(model, prompt, payload):
        if (
            model == "three"
            and json.loads(payload)["entries"][0]["source"] == "Source 100"
        ):
            return "bad"
        return response(model, prompt, payload)

    config["request"] = request
    assert not run_classification(inputs, run, **config)["complete"]
    with sqlite3.connect(run / "decisions.sqlite") as db:
        db.execute(
            'UPDATE decisions SET class=\'C\',votes=\'["C","C","C"]\' WHERE entry_id=1'
        )
    with pytest.raises(ValueError, match="checkpoint changed"):
        run_classification(inputs, run, **config)


def test_run_when_another_owner_holds_lock_then_no_requests(tmp_path):
    inputs, run = write_inputs(tmp_path / "input.jsonl", 1), tmp_path / "run"
    run.mkdir()
    with FileLock(run / ".run.lock", timeout=0), pytest.raises(Timeout):
        run_classification(inputs, run, **options(tmp_path))
    assert not (run / "decisions.sqlite").exists()


def test_run_when_database_from_another_run_then_refuse_rebinding(tmp_path):
    import shutil

    inputs, run = write_inputs(tmp_path / "input.jsonl", 1), tmp_path / "run"
    config = options(tmp_path)
    run_classification(inputs, run, **config)
    other = tmp_path / "other"
    run_classification(inputs, other, **{**config, "prompt": "Another rubric"})
    shutil.copyfile(other / "decisions.sqlite", run / "decisions.sqlite")
    with pytest.raises(ValueError, match="belongs to another run"):
        run_classification(inputs, run, **config)


def test_run_when_schema_initialization_fails_then_retry_creates_complete_schema(
    tmp_path, monkeypatch
):
    from vexy_localizzy.experimental import classification_run_store

    inputs, run = write_inputs(tmp_path / "input.jsonl", 1), tmp_path / "run"
    original = classification_run_store.SCHEMA
    monkeypatch.setattr(classification_run_store, "SCHEMA", (*original, "NOT SQL"))
    with pytest.raises(sqlite3.OperationalError):
        run_classification(inputs, run, **options(tmp_path))
    with sqlite3.connect(run / "decisions.sqlite") as db:
        assert (
            db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            == []
        )
    monkeypatch.setattr(classification_run_store, "SCHEMA", original)
    assert run_classification(inputs, run, **options(tmp_path))["complete"]
