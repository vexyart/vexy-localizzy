# this_file: tests/memory/test_build_ui.py
"""A project memory holds every finished message and never a core term."""

from pathlib import Path

from vexy_localizzy.memory.build_ui import build_ui
from vexy_localizzy.tmx import read_tmx

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
    assert result["language"] == "de", "the memory takes the core memory's tag"
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
