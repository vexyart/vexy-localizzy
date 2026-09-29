# this_file: src/vexy_localizzy/sourcefix/literals.py
"""Use XML parser offsets and C++ syntax trees for scoped source edits."""

import re
from pathlib import Path
from xml.parsers import expat
from xml.sax.saxutils import escape

from vexy_localizzy.sourcefix.cpp import cpp_literals, encode_cpp
from vexy_localizzy.sourcefix.literal import Literal

CPP = {".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx", ".mm", ".c"}


def ui_literals(raw: bytes) -> list[Literal]:
    parser = expat.ParserCreate()
    found = []
    current = None
    tag_end = re.compile(rb"""<string(?:\s+[^\s=/>]+\s*=\s*(?:"[^"]*"|'[^']*'))*\s*>""")

    def start(name: str, attrs: dict) -> None:
        nonlocal current
        if current is not None:
            raise ValueError("Nested XML in UI string is not supported")
        if name == "string" and attrs.get("notr") != "true":
            match = tag_end.match(raw, parser.CurrentByteIndex)
            if match is not None:
                current = (match.end(), [], attrs.get("comment", ""))

    def end(name: str) -> None:
        nonlocal current
        if name == "string" and current is not None:
            begin, pieces, comment = current
            finish = parser.CurrentByteIndex
            found.append(
                Literal(
                    begin,
                    finish,
                    "".join(pieces),
                    raw[:begin].count(b"\n") + 1,
                    raw[:finish].count(b"\n") + 1,
                    comment=comment,
                )
            )
            current = None

    def characters(text: str) -> None:
        if current is not None:
            current[1].append(text)

    def reject(*args) -> None:
        raise ValueError("Entity declarations are not supported in UI files")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = characters
    parser.EntityDeclHandler = reject
    parser.Parse(raw, True)
    return found


def literals(path: Path, raw: bytes) -> list[Literal]:
    if path.suffix == ".ui":
        return ui_literals(raw)
    if path.suffix in CPP:
        return cpp_literals(raw)
    raise ValueError(f"Unsupported source format (no files changed): {path}")


def replacement(path: Path, literal: Literal, new: str, raw: bytes = b"") -> bytes:
    if path.suffix == ".ui":
        return escape(new, {"\r": "&#13;"}).encode("utf-8")
    if literal.fragments:
        pieces, cursor = [], literal.start
        for i, (start, end) in enumerate(literal.fragments):
            prefix = re.match(rb"(?:u8|u|U|L)?", raw[start:end]).group().decode()
            pieces.extend(
                (raw[cursor:start], encode_cpp(new if i == 0 else "", prefix))
            )
            cursor = end
        pieces.append(raw[cursor : literal.end])
        return b"".join(pieces)
    return encode_cpp(new, literal.prefix)
