# this_file: tests/test_source_extraction.py
"""Shared extraction commands preserve selected pairs and source files."""

import sys
import xml.etree.ElementTree as ET

import pytest

from vexy_localizzy.cli import main
from vexy_localizzy.source_extraction import extract


def segments(path):
    return [
        [s.text for s in u.findall("tuv/seg")]
        for u in ET.parse(path).findall("body/tu")
    ]


def test_extract_when_ts_then_select_finished_pairs_and_metadata(tmp_path):
    source = tmp_path / "catalog.ts"
    raw = b'<TS language="de_DE" sourcelanguage="en_US"><context><name>Menu</name><message><source>Open</source><translation>Offen</translation></message><message><source>Skip</source><translation type="unfinished">Nein</translation></message></context></TS>'
    source.write_bytes(raw)
    out = tmp_path / "out.tmx"
    report = extract(str(source), str(out))
    assert segments(out) == [["Open", "Offen"]]
    unit = ET.parse(out).find("body/tu")
    assert unit.findtext('prop[@type="x-context"]') == "Menu"
    assert unit.findtext('prop[@type="x-origin"]') == str(source)
    assert report["units"] == 1
    assert report["source_lang"] == "en-US"
    assert report["target_lang"] == "de-DE"
    assert source.read_bytes() == raw


def test_extract_when_po_then_fuzzy_policy_and_deduplication(tmp_path):
    source = tmp_path / "catalog.po"
    source.write_text(
        'msgid ""\nmsgstr "Language: pl\\n"\n\nmsgid "Open"\nmsgstr "Otwórz"\n\n#, fuzzy\nmsgid "Maybe"\nmsgstr "Może"\n'
    )
    out = tmp_path / "out.tmx"
    assert extract(str(source), str(out))["units"] == 1
    assert extract(str(source), str(out), fuzzy=True)["units"] == 2


@pytest.mark.parametrize(
    "suffix,reference,target,expected",
    [
        (
            ".strings",
            '"key"="Open";',
            '"key"="/* Öffnen */"; "absent"="missing";',
            [["Open", "/* Öffnen */"]],
        ),
        (
            ".ftl",
            "key = Open\n",
            "key = Öffnen\nabsent = Missing\n",
            [["Open", "Öffnen"]],
        ),
    ],
)
def test_extract_when_keyed_resources_then_join_by_key_and_report_unmatched(
    tmp_path, suffix, reference, target, expected
):
    source = tmp_path / ("source" + suffix)
    localized = tmp_path / ("target" + suffix)
    source.write_text(reference)
    localized.write_text(target)
    out = tmp_path / "out.tmx"
    result = extract(str(localized), str(out), source=str(source), target_lang="de")
    assert segments(out) == expected
    assert result["unmatched_keys"] == ["absent"]
    unit = ET.parse(out).find("body/tu")
    assert unit.findtext('prop[@type="x-source-origin"]') == str(source)
    assert unit.findtext('prop[@type="x-context"]') == "key"


def test_extract_when_target_has_extra_selector_then_join_source_default(tmp_path):
    source, target, out = (
        tmp_path / "source.ftl",
        tmp_path / "target.ftl",
        tmp_path / "out.tmx",
    )
    source.write_text("n = { $n ->\n [one] One\n *[other] Many\n}\n")
    target.write_text("n = { $n ->\n [few] Kilka\n *[other] Wiele\n}\n")
    report = extract(str(target), str(out), source=str(source), target_lang="pl")
    assert report["unmatched_keys"] == []
    assert segments(out) == [["Many", "Kilka"], ["Many", "Wiele"]]


def test_main_when_extract_requested_then_dispatch_shared_command(
    tmp_path, monkeypatch, capsys
):
    source, out = tmp_path / "a.po", tmp_path / "a.tmx"
    source.write_text('msgid "Open"\nmsgstr "Offen"\n')
    monkeypatch.setattr(
        sys,
        "argv",
        ["localizzy", "tm", "extract", str(source), str(out), "--target_lang=de"],
    )
    main()
    assert segments(out) == [["Open", "Offen"]]
    assert "units:" in capsys.readouterr().out


def test_extract_when_plain_apple_key_missing_then_do_not_guess_plural_key(tmp_path):
    source, target, out = (
        tmp_path / "source.strings",
        tmp_path / "target.strings",
        tmp_path / "out.tmx",
    )
    source.write_text('"plain|other"="Unrelated";')
    target.write_text('"plain"="Target";')
    result = extract(str(target), str(out), source=str(source), target_lang="de")
    assert result["units"] == 0
    assert result["unmatched_keys"] == ["plain"]


def test_extract_when_forbidden_xml_text_then_existing_output_survives(tmp_path):
    source, out = tmp_path / "a.po", tmp_path / "out.tmx"
    source.write_text('msgid "Open"\nmsgstr "Bad\x04text"\n')
    out.write_bytes(b"existing")
    with pytest.raises(ValueError):
        extract(str(source), str(out), target_lang="de")
    assert out.read_bytes() == b"existing"
    assert not list(tmp_path.glob(".out.tmx.*"))


def test_extract_when_duplicate_rows_then_dedupe_is_explicit(tmp_path):
    source, out = tmp_path / "a.po", tmp_path / "out.tmx"
    source.write_text('msgid "Open"\nmsgstr "Offen"\n\nmsgid "Open"\nmsgstr "Offen"\n')
    assert extract(str(source), str(out), target_lang="de")["units"] == 1
    assert extract(str(source), str(out), target_lang="de", dedupe=False)["units"] == 2


def test_extract_when_stringsdict_has_extra_plural_then_use_other_and_retain_format(
    tmp_path,
):
    import plistlib

    source, target, out = (
        tmp_path / "source.stringsdict",
        tmp_path / "target.stringsdict",
        tmp_path / "out.tmx",
    )

    def resource(form):
        return {"n": {"NSStringLocalizedFormatKey": "%#@count@", "count": form}}

    source.write_bytes(plistlib.dumps(resource({"other": "Many"})))
    target.write_bytes(plistlib.dumps(resource({"few": "Kilka", "other": "Wiele"})))
    assert (
        extract(str(target), str(out), source=str(source), target_lang="pl")["units"]
        == 3
    )
    assert segments(out) == [
        ["%#@count@", "%#@count@"],
        ["Many", "Kilka"],
        ["Many", "Wiele"],
    ]


@pytest.mark.parametrize("extra", [{"fuzzy": True}, {"source": "reference"}])
def test_extract_when_options_do_not_apply_then_reject(tmp_path, extra):
    source, out = tmp_path / "a.ts", tmp_path / "out.tmx"
    source.write_text('<TS language="de"/>')
    if "source" in extra:
        extra = {"source": str(source)}
    with pytest.raises(ValueError):
        extract(str(source), str(out), **extra)
    assert not out.exists()
