# this_file: tests/extract/test_legacy_json.py
"""Locale JSON delegates strict parsing while retaining private selection policy."""

import importlib

import pytest


@pytest.fixture
def adobe(monkeypatch):
    return importlib.import_module("vexy_localizzy.extract.adobe")


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16"])
def test_locale_json_when_valid_then_preserve_filters_and_provenance(
    tmp_path, adobe, encoding
):
    path = tmp_path / "locale/de_DE/strings.json"
    path.parent.mkdir(parents=True)
    data = '{"nested":{"label":"  Öffnen  ","id":"Ignore"},"items":["First",42,"https://example.test/help"],"number":"123","empty":" ","emoji":"😀","count_one":"One","count_other":"Other"}'.encode(
        encoding
    )
    path.write_bytes(data)
    entries = list(adobe.parse_locale_json(path, tmp_path))
    assert [(entry.key, entry.text) for entry in entries] == [
        ("nested.label", "  Öffnen  "),
        ("items.0", "First"),
        ("count_one", "One"),
        ("count_other", "Other"),
    ], "Keep existing UI-text filtering and literal plural suffixes"
    assert all(
        entry.lang == "de" and entry.origin == "locale/de_DE/strings.json"
        for entry in entries
    )
    assert path.read_bytes() == data


@pytest.mark.parametrize(
    "data",
    [
        b'{"valid":"value","bad":}',
        b'{"bad":"\xff"}',
        b'{"key":"first","key":"second"}',
        b'{"key":"\\ud800"}',
        b'{"a.b":"literal","a":{"b":"nested"}}',
    ],
)
def test_locale_json_when_invalid_or_ambiguous_then_refuse(tmp_path, adobe, data):
    path = tmp_path / "locale/de_DE/strings.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    with pytest.raises(ValueError):
        list(adobe.parse_locale_json(path, tmp_path))


def test_locale_json_when_consumer_loaded_then_shared_reader(adobe):
    from vexy_localizzy.extract.json_resources import string_pairs

    assert adobe.json_pairs is string_pairs


def test_locale_json_when_keys_end_in_dots_then_keep_distinct_entries(tmp_path, adobe):
    path = tmp_path / "locale/de_DE/strings.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"open":"Open","open...":"Open dialog","parent":{"":"Empty key"}}')
    entries = list(adobe.parse_locale_json(path, tmp_path))
    assert [(entry.key, entry.text) for entry in entries] == [
        ("open", "Open"),
        ("open...", "Open dialog"),
        ("parent.", "Empty key"),
    ], "Literal trailing dots and empty key components cannot be discarded"


def test_command_when_locale_json_invalid_then_preserve_every_output(tmp_path, adobe):
    root, output = tmp_path / "input", tmp_path / "output"
    locale = root / "locale/de_DE"
    locale.mkdir(parents=True)
    (locale / "good.json").write_text('{"key":"Valid"}')
    (locale / "bad.json").write_text('{"key":}')
    output.mkdir()
    previous = {"de.tmx": b"existing German", "en.tmx": b"existing English"}
    for name, data in previous.items():
        (output / name).write_bytes(data)
    with pytest.raises(SystemExit, match="resource errors"):
        adobe.run(str(root), str(output), ui_lang="en")
    assert {path.name: path.read_bytes() for path in output.iterdir()} == previous
