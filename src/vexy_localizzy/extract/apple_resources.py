# this_file: src/vexy_localizzy/extract/apple_resources.py
"""Read Apple resource values without imposing bundle discovery or locale policy."""

import plistlib
from collections.abc import Iterator

FORMAT_KEY = "NSStringLocalizedFormatKey"
DEVICE_KEY = "NSStringDeviceSpecificRuleType"
PLURAL_META = {"NSStringFormatSpecTypeKey", "NSStringFormatValueTypeKey"}


class _StringPairs:
    """OpenStep's dictionary factory, retaining duplicate string keys in order."""

    def __init__(self):
        self.pairs: list[tuple[str, str]] = []

    def __setitem__(self, key: str, value: object) -> None:
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError(
                "Apple .strings entries must contain string keys and values"
            )
        self.pairs.append((key, value))


def _decode(data: bytes) -> str:
    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    return data.decode(encoding)


def parse_strings_text(data: bytes) -> list[tuple[str, str]]:
    """Parse UTF-8/UTF-16 .strings with comments, escapes and repeated keys intact.

    Requires the sources extra. A dictionary wrapper enforces complete parsing of
    the brace-less resource syntax, including otherwise unconsumed trailing text.
    """
    from openstep_plist import ParseError, loads

    text = _decode(data)
    try:
        parsed = loads("{" + text + "\n}", dict_type=_StringPairs)
    except ParseError as error:
        raise ValueError("Invalid Apple .strings syntax") from error
    return parsed.pairs


def resource_items(data: bytes) -> list[tuple[str, object]]:
    """Read ordered .strings/.stringsdict pairs; retain native dictionary values.

    Binary/XML property lists use Python's native reader. Text decoding is strict:
    invalid input must not silently introduce replacement characters into memory.
    """
    if data.startswith(b"bplist"):
        obj = plistlib.loads(data)
    elif _decode(data).lstrip().startswith("<"):
        obj = plistlib.loads(data, fmt=plistlib.FMT_XML)
    else:
        return parse_strings_text(data)
    if not isinstance(obj, dict):
        raise ValueError("Apple resource property list must be a dictionary")
    return list(obj.items())


def loctable_tables(data: bytes) -> list[tuple[str, dict[str, object]]]:
    """Return ordered raw language tables, excluding LocProvenance metadata.

    Read binary/XML resource values without normalizing locale keys or assigning
    fallback languages. Consumers select tables and project values explicitly.
    """
    return [
        (name, table)
        for name, table in resource_items(data)
        if name != "LocProvenance" and isinstance(table, dict)
    ]


def flatten_value(
    key: str, value: object, *, device: str = "mac"
) -> Iterator[tuple[str, str]]:
    """Project nonempty resource text into legacy key/variable/category pairs.

    This extraction projection retains format strings and all plural categories;
    device dictionaries choose the requested device, then other. Native catalog
    editing needs the original resource, since this projection is intentionally lossy.
    """
    if isinstance(value, str):
        if value:
            yield key, value
        return
    if not isinstance(value, dict):
        return
    if DEVICE_KEY in value:
        variants = value[DEVICE_KEY]
        if isinstance(variants, dict):
            text = variants.get(device) or variants.get("other")
            if isinstance(text, str) and text:
                yield key, text
        return
    fmt = value.get(FORMAT_KEY)
    if isinstance(fmt, str) and fmt:
        yield key, fmt
    for var, spec in value.items():
        if var == FORMAT_KEY or not isinstance(spec, dict):
            continue
        for category, text in spec.items():
            if category not in PLURAL_META and isinstance(text, str) and text:
                yield f"{key}|{var}|{category}", text
