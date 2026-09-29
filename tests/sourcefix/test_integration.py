# this_file: tests/sourcefix/test_integration.py
"""Native Qt extraction is an independent oracle for source corrections."""

import shutil
import subprocess

import pytest
from lxml import etree

from vexy_localizzy.sourcefix import apply, prepare
from vexy_localizzy.sourcefix.catalog import Catalog
from vexy_localizzy.sourcefix.files import commit


def test_apply_when_native_lupdate_reextracts_then_only_new_sources(tmp_path):
    lupdate = shutil.which("lupdate")
    if not lupdate:
        pytest.skip("Qt lupdate is not installed")
    cpp = tmp_path / "window.cpp"
    cpp.write_text("""class Window : public QObject {
 Q_OBJECT
 void f() {
   tr("Old "
      "word");
   tr("Keep");
 }
};
""")
    ui = tmp_path / "panel.ui"
    ui.write_text("""<ui version="4.0">
 <class>Panel</class>
 <widget class="QWidget" name="Panel">
  <property name="windowTitle"><string>Old &amp; title</string></property>
  <property name="toolTip"><string>Keep tip</string></property>
 </widget>
</ui>
""")
    en, mirror, fresh = [tmp_path / name for name in ("en.ts", "edit.ts", "fresh.ts")]

    def extract(out):
        subprocess.run(
            [
                lupdate,
                str(cpp),
                str(ui),
                "-source-language",
                "en_US",
                "-target-language",
                "en_US",
                "-locations",
                "relative",
                "-ts",
                str(out),
            ],
            check=True,
            capture_output=True,
        )

    extract(en)
    prepare(str(en), str(mirror), str(tmp_path))
    tree = etree.parse(str(mirror))
    for message in tree.findall(".//message"):
        if message.findtext("source").startswith("Old"):
            target = message.find("translation")
            target.text = message.findtext("source").replace("Old", "New\nsecond line")
            target.attrib.clear()
    tree.write(str(mirror), encoding="utf-8")
    result = apply(str(mirror), str(en), str(tmp_path))
    assert result["edits"] == 2
    extract(fresh)
    actual, expected = Catalog(en), Catalog(fresh)
    assert actual.index.keys() == expected.index.keys(), (
        "Native extraction must reproduce updated identities"
    )
    assert actual.locations() == expected.locations(), (
        "Line deltas must track multiline edits"
    )
    # A second correction after shifted lines must still work from the same mirror.
    tree = etree.parse(str(mirror))
    msg = next(m for m in tree.findall(".//message") if m.findtext("source") == "Keep")
    msg.find("translation").text = "Retain"
    msg.find("translation").attrib.clear()
    tree.write(str(mirror), encoding="utf-8")
    assert apply(str(mirror), str(en), str(tmp_path))["edits"] == 1
    assert 'tr("Retain")' in cpp.read_text()


def test_commit_when_second_replace_fails_then_restore_every_original(
    tmp_path, monkeypatch
):
    import vexy_localizzy.sourcefix.files as files

    paths = [tmp_path / str(i) for i in range(3)]
    for path in paths:
        path.write_bytes(b"before")
    original_replace = files.os.replace
    calls = 0

    def fail_once(src, dst):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated write failure")
        return original_replace(src, dst)

    monkeypatch.setattr(files.os, "replace", fail_once)
    with pytest.raises(OSError, match="simulated"):
        commit(dict.fromkeys(paths, b"after"), dict.fromkeys(paths, b"before"))
    assert all(p.read_bytes() == b"before" for p in paths)
    assert len(list(tmp_path.iterdir())) == 3, "Staged files must be removed"


def test_commit_when_file_changed_during_plan_then_preserve_new_work(tmp_path):
    path = tmp_path / "source"
    path.write_bytes(b"user edit")
    with pytest.raises(ValueError, match="changed while"):
        commit({path: b"ours"}, {path: b"before"})
    assert path.read_bytes() == b"user edit"


def test_extraction_when_qt_is_unavailable_then_actionable_error(tmp_path):
    from vexy_localizzy.sourcefix.extract import current_locations

    with pytest.raises(ValueError, match="Qt lupdate is required"):
        current_locations(set(), tmp_path, "localizzy-nonexistent-lupdate")
