# this_file: src/vexy_localizzy/formats/xliff_xml.py
"""XLIFF 1.2 XML boundaries and retained inline-code handling."""

from copy import deepcopy
from io import BytesIO
from xml.sax.saxutils import escape

from lxml import etree

NAMESPACE = "urn:oasis:names:tc:xliff:document:1.2"
PLURALS = "x-gettext-plurals"


def read_tree(raw: bytes) -> etree._ElementTree:
    parser = etree.XMLParser(
        resolve_entities=False, load_dtd=False, no_network=True, strip_cdata=False
    )
    tree = etree.parse(BytesIO(raw), parser)
    if tree.docinfo.internalDTD is not None and list(
        tree.docinfo.internalDTD.iterentities()
    ):
        raise ValueError("Entity declarations are not supported")
    return tree


def parse(raw: bytes) -> tuple[etree._ElementTree, str]:
    tree = read_tree(raw)
    root = tree.getroot()
    name = etree.QName(root)
    if (
        name.localname != "xliff"
        or root.get("version") != "1.2"
        or name.namespace not in (None, NAMESPACE)
    ):
        raise ValueError("Expected XLIFF 1.2 document")
    if tree.docinfo.internalDTD is not None and list(
        tree.docinfo.internalDTD.iterentities()
    ):
        raise ValueError("Entity declarations are not supported")
    ns = f"{{{name.namespace}}}" if name.namespace else ""
    files = root.findall(ns + "file")
    if not files or any(file.find(ns + "body") is None for file in files):
        raise ValueError("XLIFF requires file/body elements")
    locales = {
        (file.get("source-language") or "en", file.get("target-language"))
        for file in files
    }
    if len(locales) != 1:
        raise ValueError("Split XLIFF files with different language pairs explicitly")
    return tree, ns


def records(element, ns):
    """Walk core groups only; alternative translations are metadata, not messages."""
    for child in element:
        if child.tag == ns + "trans-unit" or (
            child.tag == ns + "group" and child.get("restype") == PLURALS
        ):
            yield child
        elif child.tag in (ns + "file", ns + "body", ns + "group"):
            yield from records(child, ns)


def content(element: etree._Element) -> str:
    """Plain text stays plain; content with inline nodes uses an XML fragment."""
    if not len(element):
        return element.text or ""
    return escape(element.text or "") + "".join(
        etree.tostring(child, encoding="unicode", with_tail=False)
        + escape(child.tail or "")
        for child in element
    )


def code_shape(element):
    """Inline identity/attributes and opaque native code cannot be edited as text."""
    opaque = {"bpt", "ept", "ph", "it", "x", "bx", "ex"}
    shape = []
    for child in element:
        if not isinstance(child.tag, str):
            shape.append((str(child.tag), child.text))
            continue
        frozen_text = child.text if etree.QName(child).localname in opaque else None
        shape.append(
            (
                child.tag,
                tuple(sorted(child.attrib.items())),
                frozen_text,
                code_shape(child),
            )
        )
    return tuple(shape)


def set_content(
    element: etree._Element, value: str, reference: etree._Element | None = None
) -> None:
    reference = element if reference is None else reference
    if not len(reference):
        element.text = value
        return
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    try:
        fragment = etree.fromstring(
            ("<fragment>" + value + "</fragment>").encode(), parser
        )
    except etree.XMLSyntaxError as error:
        raise ValueError("Invalid XLIFF inline XML fragment") from error
    if code_shape(reference) != code_shape(fragment):
        raise ValueError(
            "XLIFF inline codes and segmentation identities must be preserved"
        )
    for child in list(element):
        element.remove(child)
    element.text = fragment.text
    for child in fragment:
        element.append(deepcopy(child))


def context(element, kind: str, ns) -> str | None:
    """Nearest context declaration wins, including explicitly empty declarations."""
    for ancestor in (element, *element.iterancestors()):
        for item in ancestor.findall(f"{ns}context-group/{ns}context"):
            if item.get("context-type") == kind:
                return "".join(item.itertext())
    return None


def forms(group: etree._Element, ns: str) -> dict[str, etree._Element]:
    result = {}
    for child in group.findall(ns + "trans-unit"):
        identifier = child.get("id", "")
        if "[" not in identifier or not identifier.endswith("]"):
            raise ValueError(
                "Plural form IDs must carry explicit [category] or [index]"
            )
        key = identifier.rsplit("[", 1)[1][:-1]
        if not key or key in result:
            raise ValueError("Duplicate or empty XLIFF plural form identity")
        result[key] = child
    if not result:
        raise ValueError("XLIFF plural group cannot be empty")
    return result


def update_languages(node, ns, before, after):
    """Keep explicit primary language labels consistent; leave alternatives alone."""
    attribute = "{http://www.w3.org/XML/1998/namespace}lang"
    for tag, field in (
        ("source", "source_lang"),
        ("seg-source", "source_lang"),
        ("target", "target_lang"),
    ):
        value = getattr(after, field)
        if value == getattr(before, field):
            continue
        for element in node.findall(ns + tag):
            if attribute in element.attrib:
                if value is None:
                    element.attrib.pop(attribute)
                else:
                    element.set(attribute, value)
