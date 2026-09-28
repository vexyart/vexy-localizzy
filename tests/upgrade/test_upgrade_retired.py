# this_file: tests/upgrade/test_upgrade_retired.py
"""RETIRED: absolute locations (checked against Qt lconvert) and valid output."""

from upgrade_helpers import FIXTURES, context, doc, message

from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.formats.ts_read import load_bytes
from vexy_localizzy.upgrade import build_retired, message_refs, resolve_locations

# Output of: lconvert -i relative_locations.ts -o out.ts -locations absolute
LCONVERT_ABSOLUTE = {
    "one": [("a.cpp", "10")],
    "two": [("a.cpp", "50")],
    "three": [("a.cpp", "15")],
    "four": [("b.cpp", "3"), ("a.cpp", "16")],
    "five": [("b.cpp", "5")],
    "six": [("b.cpp", "6")],
}


def test_resolve_locations_when_relative_chain_then_matches_lconvert():
    tree, ns = xml.parse((FIXTURES / "relative_locations.ts").read_bytes())
    resolve_locations(tree.getroot(), ns)
    got = {
        xml.text(m.find("source"), ns): [
            (loc.get("filename"), loc.get("line")) for loc in m.findall("location")
        ]
        for _, m in xml.messages(tree.getroot(), ns)
    }
    assert got == LCONVERT_ABSOLUTE


def test_build_retired_when_subset_then_absolute_and_grouped():
    raw = (FIXTURES / "relative_locations.ts").read_bytes()
    retired = build_retired(raw, [2, 4, 5])
    refs = message_refs(retired)
    assert [(r.context, r.source) for r in refs] == [
        ("A", "three"),
        ("A", "five"),
        ("B", "six"),
    ]
    location = refs[1].element.find("location")
    assert dict(location.attrib) == {"filename": "b.cpp", "line": "5"}


def test_build_retired_when_nothing_then_valid_empty_ts():
    raw = doc(context("C", message("A", "a")))
    retired = build_retired(raw, [])
    assert load_bytes(retired).units == []
    assert b'language="de_DE"' in retired


def test_build_retired_when_byte_refs_then_text_preserved():
    raw = doc(
        context(
            "C", message('Tab<byte value="x9"/> here', 'Tab<byte value="x9"/> hier')
        )
    )
    retired = build_retired(raw, [0])
    assert message_refs(retired)[0].source == "Tab\t here"
