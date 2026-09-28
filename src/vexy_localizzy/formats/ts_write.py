# this_file: src/vexy_localizzy/formats/ts_write.py
"""Apply Qt translation edits without rebuilding source metadata."""

from pathlib import Path

from lxml import etree

from vexy_localizzy.catalog import Catalog
from vexy_localizzy.formats import ts_splice
from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.formats.ts_read import load_bytes


def _set_plural(trans, plural, ns):
    if plural.indexing != "index" or set(plural.forms) != {
        str(i) for i in range(len(plural.forms))
    }:
        raise ValueError(
            "Qt requires contiguous positional plural forms; supply an explicit mapping"
        )
    if plural.icu is not None or set(plural.variants) - set(plural.forms):
        raise ValueError("Qt plural representation contains unsupported fields")
    forms = trans.findall(ns + "numerusform")
    if any(child.tag != ns + "numerusform" for child in trans):
        raise ValueError("Cannot replace plural translation containing unsupported XML")
    if forms and len(forms) != len(plural.forms):
        raise ValueError("Changing retained plural count needs explicit conversion")
    for i in range(len(plural.forms)):
        key = str(i)
        form = forms[i] if forms else etree.SubElement(trans, ns + "numerusform")
        if key in plural.variants:
            if not plural.variants[key] or plural.variants[key][0] != plural.forms[key]:
                raise ValueError("First plural length variant must equal its form text")
            xml.set_variants(form, plural.variants[key], ns)
        elif xml.text(form, ns) != plural.forms[key]:
            xml.set_text(form, plural.forms[key], ns)


def _apply(message, unit, before, ns):
    if before is not None:
        editable = {"target", "plural", "variants", "state"}
        if unit.model_dump(exclude=editable) != before.model_dump(exclude=editable):
            raise ValueError(
                f"Only translation and state edits are supported for retained message {unit.key}"
            )
        if (unit.plural is None) != (before.plural is None) or (
            unit.variants is None
        ) != (before.variants is None):
            raise ValueError(
                "Changing a retained translation's shape needs explicit conversion"
            )
        if unit.plural is not None and set(unit.plural.variants) != set(
            before.plural.variants
        ):
            raise ValueError(
                "Changing a retained plural form's shape needs explicit conversion"
            )
        if unit == before:
            return False
    if unit.target is not None and (
        unit.plural is not None or unit.variants is not None
    ):
        raise ValueError(
            "Edit plural forms or length variants instead of scalar target"
        )
    trans = xml.ensure_translation(message, ns)
    if unit.plural is not None:
        if before is None or unit.plural != before.plural:
            _set_plural(trans, unit.plural, ns)
    elif unit.variants is not None:
        if before is None or unit.variants != before.variants:
            xml.set_variants(trans, unit.variants, ns)
    elif before is None or unit.target != before.target:
        if unit.target is None and before is not None:
            raise ValueError(
                "Removing a retained translation needs explicit conversion"
            )
        xml.set_text(trans, unit.target or "", ns)
    if before is None or unit.state != before.state:
        if unit.state in ("untranslated", "needs_review"):
            trans.set("type", "unfinished")
        elif unit.state == "vanished":
            trans.set("type", "vanished")
        else:
            trans.attrib.pop("type", None)
    return True


def _fresh(catalog):
    root = etree.Element("TS", version="2.1", sourcelanguage=catalog.source_lang)
    context, previous_context = None, None
    for unit in catalog.units:
        if context is None or unit.context != previous_context:
            context = etree.SubElement(root, "context")
            xml.set_text(etree.SubElement(context, "name"), unit.context, "")
            previous_context = unit.context
        message = etree.SubElement(context, "message")
        if unit.plural is not None:
            message.set("numerus", "yes")
        for location in unit.locations:
            filename, sep, line = location.rpartition(":")
            attributes = {"filename": filename if sep else location}
            if sep:
                attributes["line"] = line
            etree.SubElement(message, "location", **attributes)
        xml.set_text(etree.SubElement(message, "source"), unit.source, "")
        if unit.disambiguation is not None:
            xml.set_text(etree.SubElement(message, "comment"), unit.disambiguation, "")
        if unit.notes:
            xml.set_text(
                etree.SubElement(message, "extracomment"), "\n".join(unit.notes), ""
            )
        _apply(message, unit, None, "")
        xml.set_text(etree.SubElement(message, "extra-localizzy-key"), unit.key, "")
    return etree.ElementTree(root), ""


def dump(catalog: Catalog, path: Path, *, keep_locations: bool = True) -> None:
    """Atomically serialize; unsupported retained-document edits fail before writing.

    A retained document keeps its original bytes: only edited messages are
    re-rendered and spliced in, so a one-string edit is a one-line diff.
    """
    catalog = Catalog.model_validate(catalog.model_dump())
    if not keep_locations and any(unit.locations for unit in catalog.units):
        raise ValueError("Location removal requires an explicit lossy conversion")
    if catalog.document is None:
        tree, _ = _fresh(catalog)
        if catalog.target_lang is not None:
            tree.getroot().set("language", catalog.target_lang)
        raw = etree.tostring(
            tree, encoding="utf-8", xml_declaration=True, doctype="<!DOCTYPE TS>"
        )
        load_bytes(raw)
        atomic_write(path, raw)
        return
    if catalog.document.format != "ts":
        raise ValueError(
            "Converting another retained format to TS requires explicit loss acknowledgement"
        )
    raw = catalog.document.content
    baseline = load_bytes(raw)
    if catalog.source_lang != baseline.source_lang:
        raise ValueError("Changing the source language requires explicit conversion")
    current = {unit.record_id: unit for unit in catalog.units}
    if len(current) != len(catalog.units) or set(current) != {
        unit.record_id for unit in baseline.units
    }:
        raise ValueError("Retained TS message identities must match exactly")
    if catalog.target_lang == baseline.target_lang and all(
        current[unit.record_id] == unit for unit in baseline.units
    ):
        atomic_write(path, raw)
        return
    tree, ns = xml.parse(raw)
    elements = [message for _, message in xml.messages(tree.getroot(), ns)]
    encoding = tree.docinfo.encoding or "UTF-8"
    spans = ts_splice.message_spans(raw)
    ts_splice.check_spans(raw, spans, elements, encoding)
    replacements = {}
    style = None
    for ordinal, (message, before) in enumerate(
        zip(elements, baseline.units, strict=True)
    ):
        existing = list(message.iter())
        if not _apply(message, current[before.record_id], before, ns):
            continue
        created = [node for node in message.iter() if not _contains(existing, node)]
        style = style or ts_splice.detect_style(raw, encoding)
        span = spans[ordinal]
        rendered = ts_splice.render_message(message, style, span.indent, created)
        if rendered != raw[span.start : span.end]:
            replacements[ordinal] = rendered
    root_attrs = (
        {"language": catalog.target_lang}
        if catalog.target_lang != baseline.target_lang
        else None
    )
    if replacements or root_attrs:
        raw = ts_splice.splice(raw, replacements, root_attrs=root_attrs)
        load_bytes(raw)
    atomic_write(path, raw)


def _contains(nodes, node) -> bool:
    return any(candidate is node for candidate in nodes)
