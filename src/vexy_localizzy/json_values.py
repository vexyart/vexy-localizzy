# this_file: src/vexy_localizzy/json_values.py
"""Shared standard-library JSON hooks that reject ambiguous object values."""

import json


def path_key(path: tuple[str | int, ...]) -> str:
    """Typed JSON paths distinguish object keys from array indices and literal dots."""
    return json.dumps(path, ensure_ascii=False, separators=(",", ":"))


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        key.encode("utf-8")
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def invalid_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON constant: {value}")
