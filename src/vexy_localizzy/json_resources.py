# this_file: src/vexy_localizzy/json_resources.py
"""Generic JSON string leaves with typed paths and no application text filters."""

import json
from collections.abc import Iterator
from decimal import Decimal

from vexy_localizzy.json_values import invalid_constant, unique_object

JSONPath = tuple[str | int, ...]


def _string_leaves(
    value: object, path: JSONPath = ()
) -> Iterator[tuple[JSONPath, str]]:
    if isinstance(value, str):
        value.encode("utf-8")
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from _string_leaves(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _string_leaves(child, (*path, index))


def string_pairs(text: str) -> list[tuple[JSONPath, str]]:
    """Parse all leaves before returning; reject duplicate keys and invalid Unicode.

    The root must be an object or array. Non-string leaves are omitted; empty
    strings, whitespace and plural-like suffixes remain literal. Decode input
    bytes explicitly before calling. No locale or UI-text policy is inferred.
    """
    data = json.loads(
        text,
        object_pairs_hook=unique_object,
        parse_float=Decimal,
        parse_constant=invalid_constant,
    )
    if not isinstance(data, (dict, list)):
        raise ValueError("JSON resource root must be an object or array")
    return list(_string_leaves(data))
