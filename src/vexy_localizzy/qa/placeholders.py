# this_file: src/vexy_localizzy/qa/placeholders.py
"""Exact Qt tokens and Python's own brace-format parser; never evaluate text."""

import re
from collections import Counter
from string import Formatter

QT_ARGUMENT = re.compile(r"%L?(?:[0-9]{1,2}|n)")


def arguments(text: str, style: str) -> Counter:
    """Retain multiplicity and formatting details while allowing named reordering."""
    if style == "qt":
        return Counter(QT_ARGUMENT.findall(text))
    if style == "python_brace":
        return Counter(brace_fields(text))
    raise ValueError(f"Unsupported in-process placeholder style: {style}")


def brace_fields(text: str) -> tuple:
    """Normalize implicit indices in evaluation order, including nested width fields."""
    automatic, manual = 0, False

    def parse(value, depth):
        nonlocal automatic, manual
        fields = []
        for literal, name, spec, conversion in Formatter().parse(value):
            if depth and literal:
                fields.append(("literal", literal))
            if name is None:
                continue
            if depth > 1:
                raise ValueError("Python format specifications cannot nest this deeply")
            root = name.split(".")[0].split("[")[0]
            if root == "":
                if manual:
                    raise ValueError("Cannot mix automatic and manual format indices")
                name, automatic = str(automatic) + name, automatic + 1
            elif root.isdecimal():
                if automatic:
                    raise ValueError("Cannot mix automatic and manual format indices")
                manual = True
            fields.append((name, parse(spec, depth + 1), conversion))
        return tuple(fields)

    return parse(text, 0)


def accelerators(text: str) -> tuple[int, int]:
    """Count Qt ampersand mnemonics and invalid markers; && is a literal ampersand."""
    marks = [m[1:] for m in re.findall(r"&&|&.?", text, re.DOTALL) if m != "&&"]
    return sum(bool(m) and m.isalnum() for m in marks), sum(
        not m or not m.isalnum() for m in marks
    )
