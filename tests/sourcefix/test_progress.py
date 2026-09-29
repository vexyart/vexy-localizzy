# this_file: tests/sourcefix/test_progress.py
"""The CLI explains its intent before work and remains visible during slow stages."""

import threading

import pytest

from vexy_localizzy.cli import sourcefix
from vexy_localizzy.sourcefix.progress import Progress, report


def test_cli_when_starting_then_explains_writes_before_work(monkeypatch, capsys):
    def fake_apply(*args, **kwargs):
        output = capsys.readouterr().err
        assert "APPLY" in output
        assert "finished" in output
        assert "rebuild" in output
        report("Reading example.ts")
        return {"edits": 0, "diff": ""}

    monkeypatch.setattr(sourcefix, "apply_edits", fake_apply)
    sourcefix.apply("edit.ts", "en.ts", ".")
    assert "Reading example.ts" in capsys.readouterr().err


def test_cli_when_interrupted_before_writes_then_clean_exit(monkeypatch, capsys):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(sourcefix, "apply_edits", interrupt)
    with pytest.raises(SystemExit) as exc:
        sourcefix.apply("edit.ts", "en.ts", ".")
    output = capsys.readouterr().err
    assert exc.value.code == 130
    assert "No source or catalog files were changed" in output
    assert "Traceback" not in output


def test_progress_when_stage_is_slow_then_emits_elapsed_heartbeat(capsys):
    received = threading.Event()
    with Progress(interval=0.01) as progress:
        original = progress.write

        def observe(message):
            original(message)
            if "still working" in message:
                received.set()

        progress.write = observe
        report("Rebuilding example.ts")
        assert received.wait(1), "A slow stage must emit a heartbeat"
    assert "Rebuilding example.ts" in capsys.readouterr().err


def test_progress_when_library_called_without_cli_then_silent(capsys):
    report("Library operation")
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    "state,expected",
    [
        ("restored", "restored"),
        ("committed", "already written"),
        ("writing", "Check the working tree"),
    ],
)
def test_cli_when_interrupted_then_reports_actual_write_state(
    state, expected, monkeypatch, capsys
):
    def interrupt(*args, **kwargs):
        report("Write stage", state=state)
        raise KeyboardInterrupt

    monkeypatch.setattr(sourcefix, "apply_edits", interrupt)
    with pytest.raises(SystemExit):
        sourcefix.apply("edit.ts", "en.ts", ".")
    assert expected in capsys.readouterr().err


def test_commit_when_interrupted_mid_batch_then_restores_and_reports(
    tmp_path, monkeypatch, capsys
):
    from vexy_localizzy.sourcefix import files

    first, second = tmp_path / "first", tmp_path / "second"
    for path in (first, second):
        path.write_bytes(b"before")
    replace = files.os.replace
    calls = 0

    def interrupt_second(source, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        replace(source, target)

    monkeypatch.setattr(files.os, "replace", interrupt_second)
    with pytest.raises(SystemExit) as exc:
        with Progress():
            files.commit(
                {first: b"after", second: b"after"},
                {first: b"before", second: b"before"},
            )
    assert exc.value.code == 130
    assert first.read_bytes() == second.read_bytes() == b"before"
    assert "Original files were restored" in capsys.readouterr().err


def test_cli_when_preview_then_announces_no_writes(monkeypatch, capsys):
    monkeypatch.setattr(
        sourcefix, "apply_edits", lambda *args, **kwargs: {"edits": 0, "diff": ""}
    )
    sourcefix.apply("edit.ts", "en.ts", ".", dry_run=True)
    output = capsys.readouterr().err
    assert "PREVIEW" in output
    assert "no files will change" in output


def test_cli_when_preparing_then_reports_intent_and_completion(monkeypatch, capsys):
    monkeypatch.setattr(
        sourcefix, "prepare_edits", lambda *args, **kwargs: {"editable": 1}
    )
    assert sourcefix.prepare("en.ts", "edit.ts", ".") == {"editable": 1}
    output = capsys.readouterr().err
    assert "PREPARE" in output
    assert "Done" in output
