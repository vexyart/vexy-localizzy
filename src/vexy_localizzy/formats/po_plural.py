# this_file: src/vexy_localizzy/formats/po_plural.py
"""Validate explicit gettext plural declarations without guessing category order."""

import gettext
import re

import polib


def plural_count(header: str) -> int:
    """Check declaration syntax using Python's gettext expression parser."""
    match = re.fullmatch(
        r"\s*nplurals\s*=\s*([1-9][0-9]*)\s*;\s*plural\s*=\s*([^;]+);?\s*", header
    )
    if match is None:
        raise ValueError("Invalid Plural-Forms declaration")
    gettext.c2py(match[2].strip())
    return int(match[1])


def complete(entry: polib.POEntry, count: int | None) -> bool:
    """Require all declared indices and nonempty text for a translated plural."""
    forms = entry.msgstr_plural
    return (
        count is not None
        and len(forms) == count
        and all(i in forms for i in range(count))
        and all(forms.values())
    )


def validate(parsed: polib.POFile) -> None:
    """Reject new output with incomplete active plural shapes before replacing files."""
    entries = [entry for entry in parsed if entry.msgid_plural and not entry.obsolete]
    header = parsed.metadata.get("Plural-Forms", "")
    if not entries and not header:
        return
    count = plural_count(header)
    for entry in entries:
        forms = entry.msgstr_plural
        if len(forms) != count or any(i not in forms for i in range(count)):
            raise ValueError("PO plural indices must match the declared nplurals count")
