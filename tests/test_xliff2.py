# this_file: tests/test_xliff2.py
"""Preserve XLIFF 2 segments, original data, modules and nontranslatable content."""

from copy import deepcopy

import pytest
from lxml import etree

from vexy_localizzy.conversion import convert
from vexy_localizzy.formats import xliff


def fixture(version):
    ns = "urn:oasis:names:tc:xliff:document:" + ("2.2" if version == "2.2" else "2.0")
    return f'''<xliff xmlns="{ns}" xmlns:m="urn:metadata" version="{version}" srcLang="en" trgLang="de"><file id="one"><skeleton href="keep"/><group id="g"><unit id="u" name="Title"><m:metadata>keep</m:metadata><notes><note>Keep note</note></notes><originalData><data id="d">native</data></originalData><segment id="first" state="final"><source>Open <ph id="1" dataRef="d"/></source><target>Öffne <ph id="1" dataRef="d"/></target></segment><ignorable><source> </source><target> </target></ignorable><segment id="second"><source>Again</source></segment></unit></group></file><file id="two"><unit id="u"><segment><source>Last</source><target/></segment></unit></file></xliff>'''


@pytest.mark.parametrize("version", ["2.0", "2.1", "2.2"])
def test_xliff2_when_json_roundtrip_then_all_segments_and_raw_bytes_survive(
    tmp_path, version
):
    source = tmp_path / "in.xlf"
    raw = fixture(version).encode()
    source.write_bytes(raw)
    catalog = xliff.load(source)
    assert len(catalog.units) == 4
    assert len({unit.key for unit in catalog.units}) == 4
    assert catalog.units[0].state == "approved"
    assert catalog.units[0].notes == ["Keep note"]
    assert catalog.units[1].source == " "
    assert catalog.units[2].target is None
    assert catalog.units[3].target == ""
    convert(source, "json", tmp_path / "saved.json")
    convert(tmp_path / "saved.json", "xliff", tmp_path / "out.xlf")
    assert (tmp_path / "out.xlf").read_bytes() == raw


def test_xliff2_when_inline_edit_then_only_target_and_requested_state_change(tmp_path):
    source = tmp_path / "in.xlf"
    source.write_text(fixture("2.2"))
    catalog = xliff.load(source)
    units = list(catalog.units)
    units[0] = units[0].model_copy(
        update={
            "target": units[0].target.replace("Öffne", "Neu"),
            "state": "translated",
        }
    )
    output = tmp_path / "out.xlf"
    xliff.dump(catalog.model_copy(update={"units": units}), output)
    before, after = [etree.parse(str(path)) for path in (source, output)]
    ns = "{urn:oasis:names:tc:xliff:document:2.2}"
    old, new = [tree.find(f".//{ns}segment") for tree in (before, after)]
    assert new.get("state") == "translated"
    old.replace(old.find(ns + "target"), deepcopy(new.find(ns + "target")))
    old.set("state", "translated")
    assert etree.tostring(before) == etree.tostring(after)


@pytest.mark.parametrize(
    "index,updates",
    [
        (0, {"target": "Lost inline code"}),
        (1, {"target": "changed ignorable"}),
        (0, {"notes": []}),
        (2, {"state": "approved"}),
    ],
)
def test_xliff2_when_unsupported_edit_then_existing_output_survives(
    tmp_path, index, updates
):
    source = tmp_path / "in.xlf"
    source.write_text(fixture("2.0"))
    catalog = xliff.load(source)
    units = list(catalog.units)
    units[index] = units[index].model_copy(update=updates)
    output = tmp_path / "out.xlf"
    output.write_bytes(b"existing")
    with pytest.raises(ValueError):
        xliff.dump(catalog.model_copy(update={"units": units}), output)
    assert output.read_bytes() == b"existing"


def test_xliff2_when_missing_target_added_then_language_required(tmp_path):
    source = tmp_path / "in.xlf"
    source.write_text(
        '<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" version="2.0" srcLang="en"><file id="f"><unit id="u"><segment><source>Open</source></segment></unit></file></xliff>'
    )
    catalog = xliff.load(source)
    units = [
        catalog.units[0].model_copy(update={"target": "Ouvrir", "state": "translated"})
    ]
    with pytest.raises(ValueError, match="language|trgLang"):
        xliff.dump(catalog.model_copy(update={"units": units}), tmp_path / "out.xlf")
    xliff.dump(
        catalog.model_copy(update={"units": units, "target_lang": "fr"}),
        tmp_path / "out.xlf",
    )
    assert xliff.load(tmp_path / "out.xlf").units[0].target == "Ouvrir"


def test_xliff2_when_retargeted_then_explicit_target_language_follows(tmp_path):
    source = tmp_path / "in.xlf"
    source.write_text(
        fixture("2.0").replace("<target>Öffne ", '<target xml:lang="de">Öffne ')
    )
    catalog = xliff.load(source).model_copy(update={"target_lang": "fr"})
    xliff.dump(catalog, tmp_path / "out.xlf")
    tree = etree.parse(str(tmp_path / "out.xlf"))
    assert (
        tree.find(".//{urn:oasis:names:tc:xliff:document:2.0}target").get(
            "{http://www.w3.org/XML/1998/namespace}lang"
        )
        == "fr"
    )


def test_xliff2_when_unrepresentable_review_state_then_refuse_instead_of_downgrading(
    tmp_path,
):
    source = tmp_path / "in.xlf"
    source.write_text(fixture("2.0"))
    catalog = xliff.load(source)
    units = list(catalog.units)
    units[0] = units[0].model_copy(update={"state": "needs_review"})
    with pytest.raises(ValueError, match="state"):
        xliff.dump(catalog.model_copy(update={"units": units}), tmp_path / "out.xlf")
    assert not (tmp_path / "out.xlf").exists()
