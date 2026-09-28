# this_file: tests/test_inventory.py
"""Inventory acceptance tests use only original synthetic text."""

import hashlib
from pathlib import Path

import pytest

from vexy_localizzy.inventory import inspect_file, write_inventory


def test_inspect_file_when_multilingual_then_counts_actual_language_tags(tmp_path):
    path = tmp_path / "memory.tmx"
    path.write_text("""<?xml version="1.0"?><!DOCTYPE tmx SYSTEM "missing.dtd">
    <tmx version="1.4"><header srclang="en"/><body>
    <tu><tuv xml:lang="pl"><seg>Księżyc</seg></tuv>
    <tuv xml:lang="en"><seg>Moon</seg></tuv></tu>
    <tu><tuv xml:lang="en"><seg>Sun</seg></tuv>
    <tuv xml:lang="zh-Hant"><seg>太陽</seg></tuv></tu>
    </body></tmx>""")
    report = inspect_file(path)
    assert report["status"] == "valid", (
        "Normal external DTD references must not require network access"
    )
    assert report["units"] == 2
    assert report["languages"] == {"en": 2, "pl": 1, "zh-Hant": 1}
    assert report["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_inspect_file_when_namespaced_then_counts_units(tmp_path):
    path = tmp_path / "namespaced.tmx"
    path.write_text(
        '<tmx xmlns="urn:tmx"><body><tu><tuv lang="en"><seg>x</seg></tuv></tu></body></tmx>'
    )
    assert inspect_file(path)["units"] == 1


@pytest.mark.parametrize(
    "content", ["", "<tmx><body><tu>", "<other/>", "<tmx><body>\x04</body></tmx>"]
)
def test_inspect_file_when_invalid_then_reports_failure(tmp_path, content):
    path = tmp_path / "invalid.tmx"
    path.write_text(content)
    report = inspect_file(path)
    assert report["status"] == "invalid"
    assert report["error"]


def test_inspect_file_when_entity_then_rejects_without_reading_target(tmp_path):
    secret = tmp_path / "not-input.txt"
    secret.write_text("NOT_FOR_IMPORT")
    path = tmp_path / "entity.tmx"
    path.write_text(
        f'<!DOCTYPE tmx [<!ENTITY x SYSTEM "{secret.as_uri()}">]><tmx><body><tu><tuv lang="en"><seg>&x;</seg></tuv></tu></body></tmx>'
    )
    report = inspect_file(path)
    assert report["status"] == "invalid"
    assert "NOT_FOR_IMPORT" not in str(report)


def test_inspect_file_when_ts_then_reports_state_and_variant_counts(tmp_path):
    path = tmp_path / "sample.ts"
    path.write_text(
        '<TS language="pl" sourcelanguage="en"><context><name>Panel</name><message numerus="yes"><source>%n moons</source><translation type="unfinished"><numerusform>%n księżyc</numerusform></translation></message><message><source>Old</source><translation type="vanished">Dawny</translation></message></context></TS>'
    )
    report = inspect_file(path)
    assert report["units"] == 2
    assert report["states"] == {"unfinished": 1, "vanished": 1}
    assert report["plurals"] == 1


def test_write_inventory_when_one_bad_file_then_retains_both_results(tmp_path):
    import json

    good, bad = tmp_path / "a.tmx", tmp_path / "b.tmx"
    good.write_text("<tmx><body/></tmx>")
    bad.write_text("broken")
    output = tmp_path / "manifest.jsonl"
    summary = write_inventory([good, bad], output, root=tmp_path)
    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert [record["path"] for record in records] == ["a.tmx", "b.tmx"]
    assert summary["files"] == 2 and summary["invalid"] == 1
    assert all(not Path(record["path"]).is_absolute() for record in records)


def test_inspect_file_when_missing_then_reports_io_failure(tmp_path):
    report = inspect_file(tmp_path / "missing.tmx")
    assert report["status"] == "invalid" and report["error"]


def test_inventory_when_symlink_alias_then_preserves_discovered_path(tmp_path):
    import json

    original = tmp_path / "a.tmx"
    original.write_text("<tmx><body/></tmx>")
    alias = tmp_path / "alias.tmx"
    alias.symlink_to(original)
    output = tmp_path / "manifest.jsonl"
    write_inventory([original, alias], output, root=tmp_path)
    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert [row["path"] for row in records] == ["a.tmx", "alias.tmx"]
    assert records[0]["sha256"] == records[1]["sha256"]


def test_inventory_when_external_symlink_then_records_explicit_failure(tmp_path):
    import json

    root = tmp_path / "inputs"
    root.mkdir()
    external = tmp_path / "external.tmx"
    external.write_text("<tmx><body/></tmx>")
    link = root / "link.tmx"
    link.symlink_to(external)
    output = tmp_path / "inventory.jsonl"
    summary = write_inventory([link], output, root=root)
    assert summary["invalid"] == 1
    assert json.loads(output.read_text())["path"] == "link.tmx"


def test_inspect_file_when_extension_uses_tu_name_then_counts_only_real_units(tmp_path):
    path = tmp_path / "extension.tmx"
    path.write_text(
        '<tmx xmlns:ext="urn:ext"><body><tu><tuv lang="en"><seg>Text<ext:tu><ext:tuv lang="fake"/></ext:tu></seg></tuv></tu></body></tmx>'
    )
    report = inspect_file(path)
    assert report["units"] == 1 and report["languages"] == {"en": 1}


def test_inventory_when_malformed_tail_then_partial_count_is_explicit(tmp_path):
    import json

    path = tmp_path / "bad.tmx"
    path.write_text(
        '<tmx><body><tu><tuv lang="en"><seg>Text</seg></tuv></tu>' + " " * 100000
    )
    output = tmp_path / "inventory.jsonl"
    summary = write_inventory([path], output, root=tmp_path)
    record = json.loads(output.read_text())
    assert record["units"] == 1 and record["languages"] == {"en": 1}
    assert not record["counts_complete"]
    assert summary["units"] == 0 and summary["partial_units"] == 1
