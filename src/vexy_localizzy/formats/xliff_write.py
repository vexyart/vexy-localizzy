# this_file: src/vexy_localizzy/formats/xliff_write.py
"""Atomic XLIFF 1.2 output with narrowly scoped retained-document edits."""

from pathlib import Path

from lxml import etree

from vexy_localizzy.catalog import Catalog, Unit
from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.formats.xliff_read import project
from vexy_localizzy.formats.xliff_xml import (
    NAMESPACE,
    PLURALS,
    forms,
    parse,
    records,
    set_content,
    update_languages,
)

STATES = {
    "untranslated": "new",
    "needs_review": "needs-review-translation",
    "translated": "translated",
    "approved": "final",
}


def target_text(node: etree._Element, value: str | None, ns: str) -> None:
    target = node.find(ns + "target")
    if value is None:
        if target is not None:
            if len(target) or set(target.attrib) - {"state"}:
                raise ValueError("Removing an XLIFF target would lose inline metadata")
            node.remove(target)
        return
    source = node.find(ns + "source")
    segmented = node.find(ns + "seg-source")
    reference = source if segmented is None else segmented
    if target is None:
        target = etree.Element(ns + "target")
        node.insert(node.index(reference) + 1, target)
        set_content(target, value, reference)
    else:
        set_content(
            target,
            value,
            reference
            if not len(target) and not (target.text or "").strip()
            else target,
        )


def set_state(node: etree._Element, state: str, ns: str) -> None:
    if state not in STATES:
        raise ValueError("XLIFF cannot represent this state")
    target = node.find(ns + "target")
    if target is None:
        if state != "untranslated":
            raise ValueError("XLIFF translation state requires a target")
        if "approved" in node.attrib:
            node.set("approved", "no")
        return
    target.set("state", STATES[state])
    if state == "approved" or "approved" in node.attrib:
        node.set("approved", "yes" if state == "approved" else "no")


def edit(node: etree._Element, unit: Unit, before: Unit, ns: str) -> None:
    if unit.model_dump(exclude={"target", "plural", "state"}) != before.model_dump(
        exclude={"target", "plural", "state"}
    ):
        raise ValueError("Unsupported retained XLIFF metadata edit")
    if (unit.plural is None) != (before.plural is None):
        raise ValueError("Changing XLIFF plural shape requires explicit conversion")
    if unit.plural is not None:
        if (
            unit.plural.model_dump(exclude={"forms"})
            != before.plural.model_dump(exclude={"forms"})
            or set(unit.plural.forms) != set(before.plural.forms)
            or unit.target is not None
        ):
            raise ValueError("Retained XLIFF plural structure must match")
        children = forms(node, ns)
        for key, child in children.items():
            if unit.plural.forms[key] != before.plural.forms[key]:
                target_text(child, unit.plural.forms[key], ns)
            if unit.state != before.state:
                set_state(child, unit.state, ns)
    else:
        if unit.target is None and unit.state != "untranslated":
            raise ValueError("Removing a target requires resetting its state")
        if unit.target != before.target:
            target_text(node, unit.target, ns)
        if unit.state != before.state or (
            before.target is None and unit.target is not None
        ):
            set_state(node, unit.state, ns)


def add_metadata(node: etree._Element, unit: Unit, ns: str) -> None:
    for note in unit.notes:
        etree.SubElement(node, ns + "note").text = note
    values = {
        "x-fl10n-context": unit.context,
        "x-fl10n-disambiguation": unit.disambiguation,
        "x-localizzy-source-plural": unit.source_plural,
    }
    if unit.plural is not None:
        values["x-localizzy-plural-indexing"] = unit.plural.indexing
    values = {key: value for key, value in values.items() if value is not None}
    group = etree.SubElement(node, ns + "context-group")
    for kind, value in values.items():
        etree.SubElement(group, ns + "context", {"context-type": kind}).text = value


def fresh(catalog: Catalog) -> tuple[etree._ElementTree, str]:
    ns = "{" + NAMESPACE + "}"
    root = etree.Element(ns + "xliff", version="1.2", nsmap={None: NAMESPACE})
    file = etree.SubElement(root, ns + "file", datatype="plaintext", original="catalog")
    body = etree.SubElement(file, ns + "body")
    keys = set()
    for unit in catalog.units:
        if unit.key in keys:
            raise ValueError("Fresh XLIFF message IDs must be unique")
        keys.add(unit.key)
        if unit.variants is not None or (
            unit.plural is not None
            and (unit.plural.variants or unit.plural.icu or not unit.plural.forms)
        ):
            raise ValueError(
                "XLIFF cannot represent these plural/length-variant fields"
            )
        if unit.plural is None:
            node = etree.SubElement(body, ns + "trans-unit", id=unit.key)
            etree.SubElement(node, ns + "source").text = unit.source
            target_text(node, unit.target, ns)
            set_state(node, unit.state, ns)
            add_metadata(node, unit, ns)
        else:
            node = etree.SubElement(body, ns + "group", id=unit.key, restype=PLURALS)
            add_metadata(node, unit, ns)
            for key, text in unit.plural.forms.items():
                child = etree.SubElement(
                    node, ns + "trans-unit", id=f"{unit.key}[{key}]"
                )
                etree.SubElement(child, ns + "source").text = unit.source
                target_text(child, text, ns)
                set_state(child, unit.state, ns)
    return etree.ElementTree(root), ns


def dump(catalog: Catalog, path: str | Path) -> None:
    """Preserve exact original bytes unless an allowed field changes."""
    catalog = Catalog.model_validate(catalog.model_dump())
    if catalog.document is None:
        tree, ns = fresh(catalog)
    else:
        if catalog.document.format != "xliff":
            raise ValueError(
                "Cross-format conversion requires explicit loss acknowledgement"
            )
        raw = catalog.document.content
        before = project(raw)
        tree, ns = parse(raw)
        current = {unit.record_id: unit for unit in catalog.units}
        if len(current) != len(catalog.units) or set(current) != {
            unit.record_id for unit in before.units
        }:
            raise ValueError("Retained XLIFF message identities must match exactly")
        for node, previous in zip(
            records(tree.getroot(), ns), before.units, strict=True
        ):
            edit(node, current[previous.record_id], previous, ns)
            children = (
                forms(node, ns).values() if node.get("restype") == PLURALS else (node,)
            )
            for child in children:
                update_languages(child, ns, before, catalog)
        if (
            catalog.source_lang == before.source_lang
            and catalog.target_lang == before.target_lang
            and all(current[unit.record_id] == unit for unit in before.units)
        ):
            atomic_write(path, raw)
            return
    for file in tree.getroot().findall(ns + "file"):
        file.set("source-language", catalog.source_lang)
        if catalog.target_lang is None:
            file.attrib.pop("target-language", None)
        else:
            file.set("target-language", catalog.target_lang)
    raw = etree.tostring(
        tree, encoding=tree.docinfo.encoding or "UTF-8", xml_declaration=True
    )
    project(raw)
    atomic_write(path, raw)
