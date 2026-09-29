# this_file: src/vexy_localizzy/sourcefix/cpp.py
"""Published C++ syntax trees delimit strings; byte offsets keep their locations."""

import re

import tree_sitter_cpp
from tree_sitter import Language, Parser

from vexy_localizzy.sourcefix.literal import Literal

STRING_NODES = {"string_literal", "raw_string_literal", "concatenated_string"}
ESCAPES = {
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
    "\\": "\\",
    "'": "'",
    '"': '"',
    "?": "?",
}
ESCAPE = re.compile(
    r"\\(?:\r?\n|[0-7]{1,3}|x[0-9a-fA-F]+|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|.)", re.S
)
CPP_LANGUAGE = Language(tree_sitter_cpp.language())


def decode_cpp(value: str) -> str:
    """Decode a parser-delimited C++ literal; reject unknown escapes."""
    if re.match(r'^(?:u8|u|U|L)?R"', value):
        start = value.index("(")
        delimiter = value[value.index('"') + 1 : start]
        return value[start + 1 : -(len(delimiter) + 2)]
    start = value.index('"')
    body = value[start + 1 : -1]

    def decode(match: re.Match) -> str:
        token = match.group()[1:]
        if token in ("\n", "\r\n"):
            return ""
        if token in ESCAPES:
            return ESCAPES[token]
        if token[0] in "01234567":
            return chr(int(token, 8))
        if token[0] in "xuU":
            return chr(int(token[1:], 16))
        raise ValueError(f"Unsupported C++ escape: {match.group()}")

    return ESCAPE.sub(decode, body)


def encode_cpp(value: str, prefix: str = "") -> bytes:
    escapes = {
        value: "\\" + key for key, value in ESCAPES.items() if key not in {"'", "?"}
    }
    parts = [
        escapes.get(char, f"\\{ord(char):03o}" if ord(char) < 32 else char)
        for char in value
    ]
    return (prefix + '"' + "".join(parts) + '"').encode("utf-8")


def _text(node, raw: bytes) -> str:
    if node.type == "concatenated_string":
        return "".join(
            _text(child, raw)
            for child in node.named_children
            if child.type != "comment"
        )
    if node.type not in STRING_NODES or node.has_error:
        raise ValueError("Unsupported C++ string expression")
    return decode_cpp(raw[node.start_byte : node.end_byte].decode("utf-8"))


def _call_details(
    node, raw: bytes
) -> tuple[tuple[int, ...], str | None, str | None] | None:
    parent = node.parent
    if (
        parent is None
        or parent.type != "argument_list"
        or parent.parent.type != "call_expression"
    ):
        return (), None, None
    call = parent.parent
    func = call.child_by_field_name("function")
    name = raw[func.start_byte : func.end_byte].decode("utf-8").split("::")[-1]
    args = [child for child in parent.named_children if child.type != "comment"]
    explicit = name in {
        "translate",
        "QT_TRANSLATE_NOOP",
        "QT_TRANSLATE_NOOP3",
        "QT_TRANSLATE_N_NOOP",
        "QT_TRANSLATE_N_NOOP3",
        "QT_TRANSLATE_NOOP_UTF8",
    }
    implicit = name in {"tr", "trUtf8", "QT_TR_NOOP", "QT_TR_N_NOOP", "QT_TR_NOOP_UTF8"}
    index = 1 if explicit else 0
    if not (explicit or implicit):
        return (), None, None
    if len(args) <= index or args[index] != node:
        return None
    context = _text(args[0], raw) if explicit else None
    comment = ""
    if len(args) > index + 1 and args[index + 1].type in STRING_NODES:
        comment = _text(args[index + 1], raw)
    return (raw.count(b"\n", 0, call.start_byte) + 1,), context, comment


def cpp_literals(raw: bytes) -> list[Literal]:
    parser = Parser(CPP_LANGUAGE)
    tree = parser.parse(raw)
    pending = [tree.root_node]
    found = []
    while pending:
        node = pending.pop()
        if node.type not in STRING_NODES:
            pending.extend(reversed(node.named_children))
            continue
        try:
            details = _call_details(node, raw)
            if details is None:
                continue
            anchors, context, comment = details
            prefix = (
                re.match(rb"(?:u8|u|U|L)?", raw[node.start_byte : node.end_byte])
                .group()
                .decode()
            )
            # Byte offsets avoid the 0.26 Point accessor heap-corruption bug
            # on CPython 3.12/macOS (py-tree-sitter issue 487).
            fragments = (
                tuple(
                    (child.start_byte, child.end_byte)
                    for child in node.named_children
                    if child.type in STRING_NODES
                )
                if node.type == "concatenated_string"
                else ()
            )
            found.append(
                Literal(
                    node.start_byte,
                    node.end_byte,
                    _text(node, raw),
                    raw.count(b"\n", 0, node.start_byte) + 1,
                    raw.count(b"\n", 0, node.end_byte) + 1,
                    anchors,
                    prefix,
                    context,
                    comment,
                    fragments,
                )
            )
        except (ValueError, UnicodeError):
            continue  # A requested unsupported literal later fails exact matching.
    return found
