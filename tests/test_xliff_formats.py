# this_file: tests/test_xliff_formats.py
"""XLIFF 1.2 fidelity across files, groups, inline codes and gettext plurals."""

from copy import deepcopy

import pytest
from lxml import etree

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.conversion import ConversionLoss, convert
from vexy_localizzy.formats import xliff

NS = "urn:oasis:names:tc:xliff:document:1.2"
SOURCE = f'''<?xml version="1.0" encoding="UTF-8"?>
<?retained yes?>
<xliff xmlns="{NS}" xmlns:e="urn:extension" version="1.2">
<file source-language="en" target-language="de" original="first" datatype="plaintext">
<header><e:keep a="yes"/></header><body><group id="outer">
<context-group><context context-type="x-localizzy-context">Menu</context></context-group>
<trans-unit id="a" approved="yes"><source>Open <g id="b">bold &amp; bright</g> <x id="p"/></source><target state="final">Öffne <g id="b">fett &amp; hell</g> <x id="p"/></target><note>Note</note><alt-trans><source>Alternative</source><target>Earlier</target></alt-trans><e:keep>yes</e:keep></trans-unit>
<group id="inner"><trans-unit id="empty"><source>Empty</source><target/></trans-unit></group>
</group></body></file>
<file source-language="en" target-language="de" original="second" datatype="plaintext"><body>
<trans-unit id="a"><source>Again</source></trans-unit>
<group restype="x-gettext-plurals" id="n"><context-group><context context-type="x-localizzy-context">Count</context></context-group><trans-unit id="n[one]"><source>One item</source><target state="translated">Ein</target></trans-unit><trans-unit id="n[other]"><source>One item</source><target state="translated">Viele</target></trans-unit></group>
</body></file></xliff>'''


def test_xliff_when_json_roundtrip_then_all_files_and_original_bytes_survive(tmp_path):
    source = tmp_path / "in.xlf"
    raw = SOURCE.replace("\n", "\r\n").encode()
    source.write_bytes(raw)
    catalog = xliff.load(source)
    assert len(catalog.units) == 4
    assert catalog.units[0].context == "Menu"
    assert catalog.units[0].state == "approved"
    assert "bright" in catalog.units[0].source and 'id="p"' in catalog.units[0].source
    assert catalog.units[1].target == ""
    assert catalog.units[2].target is None
    assert len({unit.key for unit in catalog.units}) == 4
    assert catalog.units[3].plural.forms == {"one": "Ein", "other": "Viele"}
    assert catalog.units[3].context == "Count"
    convert(source, "json", tmp_path / "saved.json")
    convert(tmp_path / "saved.json", "xliff", tmp_path / "out.xlf")
    assert (tmp_path / "out.xlf").read_bytes() == raw


def test_xliff_when_inline_translation_edited_then_codes_and_all_other_nodes_survive(
    tmp_path,
):
    source = tmp_path / "in.xlf"
    source.write_text(SOURCE)
    catalog = xliff.load(source)
    units = list(catalog.units)
    units[0] = units[0].model_copy(
        update={
            "target": units[0].target.replace("Öffne", "Neu").replace("fett", "stark"),
            "state": "needs_review",
        }
    )
    out = tmp_path / "out.xlf"
    xliff.dump(catalog.model_copy(update={"units": units}), out)
    before, after = etree.parse(str(source)), etree.parse(str(out))
    old, new = [tree.find(f".//{{{NS}}}trans-unit") for tree in (before, after)]
    assert new.get("approved") == "no"
    assert new.find(f"{{{NS}}}target").get("state") == "needs-review-translation"
    assert "Neu" in xliff.load(out).units[0].target
    old_target, new_target = [node.find(f"{{{NS}}}target") for node in (old, new)]
    old.replace(old_target, deepcopy(new_target))
    old.set("approved", "no")
    assert etree.tostring(before) == etree.tostring(after)


@pytest.mark.parametrize(
    "update",
    [
        {"source": "changed"},
        {"notes": []},
        {"target": "Dropped codes"},
        {"record_id": "wrong"},
        {"plural": PluralForms(forms={"one": "new"})},
    ],
)
def test_xliff_when_unsupported_edit_then_destination_untouched(tmp_path, update):
    source = tmp_path / "in.xlf"
    source.write_text(SOURCE)
    catalog = xliff.load(source)
    units = list(catalog.units)
    units[0] = units[0].model_copy(update=update)
    out = tmp_path / "out.xlf"
    out.write_bytes(b"existing")
    with pytest.raises(ValueError):
        xliff.dump(catalog.model_copy(update={"units": units}), out)
    assert out.read_bytes() == b"existing"


def test_xliff_when_fresh_plural_then_keys_context_notes_and_state_survive(tmp_path):
    catalog = Catalog(
        source_lang="en",
        target_lang="de",
        units=[
            Unit(
                key="open",
                context="Main",
                source="Open <literal>",
                target="Öffnen",
                state="approved",
                notes=["verb"],
                disambiguation="menu",
            ),
            Unit(
                key="items",
                context="C",
                source="Item",
                source_plural="Items",
                plural=PluralForms(indexing="index", forms={"0": "Ein", "1": "Viele"}),
                state="translated",
            ),
        ],
    )
    out = tmp_path / "out.xlf"
    xliff.dump(catalog, out)
    result = xliff.load(out)
    for before, after in zip(catalog.units, result.units, strict=True):
        assert before.model_dump(
            exclude={"record_id", "placeholders"}
        ) == after.model_dump(exclude={"record_id", "placeholders"})
    assert etree.parse(str(out)).getroot().get("version") == "1.2"


def test_xliff_when_group_plural_edit_then_indices_and_sources_preserved(tmp_path):
    source = tmp_path / "in.xlf"
    source.write_text(SOURCE)
    catalog = xliff.load(source)
    units = list(catalog.units)
    units[3] = units[3].model_copy(
        update={
            "plural": units[3].plural.model_copy(
                update={"forms": {"one": "Eins", "other": "Mehr"}}
            )
        }
    )
    xliff.dump(catalog.model_copy(update={"units": units}), tmp_path / "out.xlf")
    assert xliff.load(tmp_path / "out.xlf").units[3].plural == units[3].plural


@pytest.mark.parametrize(
    "source",
    [
        SOURCE.replace(
            'target-language="de" original="second"',
            'target-language="fr" original="second"',
        ),
        '<xliff version="2.0"/>',
        '<!DOCTYPE xliff [<!ENTITY secret "private">]><xliff version="1.2"/>',
    ],
)
def test_xliff_when_unsupported_or_unsafe_document_then_reject(tmp_path, source):
    path = tmp_path / "in.xlf"
    path.write_text(source)
    with pytest.raises(ValueError):
        xliff.load(path)


def test_xliff_when_cross_format_conversion_then_document_loss_reported(tmp_path):
    source = tmp_path / "in.xlf"
    source.write_text(SOURCE)
    with pytest.raises(ConversionLoss) as error:
        convert(source, "ts", tmp_path / "out.ts", plural_order=["one", "other"])
    assert "document" in {finding.data["field"] for finding in error.value.findings}


def test_xliff_when_retained_language_changes_then_all_files_updated(tmp_path):
    source = tmp_path / "in.xlf"
    source.write_text(SOURCE)
    catalog = xliff.load(source).model_copy(update={"target_lang": "fr"})
    xliff.dump(catalog, tmp_path / "out.xlf")
    assert xliff.load(tmp_path / "out.xlf").target_lang == "fr"


def test_xliff_when_retargeted_then_explicit_primary_language_attributes_follow(
    tmp_path,
):
    source = tmp_path / "in.xlf"
    source.write_text(
        SOURCE.replace(
            '<target state="final">', '<target state="final" xml:lang="de">'
        ).replace("<source>Open ", '<source xml:lang="en">Open ')
    )
    catalog = xliff.load(source).model_copy(
        update={"source_lang": "es", "target_lang": "fr"}
    )
    output = tmp_path / "out.xlf"
    xliff.dump(catalog, output)
    tree = etree.parse(str(output))
    assert (
        tree.find(f".//{{{NS}}}target").get(
            "{http://www.w3.org/XML/1998/namespace}lang"
        )
        == "fr"
    )
    assert (
        tree.find(f".//{{{NS}}}source").get(
            "{http://www.w3.org/XML/1998/namespace}lang"
        )
        == "es"
    )


def test_xliff_when_segmented_target_added_then_order_and_segmentation_preserved(
    tmp_path,
):
    source = tmp_path / "in.xlf"
    source.write_text(
        f'<xliff xmlns="{NS}" version="1.2"><file source-language="en" target-language="fr" original="a" datatype="plaintext"><body><trans-unit id="a"><source>First</source><seg-source><mrk mtype="seg" mid="1">First</mrk></seg-source></trans-unit></body></file></xliff>'
    )
    catalog = xliff.load(source)
    units = [
        catalog.units[0].model_copy(
            update={"target": catalog.units[0].source.replace("First", "Premier")}
        )
    ]
    output = tmp_path / "out.xlf"
    xliff.dump(catalog.model_copy(update={"units": units}), output)
    node = etree.parse(str(output)).find(f".//{{{NS}}}trans-unit")
    assert [etree.QName(child).localname for child in node] == [
        "source",
        "seg-source",
        "target",
    ]
    assert node.find(f"{{{NS}}}target/{{{NS}}}mrk").get("mid") == "1"
    assert xliff.load(output).units[0].state == "untranslated"


def test_xliff_when_empty_target_has_source_codes_then_cannot_drop_them(tmp_path):
    source = tmp_path / "in.xlf"
    source.write_text(
        f'<xliff xmlns="{NS}" version="1.2"><file source-language="en" original="a"><body><trans-unit id="a"><source>Open <x id="1"/></source><target/></trans-unit></body></file></xliff>'
    )
    catalog = xliff.load(source)
    units = [catalog.units[0].model_copy(update={"target": "Ouvrir"})]
    with pytest.raises(ValueError, match="inline"):
        xliff.dump(catalog.model_copy(update={"units": units}), tmp_path / "out.xlf")
    assert not (tmp_path / "out.xlf").exists()


def test_xliff_when_vanished_edit_then_reject_instead_of_dropping_state(tmp_path):
    source = tmp_path / "in.xlf"
    source.write_text(SOURCE)
    catalog = xliff.load(source)
    units = list(catalog.units)
    units[0] = units[0].model_copy(update={"state": "vanished"})
    with pytest.raises(ValueError, match="state"):
        xliff.dump(catalog.model_copy(update={"units": units}), tmp_path / "out.xlf")
    assert not (tmp_path / "out.xlf").exists()


def test_xliff_when_legacy_context_type_then_context_still_read(tmp_path):
    source = tmp_path / "legacy.xlf"
    source.write_text(SOURCE.replace("x-localizzy-context", "x-fl10n-context"))
    catalog = xliff.load(source)
    assert catalog.units[0].context == "Menu", "files written before 1.1 must load"
