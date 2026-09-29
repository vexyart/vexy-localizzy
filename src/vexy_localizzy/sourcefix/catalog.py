# this_file: src/vexy_localizzy/sourcefix/catalog.py
"""Exact Qt message identities, relative locations and scoped TS writes."""

from collections import defaultdict
from pathlib import Path

from lxml import etree

from vexy_localizzy.formats import ts_splice, ts_xml

Key = tuple[str, str, str, str, str]


def key(context: str, message: etree._Element) -> Key:
    """Keep disambiguation, IDs and numerus separate from identical wording."""
    return (
        context,
        ts_xml.text(message.find("source"), ""),
        ts_xml.text(message.find("comment"), ""),
        message.get("id", ""),
        message.get("numerus", "no"),
    )


def active(message: etree._Element) -> bool:
    target = message.find("translation")
    return target is None or target.get("type") not in {"obsolete", "vanished"}


def signature(element: etree._Element) -> bytes:
    return etree.tostring(element, with_tail=False)


class Catalog:
    """Retain original bytes and render only messages whose XML changed."""

    def __init__(self, path: Path, raw: bytes | None = None):
        self.path = path.resolve()
        self.raw = self.path.read_bytes() if raw is None else raw
        self.tree, ns = ts_xml.parse(self.raw)
        if ns:
            raise ValueError(f"Namespaced TS is not supported: {path}")
        self.records = list(ts_xml.messages(self.tree.getroot(), ""))
        self.spans = ts_splice.message_spans(self.raw)
        ts_splice.check_spans(
            self.raw, self.spans, [m for _, m in self.records], "utf-8"
        )
        self.before = [signature(m) for _, m in self.records]
        self.style = ts_splice.detect_style(self.raw)
        self.index = {}
        for context, message in self.records:
            if not active(message):
                continue
            identity = key(context, message)
            if identity in self.index:
                raise ValueError(f"Duplicate active message in {path}: {identity}")
            self.index[identity] = message

    def render(self) -> bytes:
        replacements = {}
        for i, (_, message) in enumerate(self.records):
            if signature(message) != self.before[i]:
                replacements[i] = ts_splice.render_message(
                    message, self.style, self.spans[i].indent
                )
        return ts_splice.splice(self.raw, replacements)

    def locations(self) -> dict[Key, list[tuple[Path, int | None]]]:
        """Resolve Qt's per-file line deltas and first-location filename inheritance."""
        current = ""
        lines = defaultdict(int)
        result = {}
        for context, message in self.records:
            filename = current
            resolved = []
            for i, location in enumerate(message.findall("location")):
                filename = location.get("filename", filename)
                if not filename:
                    raise ValueError(f"Location has no filename in {self.path}")
                if i == 0:
                    current = filename
                value = location.get("line")
                line = None
                if value is not None:
                    line = int(value)
                    if value.startswith(("+", "-")):
                        line += lines[filename]
                    lines[filename] = line
                resolved.append(((self.path.parent / filename).resolve(), line))
            result[key(context, message)] = resolved
        return result


def replace_source(
    message: etree._Element, new: str, *, mirror: bool, english: bool
) -> None:
    source = message.find("source")
    old = ts_xml.text(source, "")
    previous = message.find("oldsource")
    if previous is None:
        previous = etree.Element("oldsource")
        previous.tail = source.tail
        message.insert(message.index(source) + 1, previous)
    ts_xml.set_text(previous, old, "")
    ts_xml.set_text(source, new, "")
    target = ts_xml.ensure_translation(message, "")
    if mirror:
        ts_xml.set_text(target, new, "")
    elif english:
        # An English override of the old source would conceal the correction.
        ts_xml.set_text(target, "", "")
    target.set("type", "unfinished")


def rebase_locations(
    catalog: Catalog, shifts: dict[Path, list[tuple[int, int, int]]]
) -> None:
    """Re-encode existing relative deltas after edits change physical line counts."""
    locations = catalog.locations()
    last = defaultdict(int)
    for context, message in catalog.records:
        for node, (path, line) in zip(
            message.findall("location"), locations[key(context, message)], strict=True
        ):
            if line is None:
                continue
            updated = line
            for start, end, delta in shifts.get(path, []):
                if line > end:
                    updated += delta
                elif line > start:
                    raise ValueError(
                        f"Location inside a changed multiline literal: {path}:{line}"
                    )
            value = node.get("line")
            if value.startswith(("+", "-")):
                node.set("line", f"{updated - last[path]:+d}")
            elif updated != line:
                node.set("line", str(updated))
            last[path] = updated
