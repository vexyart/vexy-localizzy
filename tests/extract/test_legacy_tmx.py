# this_file: tests/extract/test_legacy_tmx.py
"""Legacy command writers share atomic TMX serialization without losing records."""

import importlib
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
def legacy(monkeypatch):
    modules = ("po2tmx", "adobe2tmx", "lproj2tmx", "ts2tmx")
    return {
        name: importlib.import_module(f"vexy_localizzy.extract.{LEGACY_MODULES[name]}")
        for name in modules
    }


def test_legacy_selection_when_imported_then_shared_projection_functions(legacy):
    from vexy_localizzy.extract.legacy_pairs import po_pairs, ts_pairs

    assert legacy["po2tmx"].units is po_pairs, (
        "Gettext selection must use the shared adapter"
    )
    assert legacy["ts2tmx"].units is ts_pairs, (
        "Qt and OSS extraction must use the shared adapter"
    )


def test_po_writer_when_extraction_fails_then_existing_output_survives(
    tmp_path, legacy
):
    output = tmp_path / "out.tmx"
    output.write_bytes(b"existing")

    def rows():
        yield ("Open", "Öffnen", "C", None)
        raise RuntimeError("source read failed")

    with pytest.raises(RuntimeError, match="source read failed"):
        legacy["po2tmx"].write_tmx(output, "en", "de", "source.po", rows())
    assert output.read_bytes() == b"existing"


@pytest.mark.parametrize("name", ["adobe2tmx", "lproj2tmx"])
def test_resource_writer_when_provenance_invalid_then_destination_survives(
    tmp_path, legacy, name
):
    entry = legacy["adobe2tmx"].Entry("domain", "key", "de", "Öffnen", "bad\x04origin")
    output = tmp_path / "out.tmx"
    output.write_bytes(b"existing")
    with pytest.raises(ValueError):
        legacy[name].write_tmx(
            output, "de", {("domain", "key"): entry}, {}, False, False
        )
    assert output.read_bytes() == b"existing"


def test_po_writer_when_special_characters_then_context_and_origin_survive(
    tmp_path, legacy
):
    output = tmp_path / "out.tmx"
    count = legacy["po2tmx"].write_tmx(
        output,
        "en",
        "pl",
        "origin<&.po",
        [
            ("A & <b>", "Ą & <b>", 'C"', None),
            ("A & <b>", "Ą & <b>", 'C"', None),
        ],
    )
    root = ET.parse(output).getroot()
    assert count == 1
    unit = root.find("body/tu")
    assert unit.findtext("prop[@type='x-origin']") == "origin<&.po"
    assert unit.findtext("prop[@type='x-context']") == 'C"'
    assert [segment.text for segment in unit.findall("tuv/seg")] == [
        "A & <b>",
        "Ą & <b>",
    ]


@pytest.mark.parametrize(
    "name,parser",
    [("adobe2tmx", "parse_apple_strings"), ("lproj2tmx", "parse_lproj_file")],
)
def test_apple_reader_when_comment_markers_in_value_then_preserve_text_and_origin(
    tmp_path, legacy, name, parser
):
    path = tmp_path / "de.lproj" / "Localizable.strings"
    path.parent.mkdir()
    path.write_text('"key"="literal /* keep */ and // keep"; "key"="second";')
    entries = list(getattr(legacy[name], parser)(path, tmp_path))
    if name == "lproj2tmx":
        entries = [entry for _, entry in entries]
    assert [entry.text for entry in entries] == [
        "literal /* keep */ and // keep",
        "second",
    ]
    assert all(entry.origin == "de.lproj/Localizable.strings" for entry in entries)
    tables = legacy[name].build_tables(
        [(False, entry) for entry in entries] if name == "lproj2tmx" else entries
    )
    assert next(iter(tables["de"].values())).text == "literal /* keep */ and // keep"
