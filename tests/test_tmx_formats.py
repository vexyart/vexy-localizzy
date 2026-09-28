# this_file: tests/test_tmx_formats.py
"""Catalog TMX projections must retain every original language and provenance node."""

import pytest
from lxml import etree

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.conversion import ConversionLoss, convert
from vexy_localizzy.formats import json_io, tmx

RAW = b"""<?xml version="1.0"?>
<tmx version="1.4"><header creationtool="fixture" creationtoolversion="1" segtype="sentence" o-tmf="unknown" adminlang="en" srclang="en-US" datatype="PlainText"><prop type="custom">header</prop></header><body>
<!-- retained --><tu tuid="same" creationid="author"><note>Usage note</note><prop type="x-origin">source:42</prop>
<tuv xml:lang="fr"><seg>Bonjour <bpt i="1">&lt;b&gt;</bpt>monde<ept i="1">&lt;/b&gt;</ept></seg></tuv>
<tuv xml:lang="en-US"><seg>Hello <bpt i="1">&lt;b&gt;</bpt>world<ept i="1">&lt;/b&gt;</ept></seg></tuv>
<tuv xml:lang="de"><prop type="custom">German metadata</prop><seg>Hallo Welt</seg></tuv></tu>
<tu tuid="same"><tuv xml:lang="en-US"><seg>Empty</seg></tuv><tuv xml:lang="fr"><seg></seg></tuv></tu>
</body></tmx>"""


def test_tmx_when_multilingual_json_roundtrip_then_all_bytes_survive(tmp_path):
    source = tmp_path / "memory.tmx"
    source.write_bytes(RAW)
    catalog = tmx.load(source)
    assert catalog.source_lang == "en-US" and catalog.target_lang is None
    assert len(catalog.units) == 2 and len({u.key for u in catalog.units}) == 2
    assert catalog.units[0].notes == ["Usage note"]
    convert(source, "json", tmp_path / "catalog.json")
    convert(tmp_path / "catalog.json", "tmx", tmp_path / "out.tmx")
    assert (tmp_path / "out.tmx").read_bytes() == RAW


def test_tmx_when_selected_target_edited_then_other_languages_and_provenance_survive(
    tmp_path,
):
    source = tmp_path / "memory.tmx"
    source.write_bytes(RAW)
    catalog = tmx.load(source, target_lang="fr")
    assert catalog.units[1].target == "", "Empty and absent target must remain distinct"
    units = list(catalog.units)
    units[0] = units[0].model_copy(
        update={"target": units[0].target.replace("Bonjour", "Salut")}
    )
    tmx.dump(catalog.model_copy(update={"units": units}), tmp_path / "out.tmx")
    before, after = [etree.parse(str(p)) for p in (source, tmp_path / "out.tmx")]
    old = before.find(
        'body/tu/tuv[@{http://www.w3.org/XML/1998/namespace}lang="fr"]/seg'
    )
    old.text = "Salut "
    assert etree.tostring(before) == etree.tostring(after)


def test_tmx_when_missing_target_added_then_source_inline_codes_required(tmp_path):
    source = tmp_path / "memory.tmx"
    source.write_bytes(RAW)
    catalog = tmx.load(source, target_lang="pl")
    first = catalog.units[0]
    units = [
        first.model_copy(update={"target": first.source.replace("Hello", "Witaj")}),
        catalog.units[1],
    ]
    tmx.dump(catalog.model_copy(update={"units": units}), tmp_path / "out.tmx")
    out = tmx.load(tmp_path / "out.tmx", target_lang="pl")
    assert out.units[0].target.startswith("Witaj") and out.units[1].target is None
    units[0] = first.model_copy(update={"target": "codes removed"})
    with pytest.raises(ValueError):
        tmx.dump(catalog.model_copy(update={"units": units}), tmp_path / "bad.tmx")


def test_tmx_when_fresh_rich_catalog_then_metadata_and_plural_values_roundtrip(
    tmp_path,
):
    units = [
        Unit(
            key="open",
            context="Window",
            source="Open",
            target="Ouvrir",
            notes=["Note"],
            state="approved",
            locations=["file.cpp:3"],
        ),
        Unit(
            key="count",
            context="",
            source="Item",
            source_plural="Items",
            plural=PluralForms(
                indexing="index", forms={"0": "Élément", "1": "Éléments"}
            ),
            state="translated",
        ),
        Unit(
            key="variant",
            context="",
            source="Long",
            variants=["Longue", "L."],
            state="needs_review",
        ),
    ]
    catalog = Catalog(source_lang="en", target_lang="fr", units=units)
    tmx.dump(catalog, tmp_path / "out.tmx")
    restored = tmx.load(tmp_path / "out.tmx")
    for original, actual in zip(units, restored.units, strict=True):
        assert original.model_dump(exclude={"record_id"}) == actual.model_dump(
            exclude={"record_id"}
        )
    tree = etree.parse(str(tmp_path / "out.tmx"))
    assert len(tree.findall("body/tu/tuv")) == 6


@pytest.mark.parametrize("change", ["source", "codes", "remove_target"])
def test_tmx_when_unsupported_edit_then_output_preserved(tmp_path, change):
    source = tmp_path / "memory.tmx"
    source.write_bytes(RAW)
    catalog = tmx.load(source, target_lang="fr")
    updates = (
        {"source": "changed"}
        if change == "source"
        else {"target": "" if change == "codes" else None}
    )
    units = [catalog.units[0].model_copy(update=updates), catalog.units[1]]
    output = tmp_path / "out.tmx"
    output.write_bytes(b"existing")
    with pytest.raises(ValueError):
        tmx.dump(catalog.model_copy(update={"units": units}), output)
    assert output.read_bytes() == b"existing"


def test_tmx_when_source_all_then_require_explicit_projection(tmp_path):
    source = tmp_path / "memory.tmx"
    source.write_bytes(RAW.replace(b'srclang="en-US"', b'srclang="*all*"'))
    with pytest.raises(ValueError, match="source"):
        tmx.load(source)
    assert tmx.load(source, source_lang="en-US", target_lang="fr").units[1].target == ""


def test_tmx_when_duplicate_selected_language_then_reject_ambiguous_projection(
    tmp_path,
):
    source = tmp_path / "memory.tmx"
    source.write_bytes(RAW.replace(b'xml:lang="de"', b'xml:lang="fr"'))
    with pytest.raises(ValueError, match="Ambiguous"):
        tmx.load(source, target_lang="fr")


def test_tmx_when_selected_pair_converted_then_losses_require_acknowledgement(tmp_path):
    source = tmp_path / "memory.tmx"
    source.write_bytes(RAW)
    with pytest.raises(ConversionLoss):
        convert(
            source, "ts", tmp_path / "out.ts", source_lang="en-US", target_lang="fr"
        )
    convert(
        source, "json", tmp_path / "out.json", source_lang="en-US", target_lang="fr"
    )
    assert json_io.load(tmp_path / "out.json").target_lang == "fr"


def test_tmx_when_another_projection_edited_then_prior_plural_metadata_survives(
    tmp_path,
):
    source = tmp_path / "memory.tmx"
    original = Catalog(
        source_lang="en",
        target_lang="fr",
        units=[
            Unit(
                key="items",
                context="",
                source="Item",
                plural=PluralForms(forms={"one": "Un", "other": "Plusieurs"}),
            )
        ],
    )
    tmx.dump(original, source)
    polish = tmx.load(source, target_lang="pl")
    units = [
        polish.units[0].model_copy(update={"target": "Przedmiot", "state": "approved"})
    ]
    tmx.dump(polish.model_copy(update={"units": units}), tmp_path / "out.tmx")
    assert (
        tmx.load(tmp_path / "out.tmx", target_lang="fr").units[0].plural
        == original.units[0].plural
    )
    assert tmx.load(tmp_path / "out.tmx", target_lang="pl").units[0].state == "approved"


@pytest.mark.parametrize("text", ["A\x00B", "A\x04B", "A\ud800B"])
def test_tmx_when_illegal_xml_character_then_fail_before_replacing(tmp_path, text):
    source = tmp_path / "memory.tmx"
    source.write_bytes(b"existing")
    with pytest.raises(ValueError):
        catalog = Catalog(
            source_lang="en", units=[Unit(key="a", context="", source=text)]
        )
        tmx.dump(catalog, source)
    assert source.read_bytes() == b"existing"


def test_tmx_when_existing_target_empty_then_source_codes_required(tmp_path):
    source = tmp_path / "memory.tmx"
    source.write_bytes(
        RAW.replace(
            b'Bonjour <bpt i="1">&lt;b&gt;</bpt>monde<ept i="1">&lt;/b&gt;</ept>', b""
        )
    )
    catalog = tmx.load(source, target_lang="fr")
    units = [
        catalog.units[0].model_copy(update={"target": "codes gone"}),
        catalog.units[1],
    ]
    with pytest.raises(ValueError, match="inline"):
        tmx.dump(catalog.model_copy(update={"units": units}), tmp_path / "bad.tmx")


@pytest.mark.parametrize("empty", [False, True])
def test_tmx_when_fresh_untranslated_then_declared_target_projection_survives(
    tmp_path, empty
):
    units = (
        []
        if empty
        else [Unit(key="open", context="Menu", source="Open", state="needs_review")]
    )
    catalog = Catalog(source_lang="en", target_lang="fr", units=units)
    tmx.dump(catalog, tmp_path / "out.tmx")
    restored = tmx.load(tmp_path / "out.tmx")
    assert restored.target_lang == "fr"
    assert [u.model_dump(exclude={"record_id"}) for u in restored.units] == [
        u.model_dump(exclude={"record_id"}) for u in units
    ]


def test_tmx_when_verified_corpus_lineage_then_reject_content_edit(tmp_path):
    from vexy_localizzy.corpus import Corpus

    source = tmp_path / "source.tmx"
    source.write_text(
        '<tmx><body><tu><tuv lang="en"><seg>Moon</seg></tuv><tuv lang="fr"><seg>Lune</seg></tuv></tu></body></tmx>'
    )
    with Corpus(tmp_path / "corpus.sqlite") as corpus:
        corpus.import_tmx(source, family="example", weight=1)
        corpus.export_tmx(tmp_path / "export.tmx")
    catalog = tmx.load(tmp_path / "export.tmx")
    edited = catalog.model_copy(
        update={"units": [catalog.units[0].model_copy(update={"target": "Soleil"})]}
    )
    output = tmp_path / "out.tmx"
    output.write_bytes(b"existing")
    with pytest.raises(ValueError, match="lineage"):
        tmx.dump(edited, output)
    assert output.read_bytes() == b"existing"
