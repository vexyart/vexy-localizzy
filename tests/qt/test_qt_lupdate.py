# this_file: tests/qt/test_qt_lupdate.py
"""lupdate wrapper with a fake tool: command line, safe replacement, languages."""

import subprocess
from pathlib import Path

import pytest

from vexy_localizzy.formats import ts as ts_io
from vexy_localizzy.qt import lupdate, process

FAKE_TOOL = "/fake/bin/lupdate"
ONE_MESSAGE_TS = (
    '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n'
    '<TS version="2.1" sourcelanguage="en">\n<context><name>Hello</name>\n'
    '<message><source>Hello</source><translation type="unfinished"></translation></message>\n'
    "</context>\n</TS>\n"
)
EMPTY_TS = '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n<TS version="2.1" sourcelanguage="en"/>\n'
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


def _fake(
    monkeypatch, body: str = ONE_MESSAGE_TS, code: int = 0, stderr: str = ""
) -> list[dict]:
    """Record lupdate calls; write ``body`` at every -ts path (unless it fails)."""
    calls: list[dict] = []

    def fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, **kwargs})
        for i, arg in enumerate(cmd):
            if arg == "-ts" and code == 0:
                Path(cmd[i + 1]).write_text(body, encoding="utf-8")
        return subprocess.CompletedProcess(cmd, code, stdout="", stderr=stderr)

    monkeypatch.setattr(lupdate, "require_tool", lambda name: FAKE_TOOL)
    monkeypatch.setattr(process.subprocess, "run", fake_run)
    return calls


@pytest.fixture
def fake_lupdate(monkeypatch):
    return _fake(monkeypatch)


def _ts_args(cmd: list[str]) -> list[Path]:
    return [Path(cmd[i + 1]) for i, a in enumerate(cmd) if a == "-ts"]


def test_run_when_fake_tool_then_command_is_built(tmp_path, fake_lupdate):
    pro = _project(tmp_path)
    out = tmp_path / "i18n"
    catalogs = lupdate.run([pro], out, prefix="hello", locales=["de", "en"])
    call = fake_lupdate[0]
    cmd = call["cmd"]
    assert cmd[:5] == [
        FAKE_TOOL,
        "-locations",
        "none",
        "-extensions",
        "cpp,h,cc,cxx,ui",
    ], f"head: {cmd}"
    assert "-no-obsolete" not in cmd, "obsolete translations are kept by default"
    assert str(pro.resolve()) in cmd, f"the .pro file must be passed through: {cmd}"
    works = _ts_args(cmd)
    assert [w.name.split(".")[-2] for w in works] == ["hello_en", "hello_de"], (
        f"source language first: {works}"
    )
    assert all(w.parent == out.resolve() and w.name.startswith(".") for w in works), (
        f"hidden siblings: {works}"
    )
    assert call["timeout"] == lupdate.LUPDATE_TIMEOUT, "lupdate must run with a timeout"
    assert call["cwd"] == str(pro.resolve().parent), (
        "lupdate runs from the .pro directory"
    )
    assert list(catalogs) == ["en", "de"], f"catalog order: {list(catalogs)}"
    assert ts_io.load(out / "hello_de.ts").target_lang == "de", (
        "language is written to the real file"
    )
    assert sorted(p.name for p in out.iterdir()) == ["hello_de.ts", "hello_en.ts"], (
        "work copies are removed"
    )


def test_run_when_no_obsolete_then_flag_passed(tmp_path, fake_lupdate):
    lupdate.run([tmp_path], tmp_path / "out", prefix="app", no_obsolete=True)
    assert "-no-obsolete" in fake_lupdate[0]["cmd"], (
        f"flag missing: {fake_lupdate[0]['cmd']}"
    )


def test_run_when_options_given_then_passed_through(tmp_path, fake_lupdate):
    (tmp_path / "src").mkdir()
    lupdate.run(
        [tmp_path],
        tmp_path / "out",
        prefix="app",
        locations="relative",
        extensions="cpp,ui",
        source_lang="de",
    )
    cmd = fake_lupdate[0]["cmd"]
    assert cmd[1:5] == ["-locations", "relative", "-extensions", "cpp,ui"], (
        f"options: {cmd}"
    )
    assert ["-I", str((tmp_path / "src").resolve())] == cmd[5:7], (
        f"nested src include path: {cmd}"
    )
    assert cmd[-1].endswith("app_de.ts"), (
        f"source language names the only catalog: {cmd}"
    )


def test_run_when_existing_catalog_then_lupdate_sees_a_copy(tmp_path, fake_lupdate):
    out = tmp_path / "out"
    out.mkdir()
    (out / "app_en.ts").write_text(
        EMPTY_TS.replace("/>", ' language="en"/>'), encoding="utf-8"
    )
    lupdate.run([tmp_path], out, prefix="app")
    assert _ts_args(fake_lupdate[0]["cmd"]) != [out / "app_en.ts"], (
        "lupdate must never edit the real file"
    )
    assert "Hello" in (out / "app_en.ts").read_text(encoding="utf-8"), (
        "real file replaced after success"
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"prefix": ""}, "prefix"),
        ({"prefix": None}, "prefix"),
        ({"prefix": "a", "locations": "all"}, "locations"),
    ],
)
def test_run_when_bad_arguments_then_value_error(
    tmp_path, fake_lupdate, kwargs, message
):
    with pytest.raises(ValueError, match=message):
        lupdate.run([tmp_path], tmp_path / "out", **kwargs)
    assert fake_lupdate == [], "bad arguments must fail before running lupdate"


def test_run_when_source_path_missing_then_value_error(tmp_path, fake_lupdate):
    with pytest.raises(ValueError, match="not found.*typo"):
        lupdate.run([tmp_path / "typo"], tmp_path / "out", prefix="app")
    assert fake_lupdate == [], "a missing source must fail before running lupdate"


def test_run_when_no_sources_then_value_error(tmp_path):
    with pytest.raises(ValueError, match="at least one"):
        lupdate.run([], tmp_path, prefix="app")


def test_run_when_no_messages_then_runtime_error_and_catalog_kept(
    tmp_path, monkeypatch
):
    _fake(monkeypatch, body=EMPTY_TS)
    out = tmp_path / "out"
    out.mkdir()
    (out / "app_de.ts").write_text(ONE_MESSAGE_TS, encoding="utf-8")
    with pytest.raises(RuntimeError, match="no messages"):
        lupdate.run([tmp_path], out, prefix="app", locales=["de"])
    assert (out / "app_de.ts").read_text(encoding="utf-8") == ONE_MESSAGE_TS, (
        "catalog must be untouched"
    )
    assert sorted(p.name for p in out.iterdir()) == ["app_de.ts"], (
        "no new or temporary files remain"
    )


def test_run_when_tool_fails_then_stderr_reported_and_catalog_kept(
    tmp_path, monkeypatch
):
    _fake(monkeypatch, code=2, stderr="Unknown option -bogus")
    out = tmp_path / "out"
    out.mkdir()
    (out / "app_en.ts").write_text(ONE_MESSAGE_TS, encoding="utf-8")
    with pytest.raises(RuntimeError, match="Unknown option -bogus"):
        lupdate.run([tmp_path], out, prefix="app")
    assert (out / "app_en.ts").read_text(encoding="utf-8") == ONE_MESSAGE_TS, (
        "catalog must be untouched"
    )
    assert sorted(p.name for p in out.iterdir()) == ["app_en.ts"], (
        "work copies are removed"
    )


@pytest.mark.parametrize(
    ("existing", "kept"), [("de_DE", "de_DE"), ("de", "de"), ("fr", "de"), (None, "de")]
)
def test_run_when_locale_catalog_has_language_then_regional_variant_kept(
    tmp_path, monkeypatch, existing, kept
):
    body = (
        ONE_MESSAGE_TS
        if existing is None
        else ONE_MESSAGE_TS.replace(
            'version="2.1"', f'version="2.1" language="{existing}"'
        )
    )
    _fake(monkeypatch, body=body)
    catalogs = lupdate.run([tmp_path], tmp_path / "out", prefix="app", locales=["de"])
    assert catalogs["de"].target_lang == kept, f"{existing} must become {kept}"
    assert ts_io.load(tmp_path / "out" / "app_de.ts").target_lang == kept, (
        "file matches the returned catalog"
    )


def test_run_tool_when_timeout_then_runtime_error(monkeypatch):
    def hang(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"], stderr=b"still parsing")

    monkeypatch.setattr(process.subprocess, "run", hang)
    with pytest.raises(RuntimeError, match="timed out.*still parsing"):
        process.run_tool("lupdate", ["lupdate"], timeout=1)
