# this_file: src/vexy_localizzy/formats/xliff2.py
"""Retained XLIFF 2.0/2.1/2.2 documents, preserving segmentation and modules."""

from pathlib import Path

from lxml import etree

from vexy_localizzy.catalog import Catalog, Unit, detect_placeholders
from vexy_localizzy.formats.document import SourceDocument, atomic_write
from vexy_localizzy.formats.xliff_read import message
from vexy_localizzy.formats.xliff_write import target_text
from vexy_localizzy.formats.xliff_xml import read_tree, update_languages

STATES = {
    "initial": "untranslated",
    "translated": "translated",
    "reviewed": "approved",
    "final": "approved",
}
OUTPUT_STATES = {
    "untranslated": "initial",
    "translated": "translated",
    "approved": "final",
}


def parse(raw: bytes) -> tuple[etree._ElementTree, str]:
    tree = read_tree(raw)
    root = tree.getroot()
    namespace = etree.QName(root).namespace
    if (
        etree.QName(root).localname != "xliff"
        or root.get("version") not in ("2.0", "2.1", "2.2")
        or namespace
        not in (
            "urn:oasis:names:tc:xliff:document:2.0",
            "urn:oasis:names:tc:xliff:document:2.2",
        )
    ):
        raise ValueError("Expected XLIFF 2 document")
    ns = "{" + namespace + "}"
    if not root.get("srcLang") or not root.findall(ns + "file"):
        raise ValueError("XLIFF 2 requires srcLang and file elements")
    return tree, ns


def segments(element, ns):
    for child in element:
        if child.tag in (ns + "segment", ns + "ignorable"):
            yield child
        elif child.tag in (ns + "file", ns + "group", ns + "unit"):
            yield from segments(child, ns)


def project(raw: bytes) -> Catalog:
    tree, ns = parse(raw)
    root = tree.getroot()
    units, keys = [], set()
    for index, segment in enumerate(segments(root, ns)):
        parent = segment.getparent()
        source, target = message(segment, ns)
        if target is not None and not root.get("trgLang"):
            raise ValueError("XLIFF targets require trgLang")
        status = STATES.get(segment.get("state", "initial"), "needs_review")
        if target is None:
            status = "untranslated"
        key = parent.get("id", str(index))
        siblings = [
            child for child in parent if child.tag in (ns + "segment", ns + "ignorable")
        ]
        if len(siblings) > 1:
            key += "/" + segment.get("id", str(siblings.index(segment)))
        while key in keys:
            key += f"~{index}"
        keys.add(key)
        units.append(
            Unit(
                key=key,
                context=parent.get("name", ""),
                source=source,
                target=target,
                state=status,
                notes=[
                    "".join(note.itertext())
                    for note in parent.findall(f"{ns}notes/{ns}note")
                ],
                placeholders=detect_placeholders(source),
                record_id=f"xliff2:{index}",
            )
        )
    return Catalog(
        source_lang=root.get("srcLang"),
        target_lang=root.get("trgLang"),
        origin_format="xliff",
        document=SourceDocument.capture(raw, "xliff"),
        units=units,
    )


def edit(node: etree._Element, unit: Unit, before: Unit, ns: str) -> None:
    if unit.target is None and unit.state != "untranslated":
        raise ValueError("Removing a target requires resetting its state")
    if node.tag == ns + "ignorable" and unit != before:
        raise ValueError(
            "XLIFF ignorable content is retained, not editable as translation"
        )
    if unit.model_dump(exclude={"target", "state"}) != before.model_dump(
        exclude={"target", "state"}
    ):
        raise ValueError("Unsupported retained XLIFF 2 metadata edit")
    if unit.target != before.target:
        target_text(node, unit.target, ns)
    if unit.state != before.state:
        if unit.state not in OUTPUT_STATES or (
            unit.target is None and unit.state != "untranslated"
        ):
            raise ValueError("XLIFF segment state requires a representable translation")
        node.set("state", OUTPUT_STATES[unit.state])
        node.attrib.pop("subState", None)


def dump(catalog: Catalog, path: str | Path) -> None:
    catalog = Catalog.model_validate(catalog.model_dump())
    raw = catalog.document.content
    before = project(raw)
    tree, ns = parse(raw)
    root = tree.getroot()
    current = {unit.record_id: unit for unit in catalog.units}
    if len(current) != len(catalog.units) or set(current) != {
        unit.record_id for unit in before.units
    }:
        raise ValueError("Retained XLIFF 2 message identities must match exactly")
    for node, previous in zip(segments(root, ns), before.units, strict=True):
        edit(node, current[previous.record_id], previous, ns)
        update_languages(node, ns, before, catalog)
    if (
        catalog.source_lang == before.source_lang
        and catalog.target_lang == before.target_lang
        and all(current[unit.record_id] == unit for unit in before.units)
    ):
        atomic_write(path, raw)
        return
    root.set("srcLang", catalog.source_lang)
    if catalog.target_lang is None:
        root.attrib.pop("trgLang", None)
    else:
        root.set("trgLang", catalog.target_lang)
    output = etree.tostring(
        tree, encoding=tree.docinfo.encoding or "UTF-8", xml_declaration=True
    )
    project(output)
    atomic_write(path, output)
