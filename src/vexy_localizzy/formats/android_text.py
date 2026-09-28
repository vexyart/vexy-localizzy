# this_file: src/vexy_localizzy/formats/android_text.py
"""Android text semantics and styled XML, checked against AAPT2 compilation."""

from copy import deepcopy
from dataclasses import dataclass

from lxml import etree

from vexy_localizzy.formats.xliff_xml import content, set_content

SPACE = " \t\n\r\f\v"
XLIFF_G = "{urn:oasis:names:tc:xliff:document:1.2}g"


@dataclass
class TextState:
    quoted: bool = False
    space: bool = False

    def feed(self, text: str) -> list[tuple[str, bool]]:
        output = []
        index = 0
        while index < len(text):
            char = text[index]
            index += 1
            if char in SPACE and not self.quoted:
                if not self.space:
                    output.append((" ", False))
                self.space = True
                continue
            self.space = False
            if char == "\\":
                if index == len(text):
                    raise ValueError("Incomplete Android escape")
                char = text[index]
                index += 1
                if char == "u":
                    digits = text[index : index + 4]
                    if len(digits) != 4 or any(
                        c not in "0123456789abcdefABCDEF" for c in digits
                    ):
                        raise ValueError("Invalid Android Unicode escape")
                    char = chr(int(digits, 16))
                    index += 4
                    if 0xD800 <= ord(char) <= 0xDFFF:
                        raise ValueError("Android escape cannot encode a surrogate")
                else:
                    char = {"n": "\n", "t": "\t"}.get(char, char)
                output.append((char, True))
            elif char == '"':
                self.quoted = not self.quoted
            elif char == "'" and not self.quoted:
                raise ValueError("Unescaped Android apostrophe")
            else:
                output.append((char, self.quoted))
        return output


def decode(text: str) -> str:
    result = TextState().feed(text)
    start, end = 0, len(result)
    while start < end and result[start] == (" ", False):
        start += 1
    while end > start and result[end - 1] == (" ", False):
        end -= 1
    return "".join(char for char, _ in result[start:end])


def encode(text: str) -> str:
    """Quote every new value so whitespace and leading reference characters stay literal."""
    escapes = {"\\": "\\\\", "\n": "\\n", "\t": "\\t", '"': '\\"', "'": "\\'"}
    value = "".join(
        escapes.get(char, f"\\u{ord(char):04x}" if ord(char) < 32 else char)
        for char in text
    )
    return '"' + value + '"'


def decoded_element(element: etree._Element) -> etree._Element:
    result = deepcopy(element)
    state = TextState()
    pieces = []

    def walk(node):
        if node.text:
            pieces.append((node, "text", state.feed(node.text)))
        for child in node:
            if isinstance(child.tag, str):
                if child.tag != XLIFF_G:
                    state.quoted = state.space = False
                walk(child)
                if child.tag != XLIFF_G:
                    state.quoted = state.space = False
            if child.tail:
                pieces.append((child, "tail", state.feed(child.tail)))

    walk(result)
    if not any(
        isinstance(node.tag, str) and node.tag != XLIFF_G
        for node in result.iterdescendants()
    ):
        # xliff:g does not create an Android styling span: trim like plain text.
        for ordered, edge in ((pieces, 0), (reversed(pieces), -1)):
            for _, _, tokens in ordered:
                while tokens and tokens[edge] == (" ", False):
                    tokens.pop(edge)
                if tokens:
                    break
    for node, field, tokens in pieces:
        setattr(node, field, "".join(char for char, _ in tokens))
    return result


def value(element: etree._Element) -> str:
    return (
        content(decoded_element(element))
        if len(element)
        else decode(element.text or "")
    )


def set_value(element: etree._Element, text: str) -> None:
    if not len(element):
        element.text = encode(text)
        return
    result = decoded_element(element)
    protected = [content(node) for node in result.iter(XLIFF_G)]
    set_content(result, text)
    if [content(node) for node in result.iter(XLIFF_G)] != protected:
        raise ValueError("Android xliff:g placeholder content must be preserved")
    for node in result.iter():
        if isinstance(node.tag, str) and node.text:
            node.text = encode(node.text)
        if node is not result and node.tail:
            node.tail = encode(node.tail)
    element.getparent().replace(element, result)
