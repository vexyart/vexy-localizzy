# this_file: src/vexy_localizzy/qa/formats.py
"""Choose the placeholder QA styles a catalog's own format actually uses.

Qt catalogs use ``%1``/``%n``. gettext declares the syntax per entry with
``c-format``, ``python-brace-format`` or ``qt-format`` flags; an unflagged
entry gets no placeholder check, as in ``msgfmt --check-format``. i18next uses
``{{name}}``. Android strings are Java/C format strings when they contain a
conversion. XLIFF and TMX carry no declaration, so each unit uses the style
detected in its own source. Used by ``translate_file``.
"""

import re

from vexy_localizzy.catalog import Catalog, Unit
from vexy_localizzy.qa.text import TextPolicy

PO_FLAGS = {
    "c-format": "printf",
    "python-brace-format": "python_brace",
    "qt-format": "qt",
}
# A Java/C conversion; a space flag is excluded so "100% done" is plain text.
JAVA_FORMAT = re.compile(r"%(?:\d+\$)?[-#+0,]*\d*(?:\.\d+)?[sdifuxXoeEgGcb]")
DETECTED = ("qt", "python_brace", "i18next", "printf")


def _po_styles(catalog: Catalog) -> dict[str, tuple[str, ...]]:
    from vexy_localizzy.formats.po_records import parse

    entries = list(parse(catalog.document.content)) if catalog.document else []
    styles = {}
    for unit in catalog.units:
        kind, _, index = (unit.record_id or "").partition(":")
        if kind != "po" or not index.isdigit() or int(index) >= len(entries):
            continue
        flags = entries[int(index)].flags
        if found := tuple(PO_FLAGS[f] for f in flags if f in PO_FLAGS):
            styles[unit.key] = found
    return styles


I18NEXT = re.compile(r"\{\{.*?\}\}", re.DOTALL)
BRACE = re.compile(r"\{\w+\}")
ICU_ARGUMENT = re.compile(r"\{\s*\w+\s*,")


def _detected(unit: Unit) -> tuple[str, ...]:
    """Styles seen in this unit's source. ``detect_placeholders`` reports
    ``{name}`` as ICU, so braces are classified here: ``{{x}}`` is i18next,
    and ``{x}`` without ICU ``{x, plural, ...}`` syntax is Python brace."""
    source = unit.source
    found = {p.style for p in unit.placeholders} - {"icu", "i18next", "python_brace"}
    if I18NEXT.search(source):
        found.add("i18next")
    elif BRACE.search(source) and not ICU_ARGUMENT.search(source):
        found.add("python_brace")
    if "printf" in found and "%(" in source:
        found.discard("printf")  # named %(x)s is not C printf; msgfmt would reject it
    return tuple(style for style in DETECTED if style in found)


def format_policy(catalog: Catalog) -> TextPolicy:
    """The TextPolicy for ``catalog``; Qt (the default) for TS and native JSON."""
    fmt = catalog.origin_format
    if fmt == "po":
        return TextPolicy(placeholder_styles=(), unit_styles=_po_styles(catalog))
    if fmt == "i18next":
        return TextPolicy(placeholder_styles=("i18next",))
    if fmt == "android":
        styles = {
            u.key: ("printf",) for u in catalog.units if JAVA_FORMAT.search(u.source)
        }
        return TextPolicy(placeholder_styles=(), unit_styles=styles)
    if fmt in ("xliff", "tmx"):
        styles = {u.key: s for u in catalog.units if (s := _detected(u))}
        return TextPolicy(placeholder_styles=(), unit_styles=styles)
    return TextPolicy()
