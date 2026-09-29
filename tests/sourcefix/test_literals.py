# this_file: tests/sourcefix/test_literals.py
"""C++ escapes, XML byte spans and ambiguous locations are observable contracts."""

from pathlib import Path

import pytest

from vexy_localizzy.sourcefix.cpp import cpp_literals, decode_cpp, encode_cpp
from vexy_localizzy.sourcefix.literals import (
    literals,
    replacement,
    ui_literals,
)


@pytest.mark.parametrize(
    "literal,text",
    [
        ('"café"', "café"),
        (r'"one\n\"two\"\\"', 'one\n"two"\\'),
        (r'"\101\x42\u00E9"', "ABé"),
        ('R"tag(a"b\nc)tag"', 'a"b\nc'),
        ('u8"Hi"', "Hi"),
        ('"a\\\nb"', "ab"),
    ],
)
def test_decode_cpp_when_supported_then_exact_text(literal, text):
    assert decode_cpp(literal) == text
    assert decode_cpp(encode_cpp(text).decode()) == text


def test_decode_cpp_when_unknown_escape_then_reject():
    with pytest.raises(ValueError, match="escape"):
        decode_cpp(r'"\q"')


def test_cpp_when_translation_context_equals_source_then_only_source_argument():
    raw = b'QCoreApplication::translate("Old", "Old", "Old");'
    values = cpp_literals(raw)
    assert len(values) == 1
    assert values[0].context == "Old"
    assert values[0].comment == "Old"
    assert raw[values[0].start : values[0].end] == b'"Old"'
    assert values[0].start == raw.index(b'"Old"', raw.index(b'"Old"') + 1)


def test_cpp_when_concatenated_then_one_logical_literal():
    values = cpp_literals(b'void X::f() { tr(\n "Old "\n "word"); }')
    assert len(values) == 1
    assert values[0].text == "Old word"
    assert values[0].matches(("X", "Old word", "", "", "no"), 1)


def test_cpp_when_comments_contain_text_then_ignore_comments():
    values = cpp_literals(b'// "Old"\n/* tr("Old") */\ntr("Old");')
    assert len(values) == 1
    assert values[0].first_line == 3


def test_cpp_when_concatenation_has_comments_then_preserve_them():
    raw = b'tr("Old " /* explanation */\n "word");'
    literal = cpp_literals(raw)[0]
    result = replacement(Path("a.cpp"), literal, "New word", raw)
    assert b"/* explanation */\n" in result
    assert cpp_literals(b"tr(" + result + b");")[0].text == "New word"


def test_ui_when_entities_and_notr_then_only_translatable_string():
    raw = b'<ui><class>X</class><string comment="a &gt; b">A &amp; B</string><string notr="true">A &amp; B</string></ui>'
    values = ui_literals(raw)
    assert len(values) == 1
    item = values[0]
    assert item.text == "A & B"
    assert item.comment == "a > b"
    edited = (
        raw[: item.start]
        + replacement(Path("a.ui"), item, 'C < D\r\n"E"')
        + raw[item.end :]
    )
    assert ui_literals(edited)[0].text == 'C < D\r\n"E"'


def test_ui_when_entities_declared_then_reject():
    with pytest.raises(ValueError, match="Entity"):
        ui_literals(b'<!DOCTYPE ui [<!ENTITY x "bad">]><ui><string>&x;</string></ui>')


def test_literals_when_unknown_format_then_reject():
    with pytest.raises(ValueError, match="Unsupported source format"):
        literals(Path("a.js"), b'tr("Old")')
