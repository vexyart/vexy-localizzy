# this_file: tests/sourcefix/test_refresh.py
"""After apply, native extraction and the editing mirror share a fresh baseline."""

import shutil

import pytest
from lxml import etree

from vexy_localizzy.sourcefix import apply, prepare
from vexy_localizzy.sourcefix.catalog import Catalog


def test_rebuild_when_text_has_significant_line_spaces_then_encode_without_loss(
    tmp_path,
):
    from vexy_localizzy.sourcefix.refresh_merge import protect_line_spaces

    raw = b"<TS><context><name>X</name><message><source>A  \nB</source><translation>C \nD</translation></message></context></TS>"
    before = Catalog(tmp_path / "en.ts", raw)
    result = protect_line_spaces(before)
    after = Catalog(tmp_path / "en.ts", result)
    assert b"A&#32;&#32;\nB" in result
    assert before.index.keys() == after.index.keys()
    assert next(iter(after.index.values())).findtext("translation") == "C \nD"


def test_apply_when_rebuilt_then_new_strings_drafts_and_baseline_survive(tmp_path):
    if not shutil.which("lupdate"):
        pytest.skip("Qt lupdate is not installed")
    code = tmp_path / "a.cpp"
    code.write_text(
        'void Window::f() { tr("Old"); tr("Draft"); tr("Newly extracted"); }\n'
    )
    en, de, mirror = [tmp_path / name for name in ("en.ts", "de.ts", "edit.ts")]
    en.write_text("""<TS version="2.1" language="en_US" sourcelanguage="en_US"><context><name>Window</name>
<message><location filename="a.cpp" line="1"/><source>Old</source><translation type="unfinished"/></message>
<message><location filename="a.cpp" line="1"/><source>Draft</source><translation type="unfinished"/></message>
<message><location filename="missing.cpp" line="1"/><source>Unavailable source</source><translation type="unfinished"/></message>
</context></TS>""")
    de.write_text(
        en.read_text()
        .replace('language="en_US" sourcelanguage', 'language="de_DE" sourcelanguage')
        .replace(
            '<source>Old</source><translation type="unfinished"/>',
            "<source>Old</source><translation>Alt</translation>",
        )
    )
    prepare(str(en), str(mirror), str(tmp_path))
    tree = etree.parse(str(mirror))
    messages = tree.findall(".//message")
    messages[0].find("translation").text = "New"
    messages[0].find("translation").attrib.clear()
    messages[1].find("translation").text = "Unapproved draft"
    tree.write(str(mirror), encoding="utf-8")
    apply(str(mirror), str(en), str(tmp_path))
    for path in (en, de, mirror):
        catalog = Catalog(path)
        sources = {k[1] for k in catalog.index}
        assert sources == {"New", "Draft", "Newly extracted", "Unavailable source"}, (
            "Every TS must be rebuilt by Qt"
        )
    english_editing = Catalog(mirror)
    assert (
        english_editing.index[("Window", "New", "", "", "no")].findtext("translation")
        == "New"
    )
    assert (
        english_editing.index[("Window", "Draft", "", "", "no")].findtext("translation")
        == "Unapproved draft"
    )
    german = Catalog(de).index[("Window", "New", "", "", "no")]
    assert german.findtext("translation") == "Alt"
    assert german.find("translation").get("type") == "unfinished"
    assert apply(str(mirror), str(en), str(tmp_path))["edits"] == 0
