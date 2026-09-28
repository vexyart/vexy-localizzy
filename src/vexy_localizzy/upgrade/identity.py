# this_file: src/vexy_localizzy/upgrade/identity.py
"""Message identity for TS upgrade, computed from XML rather than ``Unit.key``.

``Unit.key`` is a truncated slug with collision suffixes, so it cannot pair
messages across two files. The identity here is ``message/@id`` when present,
otherwise (context, source, comment). Locations never take part.
"""

from dataclasses import dataclass
from typing import Literal

from vexy_localizzy.formats import ts_xml as xml

Kind = Literal["finished", "unfinished", "vanished", "obsolete", "missing"]


@dataclass(frozen=True)
class MessageRef:
    ordinal: int  # document order, same as ts_splice spans
    context: str
    source: str  # ts_xml.text(<source>), byte refs decoded
    comment: str  # "" when absent
    msg_id: str | None  # message/@id
    numerus: bool
    kind: Kind
    has_text: bool  # any non-empty translation/numerusform/lengthvariant
    element: object  # lxml element inside the parsed tree

    @property
    def active(self) -> bool:
        """Upgrade tiers apply only to non-empty, non-obsolete messages."""
        return bool(self.source) and self.kind not in ("vanished", "obsolete")


def _kind(translation) -> Kind:
    if translation is None:
        return "missing"
    status = translation.get("type")
    if status in ("unfinished", "vanished", "obsolete"):
        return status
    return "finished"


def has_text(translation, ns: str) -> bool:
    """True when any translation slot carries text or a Qt byte reference."""
    if translation is None:
        return False
    if "".join(translation.itertext()).strip():
        return True
    return translation.find(".//" + ns + "byte") is not None


def is_filled(translation, ns: str) -> bool:
    """True when every ``numerusform`` and ``lengthvariant`` slot carries text or
    a Qt byte reference; a plural with one empty form is not filled."""
    if translation is None:
        return False
    for form in translation.findall(ns + "numerusform") or [translation]:
        for slot in form.findall(ns + "lengthvariant") or [form]:
            if not has_text(slot, ns):
                return False
    return True


def refs_from_tree(root, ns: str) -> list[MessageRef]:
    refs = []
    for ordinal, (context, message) in enumerate(xml.messages(root, ns)):
        comment = message.find(ns + "comment")
        translation = xml.translation(message, ns)
        refs.append(
            MessageRef(
                ordinal=ordinal,
                context=context,
                source=xml.text(message.find(ns + "source"), ns),
                comment=xml.text(comment, ns) if comment is not None else "",
                msg_id=message.get("id") or None,
                numerus=message.get("numerus") == "yes",
                kind=_kind(translation),
                has_text=has_text(translation, ns),
                element=message,
            )
        )
    return refs


def message_refs(raw: bytes) -> list[MessageRef]:
    """Parse TS bytes and describe every message in document order."""
    tree, ns = xml.parse(raw)
    return refs_from_tree(tree.getroot(), ns)


def identity(ref: MessageRef) -> tuple:
    return (
        ("id", ref.msg_id)
        if ref.msg_id
        else ("key", ref.context, ref.source, ref.comment)
    )


def key_identity(ref: MessageRef) -> tuple:
    """The (context, source, comment) key, used when an id has no counterpart."""
    return ("key", ref.context, ref.source, ref.comment)
