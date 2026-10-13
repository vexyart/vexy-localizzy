# this_file: tests/extract/test_legacy_loctable.py
"""Apple bundle discovery keeps its locale policy and refuses partial publication."""

import importlib
import plistlib

import pytest


@pytest.fixture
def lproj(monkeypatch):
    return importlib.import_module("vexy_localizzy.extract.lproj")


def test_loctable_when_consumer_loaded_then_shared_table_reader(lproj):
    from vexy_localizzy.extract.apple_resources import loctable_tables

    assert lproj.loctable_tables is loctable_tables, (
        "Share table reading with the public command"
    )


@pytest.mark.parametrize("fmt", [plistlib.FMT_BINARY, plistlib.FMT_XML])
def test_loctable_when_raw_aliases_then_keep_pivot_policy_and_provenance(
    tmp_path, lproj, fmt
):
    path = tmp_path / "Contents/Resources/Localizable.loctable"
    path.parent.mkdir(parents=True)
    data = plistlib.dumps(
        {
            "Base": {"key": "Fallback", "extra": "Extra"},
            "en": {"key": "Open"},
            "German": {"key": "Öffnen"},
            "LocProvenance": {"key": "Ignore"},
            "version": 1,
        },
        fmt=fmt,
        sort_keys=False,
    )
    path.write_bytes(data)
    entries = list(lproj.parse_loctable(path, tmp_path))
    assert [(fallback, entry.lang, entry.text) for fallback, entry in entries] == [
        (True, "en", "Fallback"),
        (True, "en", "Extra"),
        (False, "en", "Open"),
        (False, "de", "Öffnen"),
    ]
    assert all(
        entry.domain == "Localizable"
        and entry.origin == "Contents/Resources/Localizable.loctable"
        for _, entry in entries
    )
    tables = lproj.build_tables(entries)
    assert tables["en"][("Localizable", "key")].text == "Open", (
        "Real English wins over Base"
    )
    assert tables["en"][("Localizable", "extra")].text == "Extra", (
        "Base fills missing English keys"
    )
    assert path.read_bytes() == data, "Extraction must preserve the native resource"


@pytest.mark.parametrize("suffix", [".loctable", ".strings"])
def test_command_when_resource_invalid_then_all_existing_outputs_survive(
    tmp_path, lproj, suffix
):
    root, output = tmp_path / "Example.app", tmp_path / "output"
    locale = root / "Contents/Resources/de.lproj"
    locale.mkdir(parents=True)
    (locale / "good.strings").write_text('"Open" = "Öffnen";')
    (locale / ("bad" + suffix)).write_bytes(b"malformed resource")
    output.mkdir()
    original = {"de.tmx": b"existing German", "en.tmx": b"existing English"}
    for name, data in original.items():
        (output / name).write_bytes(data)
    with pytest.raises(SystemExit, match="resource errors"):
        lproj.run(str(root), str(output))
    assert {p.name: p.read_bytes() for p in output.iterdir()} == original, (
        "Partial extraction must not publish"
    )


def test_cli_when_input_directory_then_nested_resources_and_loctable(tmp_path):
    from lxml import etree

    from vexy_localizzy.cli.tm import lproj2tmx

    root = tmp_path / "glossary"
    for locale, text in [("en", "Open"), ("pl", "Otwórz")]:
        folder = root / f"{locale}.lproj" / "nested"
        folder.mkdir(parents=True)
        (folder / "Localizable.strings").write_bytes(
            f'"open_key" = "{text}";'.encode("utf-16")
        )
    (root / "Other.loctable").write_bytes(
        plistlib.dumps(
            {"en": {"close_key": "Close"}, "pl": {"close_key": "Zamknij"}},
            fmt=plistlib.FMT_BINARY,
        )
    )
    result = lproj2tmx(input=str(root), output=str(tmp_path / "tmx"))
    assert len(result["languages"]) == 2, "Both locales must be exported"
    tree = etree.parse(str(tmp_path / "tmx/pl.tmx"))
    assert tree.xpath("//seg/text()") == ["Close", "Zamknij", "Open", "Otwórz"], (
        "Nested strings and loctable must both pair against English"
    )


def test_cli_when_input_and_app_conflict_then_reject(tmp_path):
    from vexy_localizzy.cli.tm import lproj2tmx

    with pytest.raises(ValueError, match="either"):
        lproj2tmx(app="a", input="b", output=str(tmp_path))
