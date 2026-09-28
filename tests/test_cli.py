# this_file: tests/test_cli.py
"""Exercise command dispatch and documented workflows."""

import json
import runpy
import sys
from pathlib import Path

import pytest

from vexy_localizzy.cli import inventory, main


def test_inventory_command_when_missing_directory_then_fails(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        inventory(str(tmp_path / "missing"), str(tmp_path / "out.jsonl"))


def test_main_when_inventory_requested_then_creates_manifest(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path / "input"
    root.mkdir()
    (root / "sample.tmx").write_text("<tmx><body/></tmx>")
    output = tmp_path / "manifest.jsonl"
    monkeypatch.setattr(sys, "argv", ["localizzy", "inventory", str(root), str(output)])
    main()
    assert json.loads(output.read_text())["counts_complete"]
    assert "files:" in capsys.readouterr().out


def test_quickstart_when_run_then_demonstrates_traceable_winner(capsys):
    runpy.run_path(
        str(Path(__file__).parents[1] / "examples/quickstart.py"), run_name="__main__"
    )
    assert "winner=Księżyc score=5 sources=2" in capsys.readouterr().out


def test_main_when_convert_po_json_po_then_exact_bytes(tmp_path, monkeypatch, capsys):
    source = tmp_path / "in.po"
    source.write_bytes(b'msgid "Open"\nmsgstr "Ouvrir"\n')
    saved = tmp_path / "saved.json"
    output = tmp_path / "out.po"
    for input_path, target, out_path in [
        (source, "json", saved),
        (saved, "po", output),
    ]:
        monkeypatch.setattr(
            sys,
            "argv",
            ["localizzy", "convert", str(input_path), target, str(out_path)],
        )
        main()
    assert output.read_bytes() == source.read_bytes()
    assert "findings" in capsys.readouterr().out
