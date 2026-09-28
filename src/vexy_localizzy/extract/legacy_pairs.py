# this_file: src/vexy_localizzy/extract/legacy_pairs.py
"""Explicit compatibility projections for existing Qt/gettext TMX extractors.

These retain historical first/last plural and plain-text selection rules. Use
formats.ts, formats.po and conversion for complete native catalog preservation.
Locale normalization, source paths and output publication belong to the caller.
Adapted from MIT-licensed fl10n; see NOTICE.
"""

import xml.etree.ElementTree as ET

import polib

type Pair = tuple[str, str, str | None, str | None]
TS_SKIP_TYPES = frozenset({"unfinished", "obsolete", "vanished"})


def ts_pairs(root: ET.Element) -> list[Pair]:
    """Project finished context messages into source/target/context/plural rows.

    Preserve input order and duplicate rows. Historical Qt extraction uses the
    first and last nonempty numerusform, with the same source string for both.
    """
    result: list[Pair] = []
    for context in root.iter("context"):
        name = (context.findtext("name") or "").strip() or None
        for message in context.iter("message"):
            source = message.findtext("source") or ""
            target = message.find("translation")
            if not source or target is None or target.get("type") in TS_SKIP_TYPES:
                continue
            forms = [form.text for form in target.findall("numerusform") if form.text]
            if forms:
                result.append((source, forms[0], name, "singular"))
                if len(forms) > 1:
                    result.append((source, forms[-1], name, "plural"))
            elif target.text:
                result.append((source, target.text, name, None))
    return result


def po_pairs(catalog: polib.POFile, fuzzy: bool = False) -> list[Pair]:
    """Project gettext entries using the legacy first/last indexed plural rule.

    Obsolete, empty-source and untranslated entries are omitted. Fuzzy targets
    require opt-in; context and scalar text are passed through without stripping.
    """
    result: list[Pair] = []
    for entry in catalog:
        if entry.obsolete or not entry.msgid or (entry.fuzzy and not fuzzy):
            continue
        context = entry.msgctxt or None
        if entry.msgid_plural:
            forms = [entry.msgstr_plural[key] for key in sorted(entry.msgstr_plural)]
            if forms and forms[0]:
                result.append((entry.msgid, forms[0], context, "singular"))
            if forms and forms[-1]:
                result.append((entry.msgid_plural, forms[-1], context, "plural"))
        elif entry.msgstr:
            result.append((entry.msgid, entry.msgstr, context, None))
    return result
