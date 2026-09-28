# this_file: src/vexy_localizzy/formats/android_write.py
"""Apply Android translation edits without rebuilding unrelated resources."""

import re
from pathlib import Path

from lxml import etree

from vexy_localizzy.catalog import Catalog, Unit
from vexy_localizzy.formats.android_read import (
    QUANTITIES,
    parse,
    plural_items,
    project,
    records,
)
from vexy_localizzy.formats.android_text import encode, set_value
from vexy_localizzy.formats.document import atomic_write


def editable(node: etree._Element) -> None:
    if any(
        parent.get("translatable") == "false"
        for parent in (node, *node.iterancestors())
    ):
        raise ValueError("Nontranslatable Android resource cannot be edited")
    if not len(node) and (node.text or "").strip().startswith(("@", "?")):
        raise ValueError("Android resource references require explicit conversion")


def edit(node: etree._Element, unit: Unit, before: Unit) -> None:
    if unit.model_dump(exclude={"target", "plural"}) != before.model_dump(
        exclude={"target", "plural"}
    ):
        raise ValueError("Unsupported retained Android metadata/state edit")
    if unit.plural is None and before.plural is None:
        if unit.target is not None:
            editable(node)
            set_value(node, unit.target)
        return
    if unit.plural is None or before.plural is None or unit.target is not None:
        raise ValueError("Changing Android plural shape requires explicit conversion")
    if unit.plural.model_dump(exclude={"forms"}) != before.plural.model_dump(
        exclude={"forms"}
    ) or set(unit.plural.forms) != set(before.plural.forms):
        raise ValueError("Retained Android plural structure must match")
    for key, item in plural_items(node).items():
        if unit.plural.forms[key] != before.plural.forms[key]:
            editable(item)
            set_value(item, unit.plural.forms[key])


def fresh(catalog: Catalog) -> etree._ElementTree:
    root = etree.Element("resources")
    arrays, seen = {}, set()
    for unit in catalog.units:
        if unit.key in seen:
            raise ValueError("Android keys must be unique")
        seen.add(unit.key)
        array = re.fullmatch(r"(.+)\[([0-9]+)\]", unit.key)
        name = array[1] if array else unit.key
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", name) is None:
            raise ValueError("Invalid Android resource name")
        if unit.variants is not None:
            raise ValueError("Android does not support Qt length variants")
        if unit.plural is not None:
            plural = unit.plural
            if (
                array
                or plural.indexing != "cldr"
                or plural.icu
                or plural.variants
                or "other" not in plural.forms
                or set(plural.forms) - QUANTITIES
            ):
                raise ValueError(
                    "Android requires explicit CLDR quantities including other"
                )
            node = etree.SubElement(root, "plurals", name=name)
            for quantity, text in plural.forms.items():
                etree.SubElement(node, "item", quantity=quantity).text = encode(text)
        else:
            if array:
                if name not in arrays:
                    arrays[name] = etree.SubElement(root, "string-array", name=name)
                if int(array[2]) != len(arrays[name]):
                    raise ValueError(
                        "Android array indices must be contiguous and ordered"
                    )
                node = etree.SubElement(arrays[name], "item")
            else:
                node = etree.SubElement(root, "string", name=name)
            node.text = encode(unit.target if unit.target is not None else unit.source)
    return etree.ElementTree(root)


def dump(catalog: Catalog, path: str | Path) -> None:
    """Write one locale column; canonical JSON retains bilingual text and statuses."""
    catalog = Catalog.model_validate(catalog.model_dump())
    if catalog.document is None:
        tree = fresh(catalog)
    else:
        if catalog.document.format != "android":
            raise ValueError(
                "Cross-format conversion requires explicit loss acknowledgement"
            )
        raw = catalog.document.content
        before = project(raw, catalog.source_lang)
        tree = parse(raw)
        current = {unit.record_id: unit for unit in catalog.units}
        if len(current) != len(catalog.units) or set(current) != {
            unit.record_id for unit in before.units
        }:
            raise ValueError("Retained Android message identities must match exactly")
        for (_, _, node), previous in zip(
            records(tree.getroot()), before.units, strict=True
        ):
            edit(node, current[previous.record_id], previous)
        if all(current[unit.record_id] == unit for unit in before.units):
            atomic_write(path, raw)
            return
    raw = etree.tostring(
        tree, encoding=tree.docinfo.encoding or "UTF-8", xml_declaration=True
    )
    project(raw, catalog.source_lang)
    atomic_write(path, raw)
