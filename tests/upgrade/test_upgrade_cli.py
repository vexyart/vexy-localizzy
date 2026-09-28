# this_file: tests/upgrade/test_upgrade_cli.py
"""The Fire-ready upgrade command: parsing, refusals, exit codes, file output."""

import json
import shutil

import fire
import pytest
from upgrade_helpers import APPROVED, FIXTURES, FRESH

from vexy_localizzy.cli_upgrade import csv_list, upgrade
from vexy_localizzy.formats.ts_read import load_bytes


def fire_run(args):
    return fire.Fire({"upgrade": upgrade}, command=["upgrade", *args])


def test_csv_list_when_string_or_tuple_then_same_list():
    assert csv_list("id,context") == ["id", "context"]
    assert csv_list(("id", "context")) == ["id", "context"]
    assert csv_list(None) == []


def test_cli_when_identity_run_then_exit_zero_and_files_written(tmp_path):
    out, retired = tmp_path / "new.ts", tmp_path / "retired.ts"
    summary = fire_run(
        [
            str(APPROVED),
            str(APPROVED),
            "--out",
            str(out),
            "--retired",
            str(retired),
            "--no-engine",
        ]
    )
    assert out.read_bytes() == APPROVED.read_bytes()
    assert load_bytes(retired.read_bytes()).units[0].source == "Legacy option"
    report = json.loads((tmp_path / "new.ts.upgrade.json").read_text())
    assert report["schema_id"] == "localizzy-upgrade/1"
    assert report["out"]["path"] == str(out)
    assert summary["counts"]["exact"] > 0


def test_cli_when_untranslated_remain_then_exit_one(tmp_path, capsys):
    with pytest.raises(SystemExit) as stop:
        fire_run(
            [
                str(FRESH),
                str(APPROVED),
                "--out",
                str(tmp_path / "new.ts"),
                "--retired",
                str(tmp_path / "ret.ts"),
                "--report",
                str(tmp_path / "r.json"),
                "--direct-memory",
                str(FIXTURES / "ui-de.tmx"),
                "--glossary-memory",
                str(FIXTURES / "core-de.tmx"),
                "--finish-on",
                "id,context,term",
                "--no_engine",
            ]
        )
    assert stop.value.code == 1
    assert json.loads(capsys.readouterr().out)["counts"]["memory_context"] == 1
    assert (tmp_path / "new.ts").exists() and (tmp_path / "r.json").exists()


def test_cli_when_out_is_an_input_then_exit_two_and_input_untouched(tmp_path):
    fresh = tmp_path / "fresh.ts"
    shutil.copy(FRESH, fresh)
    before = fresh.read_bytes()
    with pytest.raises(SystemExit) as stop:
        upgrade(fresh, APPROVED, out=fresh, retired=tmp_path / "r.ts", no_engine=True)
    assert stop.value.code == 2
    assert fresh.read_bytes() == before


def test_cli_when_no_engine_and_no_endpoint_then_exit_two(tmp_path):
    with pytest.raises(SystemExit) as stop:
        upgrade(FRESH, APPROVED, out=tmp_path / "n.ts", retired=tmp_path / "r.ts")
    assert stop.value.code == 2


def test_cli_when_unknown_finish_class_then_exit_two(tmp_path):
    with pytest.raises(SystemExit) as stop:
        upgrade(
            FRESH,
            APPROVED,
            out=tmp_path / "n.ts",
            retired=tmp_path / "r.ts",
            no_engine=True,
            finish_on="id,everything",
        )
    assert stop.value.code == 2


def fake_translate_batch(batch, model, *, base_url, api_key, temperature, **_):
    from vexy_localizzy.translate.types import TranslationResult

    assert base_url == "http://synthetic" and api_key == "secret"
    return TranslationResult(
        targets={i.id: "DE " + i.source for i in batch.items},
        requested_model=model,
        reported_model=model,
    )


def test_cli_when_endpoint_given_then_engine_fills_offline(tmp_path, monkeypatch):
    import vexy_localizzy.translate.abersetz_transport as transport

    monkeypatch.setenv("SYNTHETIC_KEY", "secret")
    monkeypatch.setattr(transport, "translate_batch", fake_translate_batch)
    summary = upgrade(
        FRESH,
        APPROVED,
        out=tmp_path / "n.ts",
        retired=tmp_path / "r.ts",
        endpoint="http://synthetic",
        model="m",
        fallback_models="m2",
        api_key_env="SYNTHETIC_KEY",
        cache=tmp_path / "cache" / "c.sqlite",
    )
    assert summary["counts"]["machine"] >= 1
    assert "untranslated" not in summary["counts"]
    assert (tmp_path / "cache" / "c.sqlite").exists()


def test_cli_when_api_key_missing_then_exit_two(tmp_path, monkeypatch):
    monkeypatch.delenv("SYNTHETIC_KEY", raising=False)
    with pytest.raises(SystemExit) as stop:
        upgrade(
            FRESH,
            APPROVED,
            out=tmp_path / "n.ts",
            retired=tmp_path / "r.ts",
            endpoint="http://synthetic",
            model="m",
            api_key_env="SYNTHETIC_KEY",
        )
    assert stop.value.code == 2
