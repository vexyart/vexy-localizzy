# this_file: src/vexy_localizzy/xmlio.py
"""Shared streaming XML boundaries for TMX and Qt TS documents."""

from collections.abc import Iterator

from lxml import etree


def release(element: etree._Element) -> None:
    """Discard consumed units and siblings without removing parser parents."""
    element.clear(keep_tail=True)
    parent = element.getparent()
    if parent is not None:
        while element.getprevious() is not None:
            del parent[0]


def records(stream) -> Iterator[tuple[str, etree._Element, str]]:
    """Yield structural records; their elements live only until the next step."""
    events = etree.iterparse(
        stream,
        events=("start", "end"),
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
    )
    root = None
    namespace = ""
    for event, element in events:
        if root is None:
            root = element
            kind = etree.QName(root).localname
            if kind not in {"tmx", "TS"}:
                raise ValueError("Expected a TMX or TS root")
            namespace = (
                f"{{{etree.QName(root).namespace}}}"
                if etree.QName(root).namespace
                else ""
            )
            dtd = root.getroottree().docinfo.internalDTD
            if dtd is not None and list(dtd.iterentities()):
                raise ValueError("Entity declarations are not supported")
            yield "root", root, namespace
        if event != "end":
            continue
        parent = element.getparent()
        if parent is None:
            continue
        direct = parent is root
        child = parent.getparent() is root
        if kind == "tmx" and direct and element.tag == namespace + "header":
            yield "header", element, namespace
            release(element)
        elif (
            kind == "tmx"
            and child
            and parent.tag == namespace + "body"
            and element.tag == namespace + "tu"
        ):
            yield "tu", element, namespace
            release(element)
        elif (
            kind == "TS"
            and element.tag == namespace + "message"
            and (direct or (child and parent.tag == namespace + "context"))
        ):
            yield "message", element, namespace
            release(element)
        elif kind == "TS" and direct and element.tag == namespace + "context":
            release(element)
