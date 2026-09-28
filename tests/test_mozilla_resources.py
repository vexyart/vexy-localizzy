# this_file: tests/test_mozilla_resources.py
"""Mozilla resource extraction keeps literal references and rejects partial input."""

import xml.etree.ElementTree as ET

import pytest

from vexy_localizzy.mozilla_resources import parse_mozilla
from vexy_localizzy.source_extraction import extract


@pytest.mark.parametrize(
    "kind,text,expected",
    [
        ("dtd", "", []),
        ("properties", "", []),
        (
            "dtd",
            '<!-- <!ENTITY hidden "No"> -->\n<!ENTITY visible "Yes">',
            [("visible", "Yes")],
        ),
        (
            "dtd",
            '<!ENTITY key "A &amp; B &brand; &#x1F600;">',
            [("key", "A &amp; B &brand; &#x1F600;")],
        ),
        (
            "dtd",
            '<!ENTITY key "First"><!ENTITY key "Last">',
            [("key", "First"), ("key", "Last")],
        ),
        (
            "dtd",
            '<!ENTITY % brand SYSTEM "https://example.invalid/brand.dtd">\n%brand;\n<!ENTITY key "&brand;">',
            [("key", "&brand;")],
        ),
        (
            "properties",
            "key=one\\nline\nkey=second  \n",
            [("key", "one\nline"), ("key", "second  ")],
        ),
        ("properties", "key=long\\\r\n  line\n", [("key", "longline")]),
        ("properties", "key=two\\\\\nnext=ok", [("key", "two\\"), ("next", "ok")]),
        ("properties", r"key\:part=\uD83D\uDE00", [("key:part", "😀")]),
        ("properties", "empty=\n", [("empty", "")]),
        ("properties", r"key=\uNOPE", [("key", "uNOPE")]),
    ],
)
def test_mozilla_when_valid_then_preserve_order_and_values(kind, text, expected):
    assert parse_mozilla(text, kind) == expected


@pytest.mark.parametrize(
    "text",
    [
        '<!ENTITY bad "missing>',
        '<!ENTITY good "Yes">\njunk',
        '<!ENTITY key "literal <!-- comment -->">',
    ],
)
def test_dtd_when_invalid_then_no_partial_resource(text):
    with pytest.raises(ValueError):
        parse_mozilla(text, "dtd")


def test_properties_when_isolated_surrogate_then_reject_non_unicode_text():
    with pytest.raises(ValueError):
        parse_mozilla(r"key=\uD800", "properties")


def test_mozilla_when_format_unknown_then_refuse():
    with pytest.raises(ValueError, match="Mozilla format"):
        parse_mozilla("key=value", "json")


@pytest.mark.parametrize("kind", ["dtd", "mozilla-properties"])
def test_extract_when_mozilla_resources_paired_then_preserve_key_and_origin(
    tmp_path, kind
):
    source, target, output = (
        tmp_path / name for name in ("source", "target", "output.tmx")
    )
    source.write_text('<!ENTITY key "Open">' if kind == "dtd" else "key=Open\n")
    target.write_text(
        '<!ENTITY key "Öffnen"><!ENTITY extra "Neu">'
        if kind == "dtd"
        else "key=Öffnen\nextra=Neu\n"
    )
    result = extract(
        str(target),
        str(output),
        source=str(source),
        source_format=kind,
        target_lang="de",
    )
    assert result["units"] == 1 and result["unmatched_keys"] == ["extra"]
    unit = ET.parse(output).find("body/tu")
    assert [s.text for s in unit.findall("tuv/seg")] == ["Open", "Öffnen"]
    assert unit.findtext("prop[@type='x-context']") == "key"
    assert unit.findtext("prop[@type='x-source-origin']") == str(source)


def test_extract_when_dtd_invalid_then_preserve_output(tmp_path):
    source, target, output = (
        tmp_path / name for name in ("source.dtd", "target.dtd", "output.tmx")
    )
    source.write_text('<!ENTITY key "Open">')
    target.write_text('<!ENTITY key "Öffnen">\ninvalid')
    output.write_bytes(b"existing")
    with pytest.raises(ValueError):
        extract(str(target), str(output), source=str(source), target_lang="de")
    assert output.read_bytes() == b"existing"
