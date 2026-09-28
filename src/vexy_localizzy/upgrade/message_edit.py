# this_file: src/vexy_localizzy/upgrade/message_edit.py
"""Build a NEW ``<message>`` from a FRESH copy, following the ownership table.

FRESH owns ids, locations, source, comment and extracomment. APPROVED owns the
whole ``<translation>`` element and, when FRESH lacks them, translatorcomment,
userdata and extra-* children. Inserted children follow Qt's child order and
are returned as ``created`` so ``ts_splice.render_message`` can indent them.
"""

import copy

from lxml import etree

from vexy_localizzy.formats import ts_xml as xml

_RANK = {
    "location": 0,
    "source": 1,
    "oldsource": 2,
    "comment": 3,
    "oldcomment": 4,
    "extracomment": 5,
    "translatorcomment": 6,
    "translation": 7,
    "userdata": 8,
}
_CARRIED = ("translatorcomment", "userdata")


def local(node) -> str:
    return etree.QName(node).localname if isinstance(node.tag, str) else ""


def _rank(node) -> int | None:
    name = local(node)
    if name.startswith("extra-"):
        return 9
    return _RANK.get(name)


def insert_ordered(message, node) -> None:
    """Insert after the last child that Qt writes at or before this one."""
    wanted = _rank(node)
    position = 0
    for index, child in enumerate(message):
        rank = _rank(child)
        if rank is not None and wanted is not None and rank <= wanted:
            position = index + 1
    message.insert(position, node)


def c14n(element) -> bytes:
    return etree.tostring(element, method="c14n", exclusive=True, with_tail=False)


def set_state(trans, finished: bool | None) -> None:
    """None keeps the copied state; False marks unfinished; True clears the mark."""
    if finished is False:
        trans.set("type", "unfinished")
    elif finished is True and trans.get("type") == "unfinished":
        del trans.attrib["type"]


def fit_forms(trans, ns: str, count: int, created: list) -> None:
    """Keep the first `count` numerus forms; add empty ones for missing slots."""
    forms = trans.findall(ns + "numerusform")
    if len(forms) > count:
        closing = forms[-1].tail
        for form in forms[count:]:
            trans.remove(form)
        if count:
            forms[count - 1].tail = closing
    for _ in range(count - len(forms)):
        form = etree.SubElement(trans, ns + "numerusform")
        created.append(form)


def port(
    new,
    approved,
    ns: str,
    *,
    finished: bool | None,
    form_count: int | None,
    old: bool,
    created: list,
) -> None:
    """Copy APPROVED's translation and translator metadata into `new`."""
    source_trans = xml.translation(approved, ns)
    target_trans = xml.translation(new, ns)
    trans = (
        copy.deepcopy(source_trans)
        if source_trans is not None
        else etree.Element(ns + "translation")
    )
    if target_trans is not None:
        trans.tail = target_trans.tail
        new.replace(target_trans, trans)
    else:
        trans.tail = None
        insert_ordered(new, trans)
        created.append(trans)
    if form_count is not None and new.get("numerus") == "yes":
        fit_forms(trans, ns, form_count, created)
    set_state(trans, finished)
    for child in approved:
        name = local(child)
        if not (name in _CARRIED or name.startswith("extra-")):
            continue
        if new.find(child.tag) is not None:
            continue
        clone = copy.deepcopy(child)
        clone.tail = None
        insert_ordered(new, clone)
        created.append(clone)
    if old:
        _write_old(new, approved, ns, created)


def _write_old(new, approved, ns: str, created: list) -> None:
    """oldsource/oldcomment carry APPROVED's text when it differs from FRESH's."""
    pairs = (("source", "oldsource"), ("comment", "oldcomment"))
    for current, previous in pairs:
        before = approved.find(ns + current)
        now = new.find(ns + current)
        if before is None or not xml.text(before, ns):
            continue
        if now is not None and xml.text(now, ns) == xml.text(before, ns):
            continue
        for stale in new.findall(ns + previous):
            new.remove(stale)
        clone = copy.deepcopy(before)
        clone.tag = ns + previous
        clone.tail = None
        insert_ordered(new, clone)
        created.append(clone)


def _ensure_translation(new, ns: str, created: list):
    trans = xml.translation(new, ns)
    if trans is None:
        trans = etree.Element(ns + "translation")
        insert_ordered(new, trans)
        created.append(trans)
    return trans


def _clear_children(trans) -> None:
    for child in list(trans):
        trans.remove(child)


def write_values(
    new, ns: str, kind: str, values, *, finished: bool, created: list
) -> None:
    """Write memory or engine text: kind is scalar, forms or variants."""
    trans = _ensure_translation(new, ns, created)
    if kind == "scalar":
        if any(child.tag != ns + "byte" for child in trans) or trans.get("variants"):
            _clear_children(trans)
            trans.attrib.pop("variants", None)
        if xml.text(trans, ns) != values:
            xml.set_text(trans, values, ns)
    elif kind == "variants":
        if trans.findall(ns + "lengthvariant") and len(
            trans.findall(ns + "lengthvariant")
        ) != len(values):
            _clear_children(trans)
        if any(child.tag != ns + "lengthvariant" for child in trans):
            _clear_children(trans)
        before = list(trans.iter())
        xml.set_variants(trans, list(values), ns)
        created.extend(n for n in trans.iter() if not any(n is b for b in before))
    else:
        _write_forms(trans, ns, list(values), created)
    set_state(trans, finished)


def _write_forms(trans, ns: str, values: list[str], created: list) -> None:
    forms = trans.findall(ns + "numerusform")
    if len(forms) != len(values) or any(
        child.tag != ns + "numerusform" for child in trans
    ):
        _clear_children(trans)
        trans.text = None
        forms = []
        for _ in values:
            form = etree.SubElement(trans, ns + "numerusform")
            created.append(form)
            forms.append(form)
    for form, value in zip(forms, values, strict=True):
        if any(child.tag != ns + "byte" for child in form):
            _clear_children(form)
            form.attrib.pop("variants", None)
        if xml.text(form, ns) != value:
            xml.set_text(form, value, ns)


def write_empty(new, ns: str, form_count: int | None, created: list) -> None:
    """Pending or untranslated: an empty unfinished translation of the right shape."""
    if new.get("numerus") == "yes":
        write_values(
            new, ns, "forms", [""] * (form_count or 1), finished=False, created=created
        )
        return
    trans = xml.translation(new, ns)
    if trans is not None and trans.get("variants") == "yes":
        count = len(trans.findall(ns + "lengthvariant")) or 1
        write_values(new, ns, "variants", [""] * count, finished=False, created=created)
        return
    write_values(new, ns, "scalar", "", finished=False, created=created)
