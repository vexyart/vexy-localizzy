# this_file: src/vexy_localizzy/formats/ts_template.py
"""Explicitly prepare a new target locale while retaining its source XML tree."""

from lxml import etree

from vexy_localizzy.catalog import Catalog
from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.formats.ts_read import load_bytes
from vexy_localizzy.locales import canonical_locale


def _empty_variants(element, count, ns):
    existing = element.findall(ns + "lengthvariant")
    if existing:
        if any(child.tag != ns + "lengthvariant" for child in element):
            raise ValueError("Cannot reset length variants containing unsupported XML")
        for child in existing:
            xml.set_text(child, "", ns)
    else:
        xml.set_text(element, "", ns)
    element.set("variants", "yes")
    for _ in range(count - len(existing)):
        etree.SubElement(element, ns + "lengthvariant")


def _empty_plural(trans, count, ns):
    forms = trans.findall(ns + "numerusform")
    if any(child.tag != ns + "numerusform" for child in trans):
        raise ValueError("Cannot reset plurals containing unsupported XML")
    # Every target form receives every available UI length alternative, even
    # when the source's plural rule has a different number of positions.
    variants = max(
        (len(form.findall(ns + "lengthvariant")) for form in forms), default=0
    )
    while len(forms) < count:
        forms.append(etree.SubElement(trans, ns + "numerusform"))
    # Validate/reset all original forms before dropping positions: unsupported
    # extension XML must not disappear merely because the new locale has fewer.
    for form in forms:
        if variants:
            _empty_variants(form, variants, ns)
        else:
            xml.set_text(form, "", ns)
    for form in forms[count:]:
        trans.remove(form)
    trans.text = None


def prepare_translation(raw: bytes, *, target_lang: str, plural_count: int) -> Catalog:
    """Clear eligible targets and explicitly change native plural shape for a new locale.

    Empty-source and obsolete/vanished messages are preserved. Source/context,
    comments, locations, IDs and extension metadata outside active translations
    remain in the retained document. This is explicit preparation, not merging
    existing reviewed translations; callers restore verified reviewed targets
    separately. Native Qt plural_count must be provided by the application.
    """
    if type(plural_count) is not int or not 1 <= plural_count <= 6:
        raise ValueError("Qt plural_count must be an integer from one through six")
    target_lang = canonical_locale(target_lang)
    baseline = load_bytes(raw)
    tree, ns = xml.parse(raw)
    for (_, message), unit in zip(
        xml.messages(tree.getroot(), ns), baseline.units, strict=True
    ):
        if unit.state == "vanished" or not unit.source.strip():
            continue
        trans = xml.ensure_translation(message, ns)
        if unit.plural is not None:
            _empty_plural(trans, plural_count, ns)
        elif unit.variants is not None:
            if not unit.variants:
                raise ValueError("Cannot prepare an empty length-variant shape")
            _empty_variants(trans, len(unit.variants), ns)
        else:
            xml.set_text(trans, "", ns)
        trans.set("type", "unfinished")
    tree.getroot().set("language", target_lang)
    return load_bytes(etree.tostring(tree, encoding="utf-8", xml_declaration=True))


def prepare_review(raw: bytes, *, plural_count: int) -> Catalog:
    """Append missing Qt plural positions without clearing existing review targets.

    Complete messages and excluded messages remain untouched. Extra positions are
    rejected rather than discarded. The returned snapshot permits subsequent
    retained-document edits to fill the added positions.
    """
    if type(plural_count) is not int or not 1 <= plural_count <= 6:
        raise ValueError("Qt plural_count must be an integer from one through six")
    baseline = load_bytes(raw)
    tree, ns = xml.parse(raw)
    changed = False
    for (_, message), unit in zip(
        xml.messages(tree.getroot(), ns), baseline.units, strict=True
    ):
        if unit.plural is None or unit.state == "vanished" or not unit.source.strip():
            continue
        count = len(unit.plural.forms)
        if count > plural_count:
            raise ValueError(
                "Review preparation cannot remove existing plural positions"
            )
        if count == plural_count:
            continue
        trans = xml.ensure_translation(message, ns)
        if (
            any(child.tag != ns + "numerusform" for child in trans)
            or (trans.text or "").strip()
        ):
            raise ValueError(
                "Cannot prepare plurals containing unsupported XML or text"
            )
        for _ in range(plural_count - count):
            etree.SubElement(trans, ns + "numerusform")
        trans.set("type", "unfinished")
        changed = True
    return (
        load_bytes(etree.tostring(tree, encoding="utf-8", xml_declaration=True))
        if changed
        else baseline
    )
