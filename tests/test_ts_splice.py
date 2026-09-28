# this_file: tests/test_ts_splice.py
"""Editing a retained TS catalog rewrites only the edited messages' bytes."""

import difflib

import pytest
from lxml import etree

from vexy_localizzy.formats import ts, ts_splice
from vexy_localizzy.formats import ts_xml as xml

EXPANDED = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="de_DE" sourcelanguage="en">
    <context>
        <name>Panel</name>
        <message>
            <location filename="../panel.ui" line="+14"></location>
            <source>Open</source>
            <translation>Offnen</translation>
        </message>
        <message>
            <location line="+23"></location>
            <source>Close</source>
            <translation>Schliessen</translation>
        </message>
        <message>
            <location line="+5"></location>
            <source>Save</source>
            <translation type="unfinished"></translation>
        </message>
    </context>
</TS>
"""

LUPDATE = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="pl_PL">
<context>
    <name>Window</name>
    <message>
        <location filename="../window.cpp" line="12"/>
        <source>Open</source>
        <translation>Otworz</translation>
    </message>
    <message numerus="yes">
        <location filename="../window.cpp" line="20"/>
        <source>%n files</source>
        <translation>
            <numerusform>%n plik</numerusform>
            <numerusform>%n pliki</numerusform>
            <numerusform>%n plikow</numerusform>
        </translation>
    </message>
    <message>
        <location filename="../window.cpp" line="31"/>
        <source>Close</source>
        <translation>Zamknij</translation>
    </message>
</context>
</TS>
"""

CRLF_APOS = (
    b"<?xml version='1.0' encoding='utf-8'?>\n"
    b'<TS version="2.1" language="fr_FR">\n'
    b"<context>\n"
    b"    <name>Dialog</name>\n"
    b"    <message>\n"
    b"        <source>Don&apos;t save</source>\n"
    b"        <translation>Ne pas enregistrer</translation>\n"
    b"    </message>\n"
    b"    <message>\n"
    b"        <source>It&apos;s done</source>\n"
    b"        <translation>C&apos;est fait</translation>\n"
    b"    </message>\n"
    b"</context>\n"
    b"</TS>\n"
).replace(b"\n", b"\r\n")

TRICKY = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="de">
<!-- <message><source>commented out</source></message> -->
<context>
    <name>C</name>
    <message>
        <source><![CDATA[a <b> & </message> c]]></source>
        <translation>alt</translation>
    </message>
    <message>
        <source>plain</source>
        <translation>einfach</translation>
    </message>
</context>
</TS>
"""


def load(tmp_path, raw):
    path = tmp_path / "in.ts"
    path.write_bytes(raw)
    return ts.load(path)


def edit(catalog, index, **updates):
    units = list(catalog.units)
    units[index] = units[index].model_copy(update=updates)
    return catalog.model_copy(update={"units": units})


def dump(tmp_path, catalog):
    out = tmp_path / "out.ts"
    ts.dump(catalog, out)
    return out.read_bytes()


def changed_lines(before: bytes, after: bytes) -> tuple[list[int], list[bytes]]:
    """1-based line numbers of `before` that changed, plus the new lines."""
    old, new = before.splitlines(keepends=True), after.splitlines(keepends=True)
    matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    touched, added = [], []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            touched += range(i1 + 1, i2 + 1)
            added += new[j1:j2]
    return touched, added


def message_lines(raw: bytes, ordinal: int) -> range:
    span = ts_splice.message_spans(raw)[ordinal]
    first = raw.count(b"\n", 0, span.start) + 1
    return range(first, raw.count(b"\n", 0, span.end) + 2)


@pytest.mark.parametrize("raw", [EXPANDED, LUPDATE], ids=["expanded", "lupdate"])
def test_splice_when_one_translation_edited_then_only_that_line_changes(tmp_path, raw):
    catalog = load(tmp_path, raw)
    index = 2 if raw is LUPDATE else 1
    out = dump(tmp_path, edit(catalog, index, target=catalog.units[index].target + "!"))
    touched, added = changed_lines(raw, out)
    assert len(touched) == 1, f"Expected a one-line diff, got lines {touched}"
    assert touched[0] in message_lines(raw, index)
    assert added[0].strip().endswith(b"!</translation>")
    assert ts.load(tmp_path / "out.ts").units[index].target.endswith("!")


def test_splice_when_expanded_style_then_empty_tags_stay_expanded(tmp_path):
    catalog = load(tmp_path, EXPANDED)
    out = dump(tmp_path, edit(catalog, 0, state="needs_review"))
    touched, added = changed_lines(EXPANDED, out)
    assert added == [
        b'            <translation type="unfinished">Offnen</translation>\n'
    ]
    assert b'line="+14"></location>' in out
    assert touched == [9]


def test_splice_when_lupdate_style_then_locations_stay_self_closing(tmp_path):
    catalog = load(tmp_path, LUPDATE)
    out = dump(tmp_path, edit(catalog, 0, target="Otworz plik"))
    assert out.count(b'"/>') == LUPDATE.count(b'"/>')
    assert b"></location>" not in out


def test_splice_when_numerus_form_edited_then_only_that_form_line_changes(tmp_path):
    catalog = load(tmp_path, LUPDATE)
    plural = catalog.units[1].plural
    forms = {**plural.forms, "1": "%n pliki!"}
    out = dump(
        tmp_path, edit(catalog, 1, plural=plural.model_copy(update={"forms": forms}))
    )
    touched, added = changed_lines(LUPDATE, out)
    assert added == [b"            <numerusform>%n pliki!</numerusform>\n"]
    assert len(touched) == 1
    assert ts.load(tmp_path / "out.ts").units[1].plural.forms["1"] == "%n pliki!"


def test_splice_when_crlf_and_apos_then_declaration_newlines_and_entities_survive(
    tmp_path,
):
    catalog = load(tmp_path, CRLF_APOS)
    out = dump(tmp_path, edit(catalog, 0, target="N'enregistrez pas"))
    assert out.startswith(b"<?xml version='1.0' encoding='utf-8'?>\r\n")
    assert b"\n" not in out.replace(b"\r\n", b"")
    assert b"<translation>N&apos;enregistrez pas</translation>\r\n" in out
    touched, _ = changed_lines(CRLF_APOS, out)
    assert touched == [7]
    assert ts.load(tmp_path / "out.ts").units[0].target == "N'enregistrez pas"


def test_splice_when_cdata_and_commented_message_then_spans_skip_them(tmp_path):
    spans = ts_splice.message_spans(TRICKY)
    assert len(spans) == 2
    assert TRICKY[spans[0].start : spans[0].end].count(b"</message>") == 2
    catalog = load(tmp_path, TRICKY)
    assert catalog.units[0].source == "a <b> & </message> c"
    out = dump(tmp_path, edit(catalog, 0, target="neu"))
    touched, added = changed_lines(TRICKY, out)
    assert added == [b"        <translation>neu</translation>\n"]
    assert b"<![CDATA[a <b> & </message> c]]>" in out
    assert b"<!-- <message><source>commented out</source></message> -->" in out


def test_splice_when_tokenizer_disagrees_then_refuse_to_write(tmp_path, monkeypatch):
    catalog = edit(load(tmp_path, EXPANDED), 0, target="x")
    real = ts_splice.message_spans

    def shifted(raw):
        spans = real(raw)
        first = spans[0]
        return [
            ts_splice.MessageSpan(0, first.start + 1, first.end, first.indent),
            *spans[1:],
        ]

    monkeypatch.setattr(ts_splice, "message_spans", shifted)
    out = tmp_path / "out.ts"
    out.write_bytes(b"existing")
    with pytest.raises(ValueError, match="disagrees with XML parser"):
        ts.dump(catalog, out)
    assert out.read_bytes() == b"existing"


def test_check_spans_when_span_covers_wrong_message_then_name_its_ordinal():
    tree, ns = xml.parse(EXPANDED)
    elements = [message for _, message in xml.messages(tree.getroot(), ns)]
    spans = ts_splice.message_spans(EXPANDED)
    swapped = [spans[0], spans[2], spans[1]]
    with pytest.raises(ValueError, match="at message 1"):
        ts_splice.check_spans(EXPANDED, swapped, elements, "utf-8")
    with pytest.raises(ValueError, match="at message 2"):
        ts_splice.check_spans(EXPANDED, spans[:2], elements, "utf-8")


@pytest.mark.parametrize(
    ("target_lang", "expected"),
    [
        ("de_AT", b'<TS version="2.1" language="de_AT" sourcelanguage="en">'),
        (None, b'<TS version="2.1" sourcelanguage="en">'),
    ],
)
def test_splice_when_target_language_changes_then_only_root_tag_changes(
    tmp_path, target_lang, expected
):
    catalog = load(tmp_path, EXPANDED).model_copy(update={"target_lang": target_lang})
    out = dump(tmp_path, catalog)
    touched, added = changed_lines(EXPANDED, out)
    assert touched == [3]
    assert added == [expected + b"\n"]


def test_splice_when_root_attrs_given_then_add_escape_and_keep_other_bytes():
    raw = b"<?xml version='1.0'?><!DOCTYPE TS [<!ATTLIST TS x CDATA 'y'>]><?pi?><!-- <TS> --><TS  version='2.1' >\n<message><source>a</source></message></TS>"
    out = ts_splice.splice(raw, {}, root_attrs={"language": 'a"&<b', "version": "3"})
    assert (
        out.replace(
            b"<TS  version='3' language=\"a&quot;&amp;&lt;b\" >",
            b"<TS  version='2.1' >",
        )
        == raw
    )
    assert etree.fromstring(out).get("language") == 'a"&<b'


def test_splice_when_insert_after_then_bytes_follow_that_message():
    raw = b"<TS>\n  <message><source>a</source></message>\n</TS>"
    out = ts_splice.splice(
        raw, {}, insert_after={0: b"\n  <message><source>b</source></message>"}
    )
    assert out == (
        b"<TS>\n  <message><source>a</source></message>\n"
        b"  <message><source>b</source></message>\n</TS>"
    )
    with pytest.raises(ValueError, match="ordinal 5"):
        ts_splice.splice(raw, {5: b""})


def test_splice_when_translation_missing_then_new_element_is_indented(tmp_path):
    raw = EXPANDED.replace(
        b'            <translation type="unfinished"></translation>\n', b""
    )
    catalog = load(tmp_path, raw)
    out = dump(tmp_path, edit(catalog, 2, target="Sichern", state="translated"))
    assert (
        b"            <source>Save</source>\n            <translation>Sichern</translation>\n        </message>"
        in out
    )
    touched, _ = changed_lines(raw, out)
    assert set(touched) <= set(message_lines(raw, 2))


def test_render_when_message_unedited_then_bytes_equal_original_span():
    for raw in (EXPANDED, LUPDATE, CRLF_APOS, TRICKY):
        tree, ns = xml.parse(raw)
        style = ts_splice.detect_style(raw, tree.docinfo.encoding)
        messages = [message for _, message in xml.messages(tree.getroot(), ns)]
        for span, message in zip(ts_splice.message_spans(raw), messages, strict=True):
            assert (
                ts_splice.render_message(message, style, span.indent)
                == raw[span.start : span.end]
            )


def test_detect_style_when_expanded_catalog_then_report_its_conventions():
    style = ts_splice.detect_style(EXPANDED)
    assert style.declaration == b'<?xml version="1.0" encoding="utf-8"?>'
    assert {"location", "translation"} <= style.expanded_empty
    assert style.indent_unit == b"    "
    assert style.newline == b"\n"
    lupdate = ts_splice.detect_style(LUPDATE)
    assert "location" not in lupdate.expanded_empty
    crlf = ts_splice.detect_style(CRLF_APOS)
    assert crlf.newline == b"\r\n" and crlf.escape_apos


@pytest.mark.parametrize("value", ["\x04", "\x04 ", "\n\x04", "a\x04b"])
def test_splice_when_target_is_byte_encoded_then_no_indent_enters_text(tmp_path, value):
    catalog = load(tmp_path, EXPANDED)
    dump(tmp_path, edit(catalog, 1, target=value))
    assert ts.load(tmp_path / "out.ts").units[1].target == value


def test_splice_when_plural_form_is_byte_encoded_then_no_indent_enters_text(tmp_path):
    catalog = load(tmp_path, LUPDATE)
    plural = catalog.units[1].plural
    forms = {**plural.forms, "1": "\x04"}
    dump(tmp_path, edit(catalog, 1, plural=plural.model_copy(update={"forms": forms})))
    assert ts.load(tmp_path / "out.ts").units[1].plural.forms["1"] == "\x04"


def test_dump_when_unchanged_then_raw_bytes_written_without_span_check(
    tmp_path, monkeypatch
):
    catalog = load(tmp_path, EXPANDED)
    monkeypatch.setattr(ts_splice, "message_spans", lambda raw: [])
    assert dump(tmp_path, catalog) == EXPANDED
