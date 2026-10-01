# this_file: tests/memory/test_lookup.py
"""Exact TS/QPH source lookup in language-prefixed memories, with provenance."""

import json
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement

import pytest
from lxml import etree

from vexy_localizzy.memory import lookup as tool

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def _memory(path, rows):
    root = Element("tmx", version="1.4")
    SubElement(root, "header", srclang="en")
    body = SubElement(root, "body")
    for source, target, tag in rows:
        unit = SubElement(body, "tu")
        for language, text in (("en", source), (tag, target)):
            SubElement(SubElement(unit, "tuv", {XML_LANG: language}), "seg").text = text
    ElementTree(root).write(path, encoding="utf-8")


@pytest.fixture
def inputs(tmp_path):
    ts = tmp_path / "input.ts"
    ts.write_text(
        """<TS sourcelanguage="en"><context><name>Test</name>
<message><source> Open </source><translation>DO NOT USE</translation></message>
<message><source>Open</source></message>
<message><source>open</source><translation type="obsolete">ignored</translation></message>
<message><source>Missing</source></message>
<message><source>A<byte value="x9"/>B</source></message>
</context></TS>"""
    )
    qph = tmp_path / "input.qph"
    qph.write_text(
        "<QPH><phrase><source> QPH only </source><target>IGNORED</target></phrase></QPH>"
    )
    memories = tmp_path / "tmx"
    memories.mkdir()
    _memory(
        memories / "de-a.tmx",
        [
            (" Open ", " Öffnen ", "de-DE"),
            ("Open", "Öffnen", "de"),
            ("open", "klein", "de"),
            ("A\tB", "Tab", "de"),
            ("QPH only", "Phrase", "de"),
            ("Open", "Wrong language", "fr"),
        ],
    )
    _memory(
        memories / "de-b.tmx", [("Open", "Öffnen", "de"), ("Open", "Aufmachen", "de")]
    )
    _memory(memories / "es-a.tmx", [("Open", "Abrir", "es-419")])
    return ts, qph, memories


def test_lookup_when_exact_then_all_candidates_and_provenance(inputs):
    ts, qph, directory = inputs
    sources, language = tool.input_sources(ts, qph)
    result = tool.lookup(sources, language, ["de", "es", "fr"], directory)
    assert result["Open"] == {
        "de": {"Öffnen": ["de-a.tmx", "de-b.tmx"], "Aufmachen": ["de-b.tmx"]},
        "es": {"Abrir": ["es-a.tmx"]},
        "fr": {},
    }, result["Open"]
    assert result["open"]["de"] == {"klein": ["de-a.tmx"]}, "matching is case-sensitive"
    assert result["Missing"] == {"de": {}, "es": {}, "fr": {}}
    assert result["A\tB"]["de"] == {"Tab": ["de-a.tmx"]}, "byte nodes are decoded"
    assert result["QPH only"]["de"] == {"Phrase": ["de-a.tmx"]}
    assert "DO NOT USE" not in result and "IGNORED" not in result


def test_run_when_defaults_then_json_and_report_beside_catalog(inputs):
    ts, qph, directory = inputs
    summary = tool.run(str(ts), str(directory), "de,es", qph=str(qph))
    result = json.loads(Path(summary["json"]).read_text())
    assert list(result) == ["A\tB", "Open", "open", "QPH only"], (
        "case-insensitive order"
    )
    assert result["open"]["es"] == {}, "a matched source keeps its empty languages"
    html = Path(summary["report"]).read_text()
    assert 'id="data"' in html and '"Missing"' not in html, "unmatched sources left out"
    assert summary["matched"] == 4 and summary["sources"] == 5, summary
    assert Path(summary["json"]).name == "input.ts.lookup.json"


def test_run_when_outputs_disabled_or_colliding(inputs, tmp_path):
    ts, _, directory = inputs
    summary = tool.run(
        str(ts), str(directory), "de", out=str(tmp_path / "x.json"), report=""
    )
    assert (
        summary["report"] is None and not (tmp_path / "input.ts.lookup.html").exists()
    )
    for bad in (str(ts), str(directory / "de-a.tmx")):
        with pytest.raises(ValueError, match="overwrite"):
            tool.run(str(ts), str(directory), "de", out=bad)
    with pytest.raises(ValueError, match="language"):
        tool.run(str(ts), str(directory), "../de")
    with pytest.raises(ValueError, match="TMX directory"):
        tool.run(str(ts), str(tmp_path / "none"), "de")


def test_plain_when_markers_then_only_accelerators_dropped():
    cases = {
        "&Align": "Align",
        " E&xit ": "Exit",
        "Copy && Paste": "Copy && Paste",
        "Copy & Paste": "Copy & Paste",
        "A&nbsp;B": "A&nbsp;B",
        "&#169; &File": "&#169; File",
        "&&&Open": "&&Open",
        "Trailing &": "Trailing &",
        "": "",
    }
    for text, expected in cases.items():
        assert tool.plain(text) == expected, f"plain({text!r})"


def test_lookup_when_markers_differ_then_sources_and_targets_collapse(inputs):
    ts, _, directory = inputs
    ts.write_text(
        '<TS sourcelanguage="en"><context><name>T</name>'
        "<message><source>&amp;Open</source></message>"
        "<message><source>Open</source></message></context></TS>"
    )
    (directory / "de-c.tmx").write_text(
        '<tmx version="1.4"><header srclang="en"/><body><tu>'
        '<tuv xml:lang="en"><seg>O&amp;pen</seg></tuv>'
        '<tuv xml:lang="de"><seg>&amp;Öffnen</seg></tuv></tu></body></tmx>',
        encoding="utf-8",
    )
    sources, language = tool.input_sources(ts, None)
    assert sources == ["Open"], "marked and unmarked sources collapse"
    result = tool.lookup(sources, language, ["de"], directory)
    assert result["Open"]["de"] == {
        "Öffnen": ["de-a.tmx", "de-b.tmx", "de-c.tmx"],
        "Aufmachen": ["de-b.tmx"],
    }, result


def test_run_when_memory_malformed_then_existing_output_kept(inputs):
    ts, _, directory = inputs
    output = ts.with_name("input.ts.lookup.json")
    output.write_text("keep this")
    (directory / "de-bad.tmx").write_text("<broken>")
    with pytest.raises((ValueError, etree.XMLSyntaxError)):
        tool.run(str(ts), str(directory), "de")
    assert output.read_text() == "keep this", "a failed run replaces nothing"


def test_render_report_when_hostile_text_then_embedded_as_data():
    payload = '</script><img src=x onerror="alert(1)">'
    html = tool.render_report({payload: {"de": {payload: ["file.tmx"]}}}, ["de"])
    assert payload not in html and "\\u003c/script>" in html, "payload must be escaped"


def test_run_when_catalog_empty_and_languages_repeat(inputs):
    ts, _, directory = inputs
    ts.write_text('<TS sourcelanguage="en"/>')
    summary = tool.run(str(ts), str(directory), ("de", "es", "de"), report="")
    assert summary["languages"] == ["de", "es"], "duplicates collapse, order kept"
    assert json.loads(Path(summary["json"]).read_text()) == {}


def test_lookup_when_internal_text_differs_then_no_match(inputs):
    _, _, directory = inputs
    result = tool.lookup(["OPEN", "A B", "Ope\u0301n"], "en", ["de"], directory)
    assert all(not row["de"] for row in result.values()), "only outer space is trimmed"


def test_input_sources_when_qph_missing_or_has_entities_then_error(inputs):
    ts, qph, _ = inputs
    with pytest.raises(OSError):
        tool.input_sources(ts, ts.with_suffix(".missing.qph"))
    qph.write_text(
        '<!DOCTYPE QPH [<!ENTITY name "Open">]>'
        "<QPH><phrase><source>&name;</source></phrase></QPH>"
    )
    with pytest.raises(ValueError, match="entity"):
        tool.input_sources(ts, qph)
