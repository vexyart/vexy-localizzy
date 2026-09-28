# this_file: tests/extract/test_legacy_resource_failures.py
"""Legacy scanners must expose malformed resources before catalog publication."""

import importlib
import struct
import xml.etree.ElementTree as ET

import pytest

LEGACY_MODULES = {
    "po2tmx": "po2tmx",
    "adobe2tmx": "adobe",
    "lproj2tmx": "lproj",
    "ts2tmx": "ts2tmx",
    "oss2tmx": "oss",
}


@pytest.fixture
def commands(monkeypatch):
    modules = ("adobe2tmx", "oss2tmx")
    return {
        name: importlib.import_module(f"vexy_localizzy.extract.{LEGACY_MODULES[name]}")
        for name in modules
    }


PMST = struct.pack("<III", 3, 8, 2) + b"\x01\x00a\x01\x00A\x01\x00b\x01\x00B"


@pytest.mark.parametrize("length", [0, 11, 12, 13, 15, 17, 18, 19, 21, 23])
def test_pmst_when_truncated_then_refuse(tmp_path, commands, length):
    path = tmp_path / "Resources/idrc_PMST/300.idrc"
    path.parent.mkdir(parents=True)
    path.write_bytes(PMST[:length])
    with pytest.raises(ValueError, match="Truncated PMST"):
        list(commands["adobe2tmx"].parse_pmst(path, tmp_path))


def test_pmst_when_declared_utf8_invalid_then_refuse(tmp_path, commands):
    path = tmp_path / "Resources/idrc_PMST/300.idrc"
    path.parent.mkdir(parents=True)
    path.write_bytes(PMST[:-1] + b"\xff")
    with pytest.raises(UnicodeDecodeError):
        list(commands["adobe2tmx"].parse_pmst(path, tmp_path))


def test_pmst_when_valid_then_keep_header_policy_and_order(tmp_path, commands):
    path = tmp_path / "Resources/idrc_PMST/301.idrc"
    path.parent.mkdir(parents=True)
    path.write_bytes(PMST)
    entries = list(commands["adobe2tmx"].parse_pmst(path, tmp_path))
    assert [(entry.key, entry.text) for entry in entries] == [("a", "A"), ("b", "B")]
    assert all(
        entry.lang == "de"
        and entry.domain == "idrc:Resources:300"
        and entry.origin == "Resources/idrc_PMST/301.idrc"
        for entry in entries
    )


@pytest.mark.parametrize("kind", ["strings", "pmst"])
def test_adobe_when_one_resource_invalid_then_preserve_all_outputs(
    tmp_path, commands, kind
):
    root, output = tmp_path / "input", tmp_path / "output"
    good = root / "de.lproj/good.strings"
    good.parent.mkdir(parents=True)
    good.write_text('"key"="Good";')
    bad = root / (
        "de.lproj/bad.strings" if kind == "strings" else "Resources/idrc_PMST/300.idrc"
    )
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_bytes(b"malformed" if kind == "strings" else PMST[:-1])
    output.mkdir()
    destination = output / "de.tmx"
    destination.write_bytes(b"existing")
    with pytest.raises(SystemExit, match="resource errors"):
        commands["adobe2tmx"].run(str(root), str(output), ui_lang="en")
    assert {p.name: p.read_bytes() for p in output.iterdir()} == {"de.tmx": b"existing"}


@pytest.mark.parametrize(
    "kind,data",
    [
        ("ts", '<TS language="de"><context>'),
        ("ts", '<wrong language="de"/>'),
        ("po", 'msgid "Good"\nmsgstr "Gut"\nBOGUS'),
    ],
)
def test_oss_when_catalog_invalid_then_preserve_app_outputs(
    tmp_path, commands, monkeypatch, kind, data
):
    oss = commands["oss2tmx"]
    source, output = tmp_path / "source", tmp_path / "output"
    source.mkdir()
    (source / f"broken_de.{kind}").write_text(data)
    valid = (
        '<TS language="de"><context><name>Test</name><message><source>Good</source><translation>Gut</translation></message></context></TS>'
        if kind == "ts"
        else 'msgid "Good"\nmsgstr "Gut"\n'
    )
    (source / f"good_de.{kind}").write_text(valid)
    app = oss.App(
        name="Synthetic",
        repo=oss.Repo(url="https://example.test/repo.git"),
        glob=f"*_{'{lang}'}.{kind}",
        kind=kind,
    )
    monkeypatch.setitem(oss.APPS, "synthetic", app)
    monkeypatch.setattr(oss, "fetch", lambda *_: source)
    destination = output / "synthetic/de.tmx"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"existing")
    with pytest.raises((ValueError, OSError, ET.ParseError)):
        oss.run(output=str(output), apps="synthetic", cache=str(tmp_path / "cache"))
    assert destination.read_bytes() == b"existing"
