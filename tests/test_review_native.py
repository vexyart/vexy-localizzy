# this_file: tests/test_review_native.py
"""Review edits retain native slots and can be exported without source metadata loss."""

import xml.etree.ElementTree as ET

import pytest

from vexy_localizzy.formats import json_io, ts
from vexy_localizzy.review.store import ReviewEdit, ReviewStore

SOURCE = """<TS language="pl" sourcelanguage="en"><context><name>Menu</name><message id="n" numerus="yes"><location filename="menu.ui" line="7"/><source>%n items</source><comment>noun</comment><translation type="unfinished"><numerusform>%n element</numerusform><numerusform>%n elementy</numerusform><numerusform variants="yes"><lengthvariant>%n elementów</lengthvariant><lengthvariant>%n el.</lengthvariant></numerusform></translation><extra-note>keep</extra-note></message></context></TS>""".encode()


def prepared(tmp_path):
    path = tmp_path / "source.ts"
    path.write_bytes(SOURCE)
    catalog = ts.load(path)
    json_io.dump(catalog, tmp_path / "catalog.json")
    store = ReviewStore(
        tmp_path, {"main": "catalog.json"}, plural_forms={"main": ("0", "1", "2")}
    )
    return store, catalog.units[0].key


def test_edit_when_native_plural_variants_then_export_every_slot_and_preserve_metadata(
    tmp_path,
):
    store, key = prepared(tmp_path)
    original = store.open("main")
    values = {
        "0": "%n pozycja",
        "1": "%n pozycje",
        "2:0": "%n pozycji",
        "2:1": "%n poz.",
    }
    saved = store.save(
        "main",
        ReviewEdit(
            key=key, revision=original.revision, targets=values, action="approve"
        ),
    )
    assert store.open("main") == saved
    output = tmp_path / "reviewed.ts"
    ts.dump(saved.catalog, output)
    before, after = ET.fromstring(SOURCE), ET.parse(output).getroot()
    old, new = before.find(".//translation"), after.find(".//translation")
    assert new.get("type") is None
    assert [n.text for n in new.findall("numerusform")[:2]] == [
        "%n pozycja",
        "%n pozycje",
    ]
    assert [n.text for n in new.findall("numerusform/lengthvariant")] == [
        "%n pozycji",
        "%n poz.",
    ]
    before.find(".//message").remove(old)
    after.find(".//message").remove(new)
    assert ET.tostring(before) == ET.tostring(after)


@pytest.mark.parametrize(
    "targets",
    [
        {"0": "%n pozycja"},
        {
            "0": "%n pozycja",
            "1": "%n pozycje",
            "2:0": "%n pozycji",
            "2:1": "Missing placeholder",
        },
    ],
)
def test_edit_when_native_slot_missing_or_invalid_then_leave_disk_unchanged(
    tmp_path, targets
):
    store, key = prepared(tmp_path)
    original = store.open("main")
    with pytest.raises(ValueError):
        store.save(
            "main", ReviewEdit(key=key, revision=original.revision, targets=targets)
        )
    assert store.open("main") == original
