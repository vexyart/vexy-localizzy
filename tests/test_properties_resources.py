# this_file: tests/test_properties_resources.py
"""Properties extraction respects native escapes, continuations and duplicates."""

import xml.etree.ElementTree as ET

import pytest

from vexy_localizzy.properties_resources import parse_properties
from vexy_localizzy.source_extraction import extract


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", []),
        ("# comment\n ! comment\n", []),
        (
            "key=value\nkey:second\nempty=\nsolo",
            [("key", "value"), ("key", "second"), ("empty", ""), ("solo", "")],
        ),
        (r"host\:port = first\nsecond", [("host:port", "first\nsecond")]),
        (r"emoji=\uD83D\uDE00", [("emoji", "😀")]),
        ("message=long\\\n   line", [("message", "longline")]),
        ("message=two\\\\\nnext=ok", [("message", "two\\"), ("next", "ok")]),
        ("key\\ name value  ", [("key name", "value  ")]),
        ("key=Zażółć\n", [("key", "Zażółć")]),
        ("key=value\rnext=other\r\n", [("key", "value"), ("next", "other")]),
    ],
)
def test_properties_when_valid_then_preserve_values(text, expected):
    assert parse_properties(text) == expected, (
        "Use properties syntax without lossy normalization"
    )


def test_properties_when_later_escape_invalid_then_refuse_entire_resource():
    with pytest.raises(ValueError):
        parse_properties("good=value\nbad=\\uNOTHEX\n")


def test_extraction_when_properties_paired_then_use_keys_and_last_duplicate(tmp_path):
    source, target, output = (
        tmp_path / name
        for name in ("source.properties", "target.properties", "out.tmx")
    )
    source.write_text("key=First\nkey=Last\nemoji=Smile\n")
    target.write_text(
        "\ufeffkey=Premier\nkey=Dernier\nemoji=\\uD83D\\uDE00\nextra=Absent\n"
    )
    result = extract(str(target), str(output), source=str(source), target_lang="fr")
    assert result["units"] == 2
    assert result["unmatched_keys"] == ["extra"]
    units = ET.parse(output).findall("body/tu")
    assert [
        [segment.text for segment in unit.findall("tuv/seg")] for unit in units
    ] == [["Last", "Dernier"], ["Smile", "😀"]]
    assert [unit.findtext("prop[@type='x-context']") for unit in units] == [
        "key",
        "emoji",
    ]


@pytest.mark.parametrize("bad", [b"key=\\uNOPE", b"key=\xff"])
def test_extraction_when_properties_invalid_then_preserve_destination(tmp_path, bad):
    source, target, output = (
        tmp_path / name
        for name in ("source.properties", "target.properties", "out.tmx")
    )
    source.write_text("key=Good\n")
    target.write_bytes(bad)
    output.write_bytes(b"existing")
    with pytest.raises(ValueError):
        extract(str(target), str(output), source=str(source), target_lang="de")
    assert output.read_bytes() == b"existing", (
        "Malformed resources cannot replace output"
    )
