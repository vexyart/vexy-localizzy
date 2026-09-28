# this_file: tests/test_json_resources.py
"""Keyed JSON extraction keeps literal keys distinct from nesting and indices."""

import json
import xml.etree.ElementTree as ET

import pytest

from vexy_localizzy.extract.json_resources import string_pairs
from vexy_localizzy.extract.single import extract


def test_json_when_nested_and_literal_keys_then_preserve_typed_paths():
    assert string_pairs(
        '{"a.b":"literal","a":{"b":"nested"},"0":"key","list":["item",null,42,true,""],"count_one":"one","count_other":"many"}'
    ) == [
        (("a.b",), "literal"),
        (("a", "b"), "nested"),
        (("0",), "key"),
        (("list", 0), "item"),
        (("list", 4), ""),
        (("count_one",), "one"),
        (("count_other",), "many"),
    ], "Typed paths must preserve every string without grouping plural-like keys"


def test_json_when_array_root_then_keep_empty_keys_and_text():
    assert string_pairs('[{"":"  kept  "},"😀",[],{}]') == [
        ((0, ""), "  kept  "),
        ((1,), "😀"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        '{"key":"one","key":"two"}',
        '{"outer":{"key":1,"key":2}}',
        '{"key":NaN}',
        '{"key":Infinity}',
        '{"key":-Infinity}',
        '{"key":"good",}',
        '{"key":"good"} trailing',
        '{"key":"\\ud800"}',
        '{"\\ud800":"value"}',
        '"scalar"',
        "null",
    ],
)
def test_json_when_invalid_or_ambiguous_then_refuse_all_pairs(text):
    with pytest.raises(ValueError):
        string_pairs(text)


def test_extract_when_json_paths_differ_then_pair_exactly_and_report_missing(tmp_path):
    source, target, output = (
        tmp_path / name for name in ("en.json", "de.json", "out.tmx")
    )
    source.write_text(
        json.dumps(
            {
                "a.b": "Literal",
                "a": {"b": "Nested"},
                "list": ["Item"],
                "count_other": "Many",
                "id": "Keep in generic extraction",
            }
        )
    )
    target.write_text(
        json.dumps(
            {
                "list": {"0": "Do not match an array"},
                "a": {"b": "Verschachtelt"},
                "a.b": "Wörtlich",
                "count_one": "No plural fallback",
                "id": "Kennung",
            }
        )
    )
    before = [path.read_bytes() for path in (source, target)]
    result = extract(str(target), str(output), source=str(source), target_lang="de-DE")
    assert result["units"] == 3
    assert result["unmatched_keys"] == ['["list","0"]', '["count_one"]']
    units = ET.parse(output).findall("body/tu")
    assert [
        (u.findtext("prop[@type='x-context']"), [s.text for s in u.findall("tuv/seg")])
        for u in units
    ] == [
        ('["a","b"]', ["Nested", "Verschachtelt"]),
        ('["a.b"]', ["Literal", "Wörtlich"]),
        ('["id"]', ["Keep in generic extraction", "Kennung"]),
    ]
    assert all(
        u.findtext("prop[@type='x-source-origin']") == str(source) for u in units
    )
    assert [path.read_bytes() for path in (source, target)] == before


@pytest.mark.parametrize(
    "bad", [b'{"good":"value","bad":}', b'{"bad":"\xff"}', b'{"bad":"\\ud800"}']
)
def test_extract_when_json_invalid_then_preserve_output(tmp_path, bad):
    source, target, output = (
        tmp_path / name for name in ("en.json", "de.json", "out.tmx")
    )
    source.write_text('{"good":"Original"}')
    target.write_bytes(bad)
    output.write_bytes(b"existing")
    with pytest.raises(ValueError):
        extract(str(target), str(output), source=str(source), target_lang="de")
    assert output.read_bytes() == b"existing"
