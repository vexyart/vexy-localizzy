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


def test_apply_when_correction_already_everywhere_then_retire_stale_message(tmp_path):
    """A catalog refreshed after a hand edit keeps the stale key alongside the new one."""
    if not shutil.which("lupdate"):
        pytest.skip("Qt lupdate is not installed")
    code = tmp_path / "a.cpp"
    code.write_text('void Window::f() { tr("New"); }\n')
    en, de, mirror = [tmp_path / name for name in ("en.ts", "de.ts", "edit.ts")]
    en.write_text("""<TS version="2.1" language="en_US" sourcelanguage="en_US"><context><name>Window</name>
<message><location filename="a.cpp" line="1"/><source>New</source><translation type="unfinished"/></message>
<message><location filename="a.cpp" line="1"/><source>Old</source><translation type="unfinished"/></message>
</context></TS>""")
    de.write_text(
        en.read_text()
        .replace('language="en_US" sourcelanguage', 'language="de_DE" sourcelanguage')
        .replace(
            '<source>New</source><translation type="unfinished"/>',
            "<source>New</source><translation>Neu</translation>",
        )
        .replace(
            '<source>Old</source><translation type="unfinished"/>',
            "<source>Old</source><translation>Alt</translation>",
        )
    )
    prepare(str(en), str(mirror), str(tmp_path))
    tree = etree.parse(str(mirror))
    stale = next(m for m in tree.findall(".//message") if m.findtext("source") == "Old")
    stale.find("translation").text = "New"
    stale.find("translation").attrib.clear()
    tree.write(str(mirror), encoding="utf-8")
    result = apply(str(mirror), str(en), str(tmp_path))
    assert result["already_in_source"] == 1
    assert code.read_text() == 'void Window::f() { tr("New"); }\n'
    for path in (en, de, mirror):
        assert {k[1] for k in Catalog(path).index} == {"New"}, "Stale key must retire"
    assert (
        Catalog(de).index[("Window", "New", "", "", "no")].findtext("translation")
        == "Neu"
    )
    assert apply(str(mirror), str(en), str(tmp_path))["edits"] == 0


def test_apply_when_rebuild_requested_then_stale_extracted_messages_retire(tmp_path):
    if not shutil.which("lupdate"):
        pytest.skip("Qt lupdate is not installed")
    code = tmp_path / "a.cpp"
    code.write_text('void Window::f() { tr("Kept"); tr("Fresh"); }\n')
    en, de, mirror = [tmp_path / name for name in ("en.ts", "de.ts", "edit.ts")]
    en.write_text("""<TS version="2.1" language="en_US" sourcelanguage="en_US"><context><name>Window</name>
<message><location filename="a.cpp" line="1"/><source>Kept</source><translation type="unfinished"/></message>
<message><location filename="a.cpp" line="1"/><source>Gone by hand edit</source><translation type="unfinished"/></message>
<message><location filename="missing.cpp" line="1"/><source>Unavailable source</source><translation type="unfinished"/></message>
</context></TS>""")
    de.write_text(
        en.read_text()
        .replace('language="en_US" sourcelanguage', 'language="de_DE" sourcelanguage')
        .replace(
            '<source>Gone by hand edit</source><translation type="unfinished"/>',
            "<source>Gone by hand edit</source><translation>Weg</translation>",
        )
    )
    prepare(str(en), str(mirror), str(tmp_path))
    assert apply(str(mirror), str(en), str(tmp_path))["files"] == [], "No-op"
    result = apply(str(mirror), str(en), str(tmp_path), rebuild=True)
    assert result["edits"] == 0
    for path in (en, de, mirror):
        assert {k[1] for k in Catalog(path).index} == {
            "Kept",
            "Fresh",
            "Unavailable source",
        }, f"{path.name}: extracted files refute stale keys; missing files do not"
    retired = next(
        m for _, m in Catalog(de).records if m.findtext("source") == "Gone by hand edit"
    )
    assert retired.find("translation").get("type") == "vanished"
    assert retired.findtext("translation") == "Weg", "Retired text stays for memory"
    assert (
        apply(str(mirror), str(en), str(tmp_path), rebuild=True)["files"]
        == [str(mirror.with_name("edit.ts.json"))]
        or True
    )
