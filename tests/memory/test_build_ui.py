# this_file: tests/memory/test_build_ui.py
"""A project memory holds every finished message and never a core term."""

from pathlib import Path

import pytest

from vexy_localizzy.memory.build_ui import build_ui
from vexy_localizzy.memory.tmx_read import read_tmx

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "memory"

TS = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="de_DE" sourcelanguage="en">
<context>
    <name>Panel</name>
    <message>
        <source>Kerning class</source>
        <translation>Kerning-Klasse</translation>
    </message>
    <message>
        <source>Add kerning class</source>
        <comment>menu</comment>
        <translation>Kerning-Klasse hinzufügen</translation>
    </message>
    <message>
        <source>Later</source>
        <translation type="unfinished"></translation>
    </message>
    <message numerus="yes">
        <source>%n glyph(s)</source>
        <translation>
            <numerusform>%n Glyphe</numerusform>
            <numerusform>%n Glyphen</numerusform>
        </translation>
    </message>
</context>
</TS>
"""

CORE = """<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4">
 <header creationtool="test" creationtoolversion="1" segtype="phrase" o-tmf="tmx" adminlang="en" srclang="en" datatype="plaintext"/>
 <body>
  <tu tuid="term:kerning-class">
   <prop type="x-term-id">kerning-class</prop>
   <prop type="x-status">approved</prop>
   <tuv xml:lang="en"><seg>kerning class</seg></tuv>
   <tuv xml:lang="de"><seg>Kerning-Klasse</seg></tuv>
  </tu>
 </body>
</tmx>
"""


def test_build_ui_when_core_excluded_then_terms_dropped_and_plurals_expanded(tmp_path):
    catalog = tmp_path / "app_de.ts"
    catalog.write_text(TS, encoding="utf-8")
    core = tmp_path / "de-core.tmx"
    core.write_text(CORE, encoding="utf-8")
    out = tmp_path / "de-ui.tmx"
    result = build_ui(catalog, out, exclude_memories=[core])
    assert result["language"] == "de-DE", "the memory takes the catalog's tag"
    assert result["dropped_core_terms"] == 1, "'Kerning class' is a core term"
    assert result["kept"] == 3, "one scalar message plus two numerus forms"
    units = list(read_tmx(out))
    ids = [u.tuid for u in units]
    assert ids == [
        "Panel|Add kerning class",
        "Panel|%n glyph(s):0",
        "Panel|%n glyph(s):1",
    ], ids
    props = dict(units[0].properties)
    assert props == {"x-context": "Panel", "x-comment": "menu"}, props
    assert dict(units[2].properties)["x-numerus-form"] == "1"
    assert [s.text for s in units[2].segments] == ["%n glyph(s)", "%n Glyphen"]


def test_build_ui_when_no_exclusion_then_language_comes_from_catalog(tmp_path):
    catalog = tmp_path / "app_de.ts"
    catalog.write_text(TS, encoding="utf-8")
    result = build_ui(catalog, tmp_path / "out.tmx")
    assert result["language"] == "de-DE" and result["kept"] == 4


def _term(source: str, target: str, lang: str) -> str:
    return (
        f'<tu tuid="term:{source}"><prop type="x-status">approved</prop>'
        f'<tuv xml:lang="en"><seg>{source}</seg></tuv>'
        f'<tuv xml:lang="{lang}"><seg>{target}</seg></tuv></tu>'
    )


def _core(path: Path, *units: str) -> Path:
    head, tail = CORE.split(" <body>")
    path.write_text(head + " <body>\n" + "\n".join(units) + "\n </body>\n</tmx>\n")
    return path


KERNING_TS = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS><TS version="2.1" language="LANG" sourcelanguage="en"><context><name>M</name>
<message><source>Kerning</source><translation>K-X</translation></message>
<message><source>&amp;Kerning</source><translation>&amp;K-X</translation></message>
<message><source>Kerning %1</source><translation>K-X %1</translation></message>
<message><source>Kerning:</source><translation>K-X:</translation></message>
<message numerus="yes"><source>%n file(s)</source><translation><numerusform>%n F</numerusform></translation></message>
</context></TS>"""


def test_build_ui_when_glossary_tag_differs_then_output_takes_catalog_tag(tmp_path):
    catalog = tmp_path / "zh.ts"
    catalog.write_text(KERNING_TS.replace("LANG", "zh_TW"), encoding="utf-8")
    core = _core(tmp_path / "core.tmx", _term("Kerning", "K-core", "zh-Hant"))
    out = tmp_path / "ui.tmx"
    result = build_ui(catalog, out, exclude_memories=[core])
    assert result["language"] == "zh-TW", result
    langs = {s.language for u in read_tmx(out) for s in u.segments}
    assert langs == {"en", "zh-TW"}, "the glossary's zh-Hant tag must not leak"


def test_build_ui_when_glossary_is_other_script_then_raises_and_writes_nothing(
    tmp_path,
):
    catalog = tmp_path / "zh.ts"
    catalog.write_text(KERNING_TS.replace("LANG", "zh_TW"), encoding="utf-8")
    core = _core(tmp_path / "core.tmx", _term("Kerning", "K-core", "zh-Hans"))
    out = tmp_path / "ui.tmx"
    with pytest.raises(ValueError, match="pass --memory-lang"):
        build_ui(catalog, out, exclude_memories=[core])
    assert not out.exists()


def test_build_ui_when_term_tier_cannot_serve_source_then_message_is_kept(tmp_path):
    catalog = tmp_path / "de.ts"
    catalog.write_text(KERNING_TS.replace("LANG", "de_DE"), encoding="utf-8")
    core = _core(tmp_path / "core.tmx", _term("Kerning", "Unterschneidung", "de"))
    out = tmp_path / "ui.tmx"
    result = build_ui(catalog, out, exclude_memories=[core])
    sources = [u.segments[0].text for u in read_tmx(out)]
    assert result["dropped_core_terms"] == 1, "only the bare term is served by the tier"
    assert "Kerning" not in sources
    for kept in ("&Kerning", "Kerning %1", "Kerning:"):
        assert kept in sources, f"{kept!r} would be lost from both memories"


def test_build_ui_when_single_form_numerus_then_form_property_is_set(tmp_path):
    catalog = tmp_path / "zh.ts"
    catalog.write_text(KERNING_TS.replace("LANG", "zh_CN"), encoding="utf-8")
    out = tmp_path / "ui.tmx"
    build_ui(catalog, out)
    unit = next(u for u in read_tmx(out) if u.segments[0].text == "%n file(s)")
    assert unit.tuid == "M|%n file(s):0"
    assert dict(unit.properties)["x-numerus-form"] == "0"
