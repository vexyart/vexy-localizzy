# this_file: src/vexy_localizzy/formats/ts_read.py
"""Project retained Qt messages into editable catalog units."""

from pathlib import Path

from vexy_localizzy.catalog import (
    Catalog,
    PluralForms,
    Unit,
    derive_key,
    detect_placeholders,
)
from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.formats.document import SourceDocument


def _unit(context, message, ns, ordinal) -> Unit:
    source = xml.text(message.find(ns + "source"), ns)
    comment = message.find(ns + "comment")
    disambiguation = xml.text(comment, ns) if comment is not None else None
    trans = xml.translation(message, ns)
    status = trans.get("type") if trans is not None else "unfinished"
    state = (
        "vanished"
        if status in ("vanished", "obsolete")
        else "untranslated"
        if status == "unfinished"
        else "translated"
    )
    forms = trans.findall(ns + "numerusform") if trans is not None else []
    plural = None
    if message.get("numerus") == "yes":
        plural = PluralForms(
            indexing="index",
            forms={
                str(i): xml.text(form.find(ns + "lengthvariant"), ns)
                if xml.variants(form, ns) is not None
                else xml.text(form, ns)
                for i, form in enumerate(forms)
            },
            variants={
                str(i): xml.variants(form, ns)
                for i, form in enumerate(forms)
                if xml.variants(form, ns) is not None
            },
        )
    variants = xml.variants(trans, ns)
    key = xml.text(message.find(ns + "extra-localizzy-key"), ns) or (
        "id:" + message.get("id")
        if message.get("id")
        else derive_key(context, source, disambiguation)
    )
    return Unit(
        key=key,
        record_id=f"ts:{ordinal}",
        context=context,
        source=source,
        target=xml.text(trans, ns)
        if trans is not None and plural is None and variants is None
        else None,
        disambiguation=disambiguation,
        state=state,
        plural=plural,
        variants=variants,
        notes=[
            xml.text(child, ns)
            for child in message
            if child.tag in (ns + "extracomment", ns + "translatorcomment")
        ],
        locations=[
            f"{location.get('filename', '')}:{location.get('line')}"
            if location.get("line") is not None
            else location.get("filename", "")
            for location in message.findall(ns + "location")
        ],
        placeholders=detect_placeholders(source),
    )


def load_bytes(raw: bytes) -> Catalog:
    tree, ns = xml.parse(raw)
    root = tree.getroot()
    units, used = [], set()
    for ordinal, (context, message) in enumerate(xml.messages(root, ns)):
        unit = _unit(context, message, ns, ordinal)
        key = unit.key
        while key in used:
            key += f"~{ordinal}"
        used.add(key)
        units.append(unit.model_copy(update={"key": key}))
    return Catalog(
        source_lang=root.get("sourcelanguage", "en"),
        target_lang=root.get("language"),
        units=units,
        origin_format="ts",
        document=SourceDocument.capture(raw, "ts"),
    )


def load(path: Path) -> Catalog:
    """Read bytes once; no external file is needed for a later JSON round trip."""
    return load_bytes(Path(path).read_bytes())
