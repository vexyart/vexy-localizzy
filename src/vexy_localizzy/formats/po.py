# this_file: src/vexy_localizzy/formats/po.py
"""Preserve gettext catalogs and apply explicit translation/status edits."""

from pathlib import Path

import polib

from vexy_localizzy.catalog import Catalog, Unit
from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.formats.po_plural import validate
from vexy_localizzy.formats.po_records import parse, project, serialize


def load(path: Path, *, source_lang: str | None = None) -> Catalog:
    """Source locale uses X-Source-Language or gettext's conventional English default."""
    return project(Path(path).read_bytes(), source_lang)


def _set_target(entry: polib.POEntry, unit: Unit) -> None:
    if unit.variants is not None:
        raise ValueError("PO cannot represent Qt length variants")
    if unit.plural is None:
        if unit.target is None:
            raise ValueError(
                "PO target must be a string; use empty text for untranslated"
            )
        entry.msgstr = unit.target
        return
    plural = unit.plural
    if plural.indexing != "index" or set(plural.forms) != {
        str(i) for i in range(len(plural.forms))
    }:
        raise ValueError("PO requires explicit contiguous plural indices")
    if plural.variants or plural.icu or unit.target is not None:
        raise ValueError("PO plural representation has unsupported fields")
    if not unit.source_plural:
        raise ValueError("PO requires an explicit plural source")
    entry.msgstr_plural = {int(i): value for i, value in plural.forms.items()}


def _set_state(entry: polib.POEntry, unit: Unit) -> None:
    entry.obsolete = int(unit.state == "vanished")
    fuzzy = unit.state == "needs_review" or (
        unit.state == "untranslated"
        and (entry.msgstr or any(entry.msgstr_plural.values()))
    )
    entry.flags = [flag for flag in entry.flags if flag != "fuzzy"]
    if fuzzy:
        entry.flags.insert(0, "fuzzy")


def _edit(entry: polib.POEntry, unit: Unit, before: Unit) -> bool:
    editable = {"target", "plural", "state"}
    if unit.model_dump(exclude=editable) != before.model_dump(exclude=editable):
        raise ValueError(f"Unsupported retained PO metadata edit: {unit.key}")
    if (unit.plural is None) != (before.plural is None):
        raise ValueError("Changing PO plural shape requires explicit conversion")
    if unit.plural is not None and set(unit.plural.forms) != set(before.plural.forms):
        raise ValueError("Changing retained plural indices requires a matching rule")
    if unit.target != before.target or unit.plural != before.plural:
        _set_target(entry, unit)
    if unit.state != before.state:
        _set_state(entry, unit)
    return unit != before


def _fresh(catalog: Catalog, plural_forms: str | None) -> polib.POFile:
    if any(unit.plural is not None for unit in catalog.units) and not plural_forms:
        raise ValueError("A fresh plural PO requires an explicit Plural-Forms header")
    parsed = polib.POFile(encoding="utf-8", wrapwidth=0)
    parsed.metadata = {
        "Content-Type": "text/plain; charset=UTF-8",
        "X-Source-Language": catalog.source_lang,
    }
    if catalog.target_lang is not None:
        parsed.metadata["Language"] = catalog.target_lang
    if plural_forms:
        parsed.metadata["Plural-Forms"] = plural_forms
    for unit in catalog.units:
        entry = polib.POEntry(
            msgid=unit.source,
            msgid_plural=unit.source_plural or "",
            msgctxt=unit.context or None,
            tcomment="\n".join(unit.notes),
        )
        for location in unit.locations:
            file, separator, line = location.rpartition(":")
            entry.occurrences.append((file, line) if separator else (location, ""))
        _set_target(
            entry,
            unit.model_copy(update={"target": ""})
            if unit.target is None and unit.plural is None
            else unit,
        )
        _set_state(entry, unit)
        parsed.append(entry)
    return parsed


def dump(catalog: Catalog, path: Path, *, plural_forms: str | None = None) -> None:
    """Unchanged catalogs retain exact bytes; edited output is parsed before replace."""
    catalog = Catalog.model_validate(catalog.model_dump())
    if catalog.document is None:
        parsed = _fresh(catalog, plural_forms)
    else:
        if catalog.document.format != "po":
            raise ValueError(
                "Cross-format conversion requires explicit loss acknowledgement"
            )
        raw = catalog.document.content
        baseline = project(raw)
        parsed = parse(raw)
        current = {unit.record_id: unit for unit in catalog.units}
        if len(current) != len(catalog.units) or set(current) != {
            unit.record_id for unit in baseline.units
        }:
            raise ValueError("Retained PO message identities must match exactly")
        changed = (
            catalog.target_lang != baseline.target_lang or plural_forms is not None
        )
        if (
            changed
            and any(unit.plural is not None for unit in catalog.units)
            and not plural_forms
        ):
            raise ValueError(
                "Retargeting plural PO requires an explicit Plural-Forms rule"
            )
        if catalog.source_lang != baseline.source_lang:
            parsed.metadata["X-Source-Language"] = catalog.source_lang
            changed = True
        for entry, before in zip(parsed, baseline.units, strict=True):
            changed = _edit(entry, current[before.record_id], before) or changed
        if not changed:
            atomic_write(path, raw)
            return
    if catalog.target_lang is not None:
        parsed.metadata["Language"] = catalog.target_lang
    else:
        parsed.metadata.pop("Language", None)
    if plural_forms is not None:
        parsed.metadata["Plural-Forms"] = plural_forms
    validate(parsed)
    atomic_write(path, serialize(parsed))
