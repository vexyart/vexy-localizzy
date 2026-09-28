# this_file: src/vexy_localizzy/formats/ts_xml.py
"""Qt-specific XML details, including non-XML characters encoded as byte nodes."""

from io import BytesIO

from lxml import etree


def parse(raw: bytes):
    parser = etree.XMLParser(
        resolve_entities=False, load_dtd=False, no_network=True, strip_cdata=False
    )
    tree = etree.parse(BytesIO(raw), parser)
    root = tree.getroot()
    if etree.QName(root).localname != "TS":
        raise ValueError("Expected a TS root")
    dtd = tree.docinfo.internalDTD
    if dtd is not None and list(dtd.iterentities()):
        raise ValueError("Entity declarations are not supported")
    namespace = etree.QName(root).namespace
    return tree, f"{{{namespace}}}" if namespace else ""


def messages(root, ns):
    for child in root:
        if child.tag == ns + "message":
            yield "", child
        elif child.tag == ns + "context":
            context = text(child.find(ns + "name"), ns)
            for message in child.findall(ns + "message"):
                yield context, message


def text(element, ns) -> str:
    if element is None:
        return ""
    parts = [element.text or ""]
    for child in element:
        if child.tag == ns + "byte":
            value = child.get("value", "")
            point = int(value[1:], 16) if value.startswith("x") else int(value, 10)
            if 0xD800 <= point <= 0xDFFF:
                raise ValueError("Qt byte cannot encode a surrogate")
            parts.append(chr(point))
        elif isinstance(child.tag, str):
            parts.append(etree.tostring(child, encoding="unicode", with_tail=False))
        parts.append(child.tail or "")
    return "".join(parts)


def set_text(element, value: str, ns) -> None:
    if any(child.tag != ns + "byte" for child in element):
        raise ValueError("Cannot replace text containing unsupported XML children")
    for child in list(element):
        element.remove(child)
    element.text = ""
    tail = None
    for char in value:
        point = ord(char)
        if 0xD800 <= point <= 0xDFFF:
            raise ValueError("Qt text cannot encode a surrogate")
        valid = (
            point in (9, 10, 13)
            or 0x20 <= point <= 0xD7FF
            or 0xE000 <= point <= 0xFFFD
            or 0x10000 <= point <= 0x10FFFF
        )
        if not valid:
            tail = etree.SubElement(element, ns + "byte", value=f"x{point:x}")
        elif tail is None:
            element.text += char
        else:
            tail.tail = (tail.tail or "") + char


def variants(element, ns) -> list[str] | None:
    if element is None or element.get("variants") != "yes":
        return None
    return [text(child, ns) for child in element.findall(ns + "lengthvariant")]


def set_variants(element, values: list[str], ns) -> None:
    if not values:
        raise ValueError("Length variants cannot be empty")
    children = element.findall(ns + "lengthvariant")
    if any(child.tag != ns + "lengthvariant" for child in element):
        raise ValueError("Cannot replace length variants containing unsupported XML")
    if children and len(children) != len(values):
        raise ValueError(
            "Changing the number of retained length variants needs explicit conversion"
        )
    element.set("variants", "yes")
    for index, value in enumerate(values):
        child = (
            children[index]
            if children
            else etree.SubElement(element, ns + "lengthvariant")
        )
        if text(child, ns) != value:
            set_text(child, value, ns)


def translation(message, ns):
    found = message.findall(ns + "translation")
    if len(found) > 1:
        raise ValueError("A TS message cannot have multiple translation elements")
    return found[0] if found else None


def ensure_translation(message, ns):
    current = translation(message, ns)
    if current is not None:
        return current
    current = etree.Element(ns + "translation")
    position = next(
        (
            i
            for i, child in enumerate(message)
            if isinstance(child.tag, str)
            and (child.tag == ns + "userdata" or child.tag.startswith(ns + "extra-"))
        ),
        len(message),
    )
    message.insert(position, current)
    return current
