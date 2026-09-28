# this_file: src/vexy_localizzy/formats/tmx_write.py
"""Write native TMX segments plus documented catalog metadata properties."""

import json
from pathlib import Path

from lxml import etree

from vexy_localizzy.catalog import Catalog, Unit
from vexy_localizzy.exporter import LINEAGE_PROP
from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.formats.tmx_tree import (
    METADATA,
    PROJECTION,
    metadata_node,
    metadata_projections,
    parse,
    projection_key,
    selected,
    variants,
)
from vexy_localizzy.formats.xliff_xml import set_content
from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.tmx import XML_LANG


def representative(unit: Unit) -> str | None:
    if unit.plural is not None:
        if (
            unit.target is not None
            or unit.variants is not None
            or not unit.plural.forms
        ):
            raise ValueError("TMX plural requires nonempty forms and no scalar target")
        return unit.plural.forms.get("other", next(iter(unit.plural.forms.values())))
    if unit.variants is not None:
        if unit.target is not None or not unit.variants:
            raise ValueError("TMX length variants require values and no scalar target")
        return unit.variants[0]
    return unit.target


def store_metadata(tu, unit, source_lang, target_lang, ns):
    projections = metadata_projections(tu, ns)
    node = metadata_node(tu, ns)
    if node is None:
        node = etree.Element(ns + "prop", type=METADATA)
        first = tu.find(ns + "tuv")
        tu.insert(tu.index(first) if first is not None else len(tu), node)
    source_lang = canonical_locale(source_lang)
    target_lang = canonical_locale(target_lang) if target_lang is not None else None
    projections[projection_key(source_lang, target_lang)] = unit.model_dump(
        exclude={"source", "source_hash", "record_id"}
    )
    node.text = json.dumps(
        {"version": 1, "projections": projections},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def edit(tu, unit, before, target_lang, source_lang, ns):
    if unit == before:
        return
    editable = {"target", "plural", "variants", "state"}
    if unit.model_dump(exclude=editable) != before.model_dump(exclude=editable):
        raise ValueError("Unsupported retained TMX metadata/source edit")
    if (unit.plural is None) != (before.plural is None) or (unit.variants is None) != (
        before.variants is None
    ):
        raise ValueError("Unsupported retained TMX shape change")
    value = representative(unit)
    if value is None and representative(before) is not None:
        raise ValueError(
            "Removing retained TMX translations requires explicit conversion"
        )
    if value != representative(before):
        if any(node.get("type") == LINEAGE_PROP for node in tu.findall(ns + "prop")):
            raise ValueError(
                "Changing verified TMX lineage requires a separate revision"
            )
        if target_lang is None:
            raise ValueError("Select a TMX target language before editing")
        values = variants(tu, ns)
        tuv = selected(values, target_lang)
        reference = None
        if tuv is None:
            reference = selected(values, source_lang, required=True).find(ns + "seg")
            tuv = etree.SubElement(tu, ns + "tuv", {XML_LANG: target_lang})
            etree.SubElement(tuv, ns + "seg")
        elif not len(tuv.find(ns + "seg")) and not (tuv.find(ns + "seg").text or ""):
            reference = selected(values, source_lang, required=True).find(ns + "seg")
        set_content(tuv.find(ns + "seg"), value, reference)
    if (
        metadata_node(tu, ns) is not None
        or unit.state != before.state
        or unit.plural != before.plural
        or unit.variants != before.variants
    ):
        store_metadata(tu, unit, source_lang, target_lang, ns)


def fresh(catalog):
    root = etree.Element("tmx", version="1.4")
    header = etree.SubElement(
        root,
        "header",
        {
            "creationtool": "vexy-localizzy",
            "creationtoolversion": "1",
            "segtype": "sentence",
            "o-tmf": "vexy-localizzy",
            "adminlang": "en",
            "srclang": catalog.source_lang,
            "datatype": "PlainText",
        },
    )
    etree.SubElement(header, "prop", type=PROJECTION).text = projection_key(
        catalog.source_lang, catalog.target_lang
    )
    body = etree.SubElement(root, "body")
    for ordinal, unit in enumerate(catalog.units):
        tu = etree.SubElement(body, "tu", tuid=str(ordinal))
        store_metadata(tu, unit, catalog.source_lang, catalog.target_lang, "")
        for label, value in (
            (catalog.source_lang, unit.source),
            (catalog.target_lang, representative(unit)),
        ):
            if value is None:
                continue
            if label is None:
                raise ValueError("TMX target text requires a target language")
            tuv = etree.SubElement(tu, "tuv", {XML_LANG: label})
            etree.SubElement(tuv, "seg").text = value
    return etree.ElementTree(root)


def dump(catalog: Catalog, path: str | Path) -> None:
    from vexy_localizzy.formats.tmx import project

    catalog = Catalog.model_validate(catalog.model_dump())
    if catalog.document is None:
        tree = fresh(catalog)
    else:
        if catalog.document.format != "tmx":
            raise ValueError(
                "Cross-format conversion requires explicit loss acknowledgement"
            )
        raw = catalog.document.content
        before = project(
            raw, source_lang=catalog.source_lang, target_lang=catalog.target_lang
        )
        current = {unit.record_id: unit for unit in catalog.units}
        if len(current) != len(catalog.units) or set(current) != {
            unit.record_id for unit in before.units
        }:
            raise ValueError("Retained TMX message identities must match exactly")
        tree, ns = parse(raw)
        for tu, previous in zip(
            tree.getroot().find(ns + "body").findall(ns + "tu"),
            before.units,
            strict=True,
        ):
            edit(
                tu,
                current[previous.record_id],
                previous,
                catalog.target_lang,
                catalog.source_lang,
                ns,
            )
        if all(current[unit.record_id] == unit for unit in before.units):
            atomic_write(path, raw)
            return
    raw = etree.tostring(
        tree, encoding=tree.docinfo.encoding or "UTF-8", xml_declaration=True
    )
    project(raw, source_lang=catalog.source_lang, target_lang=catalog.target_lang)
    atomic_write(path, raw)
