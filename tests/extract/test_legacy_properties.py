# this_file: tests/extract/test_legacy_properties.py
"""Properties consumers keep discovery policy while sharing correct decoding."""

import importlib

import pytest


@pytest.fixture
def adobe(monkeypatch):
    return importlib.import_module("vexy_localizzy.extract.adobe")


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16"])
def test_properties_when_even_slashes_and_unicode_then_preserve_records(
    tmp_path, adobe, encoding
):
    path = tmp_path / "locale" / "de_DE" / "messages.properties"
    path.parent.mkdir(parents=True)
    path.write_bytes(
        ("path=two\\\\\nnext=ok\nemoji=\\uD83D\\uDE00\nkey=one\nkey=two\n").encode(
            encoding
        )
    )
    entries = list(adobe.parse_properties(path, tmp_path))
    assert [(entry.key, entry.text) for entry in entries] == [
        ("path", "two\\"),
        ("next", "ok"),
        ("emoji", "😀"),
        ("key", "one"),
        ("key", "two"),
    ], "Continuation parity and surrogate decoding must not corrupt records"
    assert all(
        entry.lang == "de" and entry.origin == "locale/de_DE/messages.properties"
        for entry in entries
    )
    assert adobe.build_tables(entries)["de"][(entries[0].domain, "key")].text == "one"


@pytest.mark.parametrize("data", [b"good=ok\nbad=\\uNOPE", b"good=ok\nbad=\xff"])
def test_properties_when_invalid_then_no_partial_entries(tmp_path, adobe, data):
    path = tmp_path / "locale" / "de_DE" / "messages.properties"
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    with pytest.raises(ValueError):
        next(adobe.parse_properties(path, tmp_path))


def test_properties_when_consumer_loaded_then_shared_parser(adobe):
    from vexy_localizzy.properties_resources import parse_properties

    assert adobe.properties_pairs is parse_properties


def test_command_when_one_resource_invalid_then_preserve_existing_output(
    tmp_path, adobe
):
    root, output = tmp_path / "input", tmp_path / "output"
    locale = root / "locale/de_DE"
    locale.mkdir(parents=True)
    (locale / "good.properties").write_text("key=Valid\n")
    (locale / "bad.properties").write_text("key=\\uNOPE\n")
    output.mkdir()
    destination = output / "de.tmx"
    destination.write_bytes(b"existing")
    with pytest.raises(SystemExit, match="resource errors"):
        adobe.run(str(root), str(output), ui_lang="en")
    assert destination.read_bytes() == b"existing", (
        "Partial extraction cannot replace a complete catalog"
    )
