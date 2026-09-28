# this_file: src/vexy_localizzy/extract/source_resources.py
"""Keyed resource projection and explicit source/target pairing for extraction."""

import re
from pathlib import Path

from vexy_localizzy.extract.legacy_pairs import Pair


def _resource_table(path: Path, kind: str) -> tuple[dict[str, str], dict[str, str]]:
    if kind == "json":
        from vexy_localizzy.extract.json_resources import string_pairs
        from vexy_localizzy.json_values import path_key

        return {
            path_key(key): value
            for key, value in string_pairs(path.read_text(encoding="utf-8-sig"))
        }, {}
    if kind in {"mozilla-properties", "dtd"}:
        from vexy_localizzy.extract.mozilla_resources import parse_mozilla

        return dict(
            parse_mozilla(
                path.read_text(encoding="utf-8-sig"), kind.removeprefix("mozilla-")
            )
        ), {}
    if kind == "properties":
        from vexy_localizzy.extract.properties_resources import parse_properties

        return dict(parse_properties(path.read_text(encoding="utf-8-sig"))), {}
    if kind == "ftl":
        from vexy_localizzy.extract.fluent_resources import parse_ftl

        table = dict(parse_ftl(path.read_text(encoding="utf-8-sig")))
        return table, {key: re.sub(r"(\[[^\]]*\])+$", "", key) for key in table}
    from vexy_localizzy.extract.apple_resources import resource_items

    return _apple_table(resource_items(path.read_bytes()))


def _apple_table(items) -> tuple[dict[str, str], dict[str, str]]:
    from vexy_localizzy.extract.apple_resources import flatten_value

    table, fallbacks = {}, {}
    for key, value in items:
        for variant, text in flatten_value(key, value):
            if variant not in table:
                table[variant] = text
                if variant != key:
                    fallbacks[variant] = variant.rsplit("|", 1)[0] + "|other"
    return table, fallbacks


def _resource_rows(path: Path, source: Path, kind: str) -> tuple[list[Pair], list[str]]:
    reference, _ = _resource_table(source, kind)
    target, fallbacks = _resource_table(path, kind)
    return _paired_rows(reference, target, fallbacks)


def _paired_rows(reference, target, fallbacks) -> tuple[list[Pair], list[str]]:
    rows, unmatched = [], []
    for key, text in target.items():
        original = reference.get(key) or reference.get(fallbacks.get(key, key))
        if original:
            rows.append((original, text, key, None))
        else:
            unmatched.append(key)
    return rows, unmatched


def loctable_rows(
    path: Path, source_key: str, target_key: str
) -> tuple[list[Pair], list[str]]:
    """Select exact raw locale keys; do not guess Base/English or region aliases."""
    from vexy_localizzy.extract.apple_resources import loctable_tables

    tables = dict(loctable_tables(path.read_bytes()))
    for key in (source_key, target_key):
        if key not in tables:
            raise ValueError(f"Missing loctable language table: {key}")
    source, _ = _apple_table(tables[source_key].items())
    target, fallbacks = _apple_table(tables[target_key].items())
    return _paired_rows(source, target, fallbacks)
