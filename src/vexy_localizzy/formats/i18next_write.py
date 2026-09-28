# this_file: src/vexy_localizzy/formats/i18next_write.py
"""Write i18next resources without reserializing untouched JSON values."""

import json
from pathlib import Path

from vexy_localizzy.catalog import Catalog, Unit
from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.formats.i18next_tree import QUANTITIES, parse, records


def replacements(unit: Unit, before: Unit, nodes) -> list:
    if unit.model_dump(exclude={"target", "plural"}) != before.model_dump(
        exclude={"target", "plural"}
    ):
        raise ValueError("Unsupported retained i18next metadata/state edit")
    if unit.plural is None and before.plural is None:
        return [] if unit.target is None else [(nodes, unit.target)]
    if unit.plural is None or before.plural is None or unit.target is not None:
        raise ValueError("Unsupported i18next plural shape change")
    if unit.plural.model_dump(exclude={"forms"}) != before.plural.model_dump(
        exclude={"forms"}
    ) or set(unit.plural.forms) != set(before.plural.forms):
        raise ValueError("Retained i18next plural categories must match")
    return [
        (nodes[key], value)
        for key, value in unit.plural.forms.items()
        if value != before.plural.forms[key]
    ]


def insert(root: dict, path: list, value: str) -> None:
    if (
        not path
        or not isinstance(path[0], str)
        or any(type(key) not in (str, int) for key in path)
    ):
        raise ValueError("i18next path must start with an object key")
    current = root
    for index, key in enumerate(path):
        last = index == len(path) - 1
        child = value if last else ([] if isinstance(path[index + 1], int) else {})
        if isinstance(current, dict) and isinstance(key, str):
            if key not in current:
                current[key] = child
            elif last:
                raise ValueError("Conflicting i18next output paths")
            current = current[key]
        elif (
            isinstance(current, list) and type(key) is int and 0 <= key <= len(current)
        ):
            if key == len(current):
                current.append(child)
            elif last:
                raise ValueError("Conflicting i18next array paths")
            current = current[key]
        else:
            raise ValueError("Conflicting i18next path or noncontiguous array")


def fresh(catalog: Catalog) -> bytes:
    root = {}
    for unit in catalog.units:
        key = unit.key.removeprefix("plural:") if unit.plural is not None else unit.key
        path = json.loads(key) if key.startswith("[") else [key]
        if not isinstance(path, list) or not path:
            raise ValueError("Invalid i18next typed path")
        if unit.variants is not None:
            raise ValueError("i18next does not support Qt length variants")
        if unit.plural is None:
            insert(root, path, unit.target if unit.target is not None else unit.source)
            continue
        plural = unit.plural
        if (
            unit.target is not None
            or not isinstance(path[-1], str)
            or not path[-1]
            or plural.indexing != "cldr"
            or plural.icu
            or plural.variants
            or "other" not in plural.forms
            or set(plural.forms) - QUANTITIES
        ):
            raise ValueError("i18next requires explicit v4 plural categories")
        for category, value in plural.forms.items():
            insert(root, [*path[:-1], path[-1] + "_" + category], value)
    return (json.dumps(root, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def dump(catalog: Catalog, path: str | Path) -> None:
    from vexy_localizzy.formats.i18next import project

    catalog = Catalog.model_validate(catalog.model_dump())
    if catalog.document is None:
        raw = fresh(catalog)
    else:
        if catalog.document.format != "i18next":
            raise ValueError(
                "Cross-format conversion requires explicit loss acknowledgement"
            )
        raw = catalog.document.content
        before = project(raw, catalog.source_lang)
        current = {unit.record_id: unit for unit in catalog.units}
        if len(current) != len(catalog.units) or set(current) != {
            unit.record_id for unit in before.units
        }:
            raise ValueError("Retained i18next message identities must match exactly")
        changes = []
        for (_, _, nodes), previous in zip(
            records(parse(raw)), before.units, strict=True
        ):
            changes.extend(replacements(current[previous.record_id], previous, nodes))
        for node, value in sorted(
            changes, key=lambda entry: entry[0].start_byte, reverse=True
        ):
            raw = (
                raw[: node.start_byte]
                + json.dumps(value, ensure_ascii=False).encode("utf-8")
                + raw[node.end_byte :]
            )
    project(raw, catalog.source_lang)
    atomic_write(path, raw)
