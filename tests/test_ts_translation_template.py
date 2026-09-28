# this_file: tests/test_ts_translation_template.py
"""Explicit locale preparation preserves source metadata and excluded messages."""

import pytest
from lxml import etree

from vexy_localizzy.formats import ts
from vexy_localizzy.formats.ts_template import prepare_translation

SOURCE = b"""<?xml version="1.0"?><!DOCTYPE TS><?keep data?>
<TS version="2.1" language="en" sourcelanguage="en" custom="yes">
<context><name>Window</name><comment>Keep context</comment>
<message id="one"><location filename="panel.ui" line="4"/><source>Open %1</source><comment>verb</comment><extracomment>Note</extracomment><translation custom="keep">English</translation><extra-opaque>x</extra-opaque></message>
<message id="n" numerus="yes"><source>%n items</source><translation><numerusform variants="yes"><lengthvariant length="full">%n items</lengthvariant><lengthvariant length="short">%n</lengthvariant></numerusform><numerusform>%n items</numerusform></translation></message>
<message id="v"><source>Width</source><translation variants="yes"><lengthvariant>Width</lengthvariant><lengthvariant>W</lengthvariant></translation></message>
<message id="absent"><source>Missing target</source><extra-info>Keep</extra-info></message>
<message id="empty"><source/><translation>Keep empty-source target</translation></message>
<message id="obsolete"><source>Old</source><translation type="obsolete">Keep old</translation></message>
</context></TS>"""


def source_metadata(raw):
    root = etree.fromstring(raw)
    root.attrib.pop("language", None)
    for message in root.findall("context/message")[:4]:
        target = message.find("translation")
        if target is not None:
            message.remove(target)
    return etree.tostring(root, method="c14n")


def test_prepare_when_target_has_more_plural_forms_then_preserve_all_source_structure(
    tmp_path,
):
    prepared = prepare_translation(SOURCE, target_lang="pl", plural_count=3)
    assert prepared.target_lang == "pl"
    assert len(prepared.units) == 6
    assert prepared.units[0].target == ""
    assert prepared.units[1].plural.forms == {"0": "", "1": "", "2": ""}
    assert prepared.units[1].plural.variants == {str(i): ["", ""] for i in range(3)}
    assert prepared.units[2].variants == ["", ""]
    assert prepared.units[3].target == ""
    assert all(u.state == "untranslated" for u in prepared.units[:4])
    output = tmp_path / "prepared.ts"
    ts.dump(prepared, output)
    assert source_metadata(output.read_bytes()) == source_metadata(SOURCE)
    assert b'custom="keep"' in output.read_bytes()
    assert b"<?keep data?>" in output.read_bytes()
    assert b'length="full"' in output.read_bytes()
    assert prepared.units[4].target == "Keep empty-source target"
    assert prepared.units[5].state == "vanished"
    assert ts.load(output) == prepared


def test_prepare_when_target_has_fewer_forms_then_all_length_variants_remain():
    prepared = prepare_translation(SOURCE, target_lang="ja", plural_count=1)
    assert prepared.units[1].plural.forms == {"0": ""}
    assert prepared.units[1].plural.variants == {"0": ["", ""]}


@pytest.mark.parametrize("count", [0, 7, -1, True, 1.5])
def test_prepare_when_plural_rule_invalid_then_reject(count):
    with pytest.raises(ValueError):
        prepare_translation(SOURCE, target_lang="pl", plural_count=count)


def test_prepare_when_translation_has_unknown_xml_then_do_not_silently_remove():
    raw = SOURCE.replace(
        b">English</translation>", b"><opaque>Keep</opaque></translation>"
    )
    with pytest.raises(ValueError, match="unsupported"):
        prepare_translation(raw, target_lang="pl", plural_count=3)


def test_prepare_when_plural_has_no_existing_forms_then_create_complete_native_shape():
    raw = b'<TS><context><name>C</name><message numerus="yes"><source>%n files</source></message></context></TS>'
    prepared = prepare_translation(raw, target_lang="ru", plural_count=3)
    assert prepared.units[0].plural.forms == {"0": "", "1": "", "2": ""}


def test_prepare_when_namespace_present_then_edit_native_messages_only():
    raw = b'<TS xmlns="urn:qt" xmlns:x="urn:opaque" language="en"><x:message>keep</x:message><message><source>Hello</source><translation>English</translation></message></TS>'
    prepared = prepare_translation(raw, target_lang="de", plural_count=2)
    assert len(prepared.units) == 1 and prepared.units[0].target == ""
    assert b"x:message" in prepared.document.content


@pytest.mark.parametrize(
    "last_form",
    [
        b'<numerusform><opaque important="yes">KEEP</opaque></numerusform>',
        b'<numerusform variants="yes"><lengthvariant><opaque>KEEP</opaque></lengthvariant></numerusform>',
    ],
)
def test_prepare_when_removed_plural_contains_unknown_xml_then_reject(last_form):
    raw = (
        b'<TS language="en"><context><name>C</name><message numerus="yes"><source>%n items</source><translation><numerusform>%n item</numerusform>'
        + last_form
        + b"</translation></message></context></TS>"
    )
    with pytest.raises(ValueError, match="unsupported"):
        prepare_translation(raw, target_lang="ja", plural_count=1)
