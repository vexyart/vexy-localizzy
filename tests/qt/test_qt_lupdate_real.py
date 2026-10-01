# this_file: tests/qt/test_qt_lupdate_real.py
"""Real lupdate merges: translations survive, removed strings stay as vanished."""

from pathlib import Path

import pytest

from vexy_localizzy.external import find_tool
from vexy_localizzy.formats import ts as ts_io
from vexy_localizzy.qt import lupdate

REAL_LUPDATE = pytest.mark.skipif(
    not find_tool("lupdate").found, reason="lupdate not installed"
)
HELLO_CPP = (
    "#include <QObject>\n"
    "class Hello : public QObject {\n"
    "  Q_OBJECT\n"
    "public:\n"
    '  QString text() const { return tr("Hello"); }\n'
    '  QString more() const { return tr("%s"); }\n'
    "};\n"
)


def _project(tmp_path: Path, extra: str = "Goodbye") -> Path:
    """Minimal qmake project with "Hello" and one more translatable string."""
    (tmp_path / "hello.cpp").write_text(
        HELLO_CPP.replace("%s", extra), encoding="utf-8"
    )
    pro = tmp_path / "hello.pro"
    pro.write_text("SOURCES += hello.cpp\n", encoding="utf-8")
    return pro


@REAL_LUPDATE
def test_run_when_real_lupdate_then_existing_translation_kept(tmp_path):
    pro = _project(tmp_path)
    out = tmp_path / "i18n"
    catalogs = lupdate.run([pro], out, prefix="hello", locales=["de"])
    assert any(u.source == "Hello" for u in catalogs["en"].units), (
        "Hello must be extracted"
    )
    assert sorted(p.name for p in out.iterdir()) == ["hello_de.ts", "hello_en.ts"], (
        "prefix names the files"
    )
    de_path = out / "hello_de.ts"
    cat = ts_io.load(de_path)
    units = [
        u.model_copy(update={"target": "Hallo", "state": "translated"})
        for u in cat.units
    ]
    ts_io.dump(cat.model_copy(update={"units": units}), de_path)
    again = lupdate.run([pro], out, prefix="hello", locales=["de"])["de"]
    hello = next(u for u in again.units if u.source == "Hello")
    assert (hello.target, hello.state) == ("Hallo", "translated"), (
        f"translation lost: {hello}"
    )


@REAL_LUPDATE
def test_run_when_real_string_left_source_then_translation_kept_as_vanished(tmp_path):
    pro = _project(tmp_path, extra="Goodbye")
    out = tmp_path / "i18n"
    lupdate.run([pro], out, prefix="hello", locales=["de"])
    de_path = out / "hello_de.ts"
    cat = ts_io.load(de_path)
    units = [
        u.model_copy(update={"target": f"de:{u.source}", "state": "translated"})
        for u in cat.units
    ]
    ts_io.dump(cat.model_copy(update={"units": units}), de_path)
    _project(tmp_path, extra="Welcome")
    again = lupdate.run([pro], out, prefix="hello", locales=["de"])["de"]
    goodbye = next((u for u in again.units if u.source == "Goodbye"), None)
    assert goodbye is not None, (
        f"a finished translation must not be deleted: {again.units}"
    )
    assert (goodbye.target, goodbye.state) == ("de:Goodbye", "vanished"), (
        f"kept as vanished: {goodbye}"
    )


@REAL_LUPDATE
def test_run_when_real_empty_source_dir_then_catalogs_untouched(tmp_path):
    pro = _project(tmp_path)
    out = tmp_path / "i18n"
    lupdate.run([pro], out, prefix="hello", locales=["de"])
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    (tmp_path / "empty").mkdir()
    with pytest.raises(RuntimeError, match="no messages"):
        lupdate.run([tmp_path / "empty"], out, prefix="hello", locales=["de"])
    assert {p.name: p.read_bytes() for p in out.iterdir()} == before, (
        "an empty source must change nothing"
    )
