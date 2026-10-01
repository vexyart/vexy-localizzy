# this_file: tests/test_catalog_formats.py
"""Lossless catalog persistence and Qt translation editing contracts."""

import json

import pytest
from lxml import etree

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.formats import json_io, ts

RICH_TS = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<?catalog retain?>
<TS version="2.1" language="pl_PL" sourcelanguage="en" custom="keep">
  <extra-custom value="yes">opaque</extra-custom>
  <dependencies><dependency catalog="base"/></dependencies>
  <!-- root message, no context -->
  <message id="root"><source>Root</source><translation type="obsolete">Old</translation></message>
  <context encoding="UTF-8"><name>Window</name><comment>Context note</comment>
    <message id="open"><location filename="panel.ui" line="12"/><location line="+2"/>
      <source>Open<byte value="x4"/> %1</source><oldsource>Earlier</oldsource>
      <comment>verb</comment><oldcomment>old hint</oldcomment>
      <extracomment>Developer</extracomment><translatorcomment>Translator</translatorcomment>
      <translation type="unfinished" custom="preserve">Otworz</translation>
      <userdata>opaque</userdata><extra-private test="keep">metadata</extra-private>
    </message>
    <message numerus="yes"><source>%n items</source><translation type="unfinished">
      <numerusform variants="yes"><lengthvariant>One item</lengthvariant><lengthvariant>One</lengthvariant></numerusform>
      <numerusform>Few</numerusform><numerusform>Many</numerusform>
    </translation></message>
    <message><source>Width</source><translation variants="yes"><lengthvariant>Width label</lengthvariant><lengthvariant>W</lengthvariant></translation></message>
    <message><source>Empty</source><translation/></message>
    <message><source>Absent</source></message>
    <message><source>Same!</source><translation>A</translation></message>
    <message><source>Same?</source><translation>B</translation></message>
  </context>
</TS>
"""


def changed(catalog, index, **updates):
    units = list(catalog.units)
    units[index] = units[index].model_copy(update=updates)
    return catalog.model_copy(update={"units": units})


def test_ts_when_unchanged_then_original_bytes_and_identity_survive_json(tmp_path):
    source = tmp_path / "input.ts"
    source.write_bytes(RICH_TS)
    catalog = ts.load(source)
    assert len(catalog.units) == 8
    assert len({unit.key for unit in catalog.units}) == 8
    assert len({unit.record_id for unit in catalog.units}) == 8
    assert catalog.units[0].context == ""
    assert catalog.units[1].source == "Open\x04 %1"
    assert catalog.units[4].target == ""
    assert catalog.units[5].target is None
    assert catalog.units[2].plural.indexing == "index"
    assert catalog.units[2].plural.forms == {"0": "One item", "1": "Few", "2": "Many"}
    assert catalog.units[2].plural.variants == {"0": ["One item", "One"]}
    assert catalog.units[3].variants == ["Width label", "W"]
    stored = tmp_path / "catalog.json"
    json_io.dump(catalog, stored)
    assert json_io.load(stored) == catalog
    source.unlink()
    output = tmp_path / "output.ts"
    ts.dump(json_io.load(stored), output)
    assert output.read_bytes() == RICH_TS, (
        "Unchanged round trips must retain exact bytes"
    )


def without_translation(raw, index):
    tree = etree.fromstring(raw)
    messages = tree.xpath("./message | ./context/message")
    translation = messages[index].find("translation")
    if translation is not None:
        messages[index].remove(translation)
    return etree.tostring(tree, method="c14n")


def test_ts_when_one_translation_edited_then_other_structure_is_unchanged(tmp_path):
    source = tmp_path / "source.ts"
    source.write_bytes(RICH_TS)
    catalog = changed(ts.load(source), 1, target="Otw\x04orz & <tag>", state="approved")
    output = tmp_path / "edited.ts"
    ts.dump(catalog, output)
    loaded = ts.load(output)
    assert loaded.units[1].target == "Otw\x04orz & <tag>"
    assert loaded.units[1].state == "translated"
    assert without_translation(output.read_bytes(), 1) == without_translation(
        RICH_TS, 1
    )
    translation = etree.parse(output).find("context/message/translation")
    assert translation.get("custom") == "preserve"
    assert translation.get("type") is None
    assert b"<?catalog retain?>" in output.read_bytes()
    assert b"<!DOCTYPE TS>" in output.read_bytes()


def test_ts_when_plural_or_variants_edited_then_positions_and_metadata_survive(
    tmp_path,
):
    source = tmp_path / "source.ts"
    source.write_bytes(RICH_TS)
    catalog = ts.load(source)
    plural = catalog.units[2].plural.model_copy(
        update={
            "forms": {"0": "Jeden element", "1": "Kilka", "2": "Wiele"},
            "variants": {"0": ["Jeden element", "Jeden"]},
        }
    )
    catalog = changed(catalog, 2, plural=plural)
    catalog = changed(catalog, 3, variants=["Szerokosc", "Szer."])
    output = tmp_path / "edited.ts"
    ts.dump(catalog, output)
    loaded = ts.load(output)
    assert loaded.units[2].plural == plural
    assert loaded.units[3].variants == ["Szerokosc", "Szer."]
    assert loaded.units[2].state == "untranslated"
    assert (
        etree.parse(output)
        .find("context/message[2]/translation/numerusform")
        .get("variants")
        == "yes"
    )


@pytest.mark.parametrize(
    "updates",
    [
        {"source": "Different"},
        {"context": "Other"},
        {"record_id": "ts:999"},
        {"notes": ["silently lost?"]},
        {"locations": []},
        {"target": None},
    ],
)
def test_ts_when_unsupported_edit_then_existing_destination_survives(tmp_path, updates):
    source = tmp_path / "source.ts"
    source.write_bytes(RICH_TS)
    output = tmp_path / "output.ts"
    output.write_bytes(b"existing")
    with pytest.raises(ValueError):
        ts.dump(changed(ts.load(source), 1, **updates), output)
    assert output.read_bytes() == b"existing"


@pytest.mark.parametrize("kind", ["missing", "duplicate", "extra"])
def test_ts_when_message_set_changes_then_refuse_silent_loss(tmp_path, kind):
    source = tmp_path / "source.ts"
    source.write_bytes(RICH_TS)
    catalog = ts.load(source)
    units = list(catalog.units)
    if kind == "missing":
        units.pop()
    elif kind == "duplicate":
        units[-1] = units[0]
    else:
        units.append(Unit(key="new", context="", source="Added"))
    with pytest.raises(ValueError):
        ts.dump(catalog.model_copy(update={"units": units}), tmp_path / "out.ts")


def test_ts_when_namespace_and_reordered_catalog_then_correct_message_edited(tmp_path):
    source = tmp_path / "source.ts"
    source.write_text(
        '<TS xmlns="urn:qt" xmlns:x="urn:extra" language="de"><x:message/><context><name>C</name><message><source>A</source><translation>B</translation></message><message><source>C</source><translation>D</translation></message></context></TS>'
    )
    catalog = ts.load(source)
    assert len(catalog.units) == 2
    catalog = changed(catalog, 0, target="E")
    catalog = catalog.model_copy(update={"units": list(reversed(catalog.units))})
    output = tmp_path / "out.ts"
    ts.dump(catalog, output)
    assert [u.target for u in ts.load(output).units] == ["E", "D"]
    assert b"x:message" in output.read_bytes()


def test_ts_when_missing_translation_added_then_message_order_preserved(tmp_path):
    source = tmp_path / "source.ts"
    source.write_bytes(RICH_TS)
    output = tmp_path / "out.ts"
    ts.dump(
        changed(ts.load(source), 5, target="Now present", state="needs_review"), output
    )
    assert ts.load(output).units[5].target == "Now present"
    assert without_translation(RICH_TS, 5) == without_translation(
        output.read_bytes(), 5
    )


@pytest.mark.parametrize(
    "raw",
    [
        b"<wrong/>",
        b'<!DOCTYPE TS [<!ENTITY x "text">]><TS><message><source>&x;</source></message></TS>',
        b'<TS><message><source>A<byte value="broken"/></source></message></TS>',
    ],
)
def test_ts_when_invalid_document_then_parse_fails(tmp_path, raw):
    path = tmp_path / "bad.ts"
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        ts.load(path)


@pytest.mark.parametrize("mutation", ["version", "unknown", "bytes", "hash"])
def test_json_when_invalid_envelope_then_refuse(tmp_path, mutation):
    source = tmp_path / "source.ts"
    source.write_bytes(RICH_TS)
    path = tmp_path / "catalog.json"
    json_io.dump(ts.load(source), path)
    data = json.loads(path.read_text())
    if mutation == "version":
        data["schema_version"] = 2
    elif mutation == "unknown":
        data["unrecognized"] = True
    elif mutation == "bytes":
        data["document"]["content_base64"] = "!"
    else:
        data["document"]["sha256"] = "0" * 64
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        json_io.load(path)


def test_ts_when_fresh_catalog_then_simple_text_and_indexed_plurals_roundtrip(tmp_path):
    catalog = Catalog(
        source_lang="en",
        target_lang="pl",
        units=[
            Unit(
                key="open",
                context="Window",
                source="Open %1",
                target="Otworz %1",
                state="needs_review",
            ),
            Unit(
                key="items",
                context="Window",
                source="%n items",
                plural=PluralForms(
                    indexing="index", forms={"0": "Jeden", "1": "Kilka", "2": "Wiele"}
                ),
            ),
        ],
    )
    output = tmp_path / "new.ts"
    ts.dump(catalog, output)
    loaded = ts.load(output)
    assert [(u.key, u.source, u.target) for u in loaded.units] == [
        ("open", "Open %1", "Otworz %1"),
        ("items", "%n items", None),
    ]
    assert loaded.units[1].plural == catalog.units[1].plural


def test_ts_when_cldr_plural_mapping_unknown_then_refuse_to_guess(tmp_path):
    catalog = Catalog(
        source_lang="en",
        target_lang="xx",
        units=[
            Unit(
                key="n",
                context="",
                source="%n",
                plural=PluralForms(forms={"one": "One", "other": "Many"}),
            )
        ],
    )
    with pytest.raises(ValueError, match="positional"):
        ts.dump(catalog, tmp_path / "new.ts")


def test_ts_when_internal_dtd_present_then_translation_edit_preserves_declarations(
    tmp_path,
):
    source = tmp_path / "source.ts"
    source.write_text(
        '<!DOCTYPE TS [<!ATTLIST TS extra CDATA "defaulted">]><TS><message><source>A</source><translation>B</translation></message></TS>'
    )
    output = tmp_path / "edited.ts"
    ts.dump(changed(ts.load(source), 0, target="C"), output)
    parsed = etree.parse(output, etree.XMLParser(attribute_defaults=True))
    assert parsed.getroot().get("extra") == "defaulted", (
        "An edit must retain DTD default-attribute semantics"
    )
    assert b"<!ATTLIST TS extra" in output.read_bytes()


def test_ts_when_plural_scalar_changed_into_variants_then_refuse_implicit_conversion(
    tmp_path,
):
    source = tmp_path / "source.ts"
    source.write_bytes(RICH_TS)
    catalog = ts.load(source)
    plural = catalog.units[2].plural.model_copy(
        update={"variants": {"0": ["One item", "One"], "1": ["Few", "F"]}}
    )
    output = tmp_path / "out.ts"
    output.write_bytes(b"existing")
    with pytest.raises(ValueError, match="shape"):
        ts.dump(changed(catalog, 2, plural=plural), output)
    assert output.read_bytes() == b"existing"


def test_catalog_when_origin_format_legacy_or_default_then_accepted():
    from vexy_localizzy.catalog import Catalog

    assert Catalog(source_lang="en").origin_format == "localizzy", "the default origin"
    legacy = Catalog.model_validate({"source_lang": "en", "origin_format": "fl10n"})
    assert legacy.origin_format == "fl10n", "catalog JSON written before 1.1 must load"
