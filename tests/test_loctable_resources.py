# this_file: tests/test_loctable_resources.py
"""Multilingual Apple tables preserve raw locale names and explicit pair selection."""

import plistlib
import xml.etree.ElementTree as ET

import pytest

from vexy_localizzy.apple_resources import loctable_tables
from vexy_localizzy.source_extraction import extract


@pytest.mark.parametrize("fmt", [plistlib.FMT_XML, plistlib.FMT_BINARY])
def test_loctable_when_native_plist_then_preserve_tables_and_skip_metadata(fmt):
    tables = {
        "de_DE": {"key": "Öffnen"},
        "en": {"key": "Open"},
        "LocProvenance": {"key": "metadata"},
        "version": 1,
    }
    assert loctable_tables(plistlib.dumps(tables, fmt=fmt, sort_keys=False)) == [
        ("de_DE", {"key": "Öffnen"}),
        ("en", {"key": "Open"}),
    ], "Raw locale names and insertion order belong to the caller"


def test_loctable_when_root_invalid_then_refuse():
    with pytest.raises(ValueError):
        loctable_tables(plistlib.dumps(["wrong root"]))


@pytest.mark.parametrize("fmt", [plistlib.FMT_XML, plistlib.FMT_BINARY])
def test_extract_when_multilingual_table_then_select_requested_pair(tmp_path, fmt):
    source, output = tmp_path / "Localizable.loctable", tmp_path / "out.tmx"
    data = plistlib.dumps(
        {
            "en": {"key": "Open"},
            "de": {"key": "Öffnen", "extra": "Neu"},
            "fr": {"key": "Ouvrir"},
        },
        fmt=fmt,
    )
    source.write_bytes(data)
    result = extract(str(source), str(output), target_lang="de")
    assert result["units"] == 1 and result["unmatched_keys"] == ["extra"]
    unit = ET.parse(output).find("body/tu")
    assert [s.text for s in unit.findall("tuv/seg")] == ["Open", "Öffnen"]
    assert unit.findtext("prop[@type='x-origin']") == str(source)
    assert unit.findtext("prop[@type='x-source-origin']") == str(source)
    assert source.read_bytes() == data


def test_extract_when_raw_locale_keys_differ_then_explicit_keys_keep_output_tags(
    tmp_path,
):
    source, output = tmp_path / "Localizable.loctable", tmp_path / "out.tmx"
    source.write_bytes(
        plistlib.dumps({"Base": {"key": "Open"}, "German": {"key": "Öffnen"}})
    )
    result = extract(
        str(source),
        str(output),
        source_lang="en-US",
        target_lang="de-DE",
        source_key="Base",
        target_key="German",
    )
    assert result["source_lang"] == "en-US" and result["target_lang"] == "de-DE"
    assert result["units"] == 1


def test_extract_when_loctable_has_plural_then_only_generated_variant_uses_other(
    tmp_path,
):
    source, output = tmp_path / "Localizable.loctable", tmp_path / "out.tmx"
    source.write_bytes(
        plistlib.dumps(
            {
                "en": {
                    "items": {"count": {"other": "Items"}},
                    "literal|count|other": "Do not match",
                },
                "pl": {
                    "items": {"count": {"few": "Elementy"}},
                    "literal|count|few": "No match",
                },
            }
        )
    )
    result = extract(str(source), str(output), target_lang="pl")
    assert result["units"] == 1 and result["unmatched_keys"] == ["literal|count|few"]
    assert [s.text for s in ET.parse(output).findall("body/tu/tuv/seg")] == [
        "Items",
        "Elementy",
    ]


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"target_lang": "fr"}, {"target_lang": "de", "source_key": "missing"}],
)
def test_extract_when_loctable_selection_missing_then_preserve_output(tmp_path, kwargs):
    source, output = tmp_path / "Localizable.loctable", tmp_path / "out.tmx"
    source.write_bytes(plistlib.dumps({"en": {"key": "Open"}, "de": {"key": "Öffnen"}}))
    output.write_bytes(b"existing")
    with pytest.raises(ValueError):
        extract(str(source), str(output), **kwargs)
    assert output.read_bytes() == b"existing"


def test_extract_when_separate_source_for_loctable_then_refuse(tmp_path):
    source, reference = tmp_path / "source.loctable", tmp_path / "reference.loctable"
    data = plistlib.dumps({"en": {}, "de": {}})
    source.write_bytes(data)
    reference.write_bytes(data)
    with pytest.raises(ValueError, match="separate source"):
        extract(
            str(source),
            str(tmp_path / "out.tmx"),
            source=str(reference),
            target_lang="de",
        )


def test_extract_when_table_keys_for_other_format_then_refuse(tmp_path):
    source = tmp_path / "source.properties"
    source.write_text("key=Open\n")
    with pytest.raises(ValueError, match="loctable"):
        extract(
            str(source), str(tmp_path / "out.tmx"), source_key="en", target_lang="de"
        )
