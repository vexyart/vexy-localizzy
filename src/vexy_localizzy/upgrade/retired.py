# this_file: src/vexy_localizzy/upgrade/retired.py
"""Write the APPROVED messages that the upgrade did not port.

lupdate writes locations relative to the previous message (``line="+23"``) and
omits repeated filenames. Dropping messages breaks that chain, so RETIRED
rewrites every location to an absolute line with an explicit filename first.
"""

import copy
from collections.abc import Sequence

from lxml import etree

from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.formats.ts_read import load_bytes


def resolve_locations(root, ns: str) -> None:
    """Make every ``<location>`` absolute, following Qt's TS reader.

    The reader keeps one filename for the whole document and a line counter per
    file. A message starts with the document's current filename. A location
    without a filename uses the message's current filename. A named location
    becomes the message's current filename, and the document's too when it is
    the message's first location. ``+N``/``-N`` adds to that file's counter and
    stores the sum; an absolute line leaves the counter unchanged.
    """
    current_file = ""
    counters: dict[str, int] = {}
    for _, message in xml.messages(root, ns):
        message_file = current_file
        for index, location in enumerate(message.findall(ns + "location")):
            filename = location.get("filename")
            if not filename:
                filename = message_file
            else:
                if index == 0:
                    current_file = filename
                message_file = filename
            line = location.get("line")
            if line is not None and line[:1] in ("+", "-"):
                try:
                    delta = int(line)
                except ValueError:
                    delta = None
                if delta is not None:
                    counters[filename] = counters.get(filename, 0) + delta
                    location.set("line", str(counters[filename]))
            _set_location(location, filename)


def _set_location(location, filename: str) -> None:
    """Write filename first, then line, then any other attributes (Qt's order)."""
    attrs = dict(location.attrib)
    attrs.pop("filename", None)
    line = attrs.pop("line", None)
    location.attrib.clear()
    if filename:
        location.set("filename", filename)
    if line is not None:
        location.set("line", line)
    for name, value in attrs.items():
        location.set(name, value)


_STRUCTURAL_KIDS = {"numerusform", "lengthvariant"}


def _containers(message, ns: str) -> list:
    containers = [message]
    for trans in message.findall(ns + "translation"):
        kids = [etree.QName(k).localname for k in trans if isinstance(k.tag, str)]
        if kids and set(kids) <= _STRUCTURAL_KIDS:
            containers.append(trans)
            for form in trans:
                names = {
                    etree.QName(k).localname for k in form if isinstance(k.tag, str)
                }
                if names and names <= _STRUCTURAL_KIDS:
                    containers.append(form)
    return containers


def _layout(root, ns: str, unit: str = "    ") -> None:
    """Indent structure only; leaf text and byte-ref tails are never touched."""

    def place(node, depth: int, kids) -> None:
        if not kids:
            return
        node.text = "\n" + unit * (depth + 1)
        for kid in kids:
            kid.tail = "\n" + unit * (depth + 1)
        kids[-1].tail = "\n" + unit * depth

    place(root, 0, list(root))
    root.tail = None
    for context in root:
        place(context, 1, list(context))
        for message in context.findall(ns + "message"):
            for depth_node in _containers(message, ns):
                depth = sum(1 for _ in depth_node.iterancestors())
                place(depth_node, depth, list(depth_node))


def build_retired(approved_raw: bytes, ordinals: Sequence[int]) -> bytes:
    """A valid TS holding the given APPROVED messages, grouped by context.

    Root attributes come from APPROVED. Each message keeps its translation type,
    so finished retired translations can still be harvested into a memory.
    """
    tree, ns = xml.parse(approved_raw)
    source_root = tree.getroot()
    resolve_locations(source_root, ns)
    wanted = set(ordinals)
    root = etree.Element(
        source_root.tag, attrib=dict(source_root.attrib), nsmap=source_root.nsmap
    )
    contexts: dict[str, object] = {}
    for ordinal, (context, message) in enumerate(xml.messages(source_root, ns)):
        if ordinal not in wanted:
            continue
        holder = contexts.get(context)
        if holder is None:
            holder = etree.SubElement(root, ns + "context")
            xml.set_text(etree.SubElement(holder, ns + "name"), context, ns)
            contexts[context] = holder
        holder.append(copy.deepcopy(message))
    _layout(root, ns)
    raw = etree.tostring(
        root, encoding="utf-8", xml_declaration=True, doctype="<!DOCTYPE TS>"
    )
    raw = raw.replace(
        b"<?xml version='1.0' encoding='utf-8'?>",
        b'<?xml version="1.0" encoding="utf-8"?>',
        1,
    )
    raw += b"\n"
    catalog = load_bytes(raw)
    if len(catalog.units) != len(wanted):
        raise ValueError("Retired TS lost messages while writing")
    return raw
