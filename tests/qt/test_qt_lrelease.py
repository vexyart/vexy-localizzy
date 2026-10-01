# this_file: tests/qt/test_qt_lrelease.py
"""lrelease wrapper: missing tool, fake tool, output clashes, real compile."""

import subprocess
from pathlib import Path

import pytest

from vexy_localizzy import external
from vexy_localizzy.external import MissingDependencyError, ToolInfo, find_tool
from vexy_localizzy.qt import lrelease, lupdate, process

REAL_TOOLS = pytest.mark.skipif(
    not (find_tool("lupdate").found and find_tool("lrelease").found),
    reason="Qt tools not installed",
)


@pytest.fixture
def fake_lrelease(monkeypatch):
    calls = []
    monkeypatch.setattr(lrelease, "require_tool", lambda name: "/fake/bin/lrelease")
    monkeypatch.setattr(
        process.subprocess,
        "run",
        lambda cmd, **kw: (
            calls.append((cmd, kw)) or subprocess.CompletedProcess(cmd, 0, "", "")
        ),
    )
    return calls


def test_lrelease_run_when_tool_missing_then_missing_dependency(monkeypatch, tmp_path):
    monkeypatch.setattr(
        external, "find_tool", lambda name: ToolInfo(name=name, path=None, version=None)
    )
    with pytest.raises(MissingDependencyError, match="lrelease"):
        lrelease.run([tmp_path / "app_de.ts"])


def test_lrelease_run_when_fake_tool_then_qm_path_and_timeout(tmp_path, fake_lrelease):
    written = lrelease.run([tmp_path / "app_de.ts"], out_dir=tmp_path / "qm")
    assert written == [tmp_path / "qm" / "app_de.qm"], f"written: {written}"
    cmd, kwargs = fake_lrelease[0]
    assert cmd[2:] == ["-qm", str(tmp_path / "qm" / "app_de.qm")], f"command: {cmd}"
    assert kwargs["timeout"] == lrelease.LRELEASE_TIMEOUT, (
        "lrelease must run with a timeout"
    )


def test_lrelease_run_when_same_stem_into_out_dir_then_value_error(
    tmp_path, fake_lrelease
):
    catalogs = [tmp_path / "a" / "app_de.ts", tmp_path / "b" / "app_de.ts"]
    with pytest.raises(ValueError, match="overwrite.*app_de"):
        lrelease.run(catalogs, out_dir=tmp_path / "qm")
    assert fake_lrelease == [], "nothing may compile when outputs clash"


def test_lrelease_run_when_same_stem_beside_catalogs_then_allowed(
    tmp_path, fake_lrelease
):
    catalogs = [tmp_path / "a" / "app_de.ts", tmp_path / "b" / "app_de.ts"]
    written = lrelease.run(catalogs)
    assert written == [tmp_path / "a" / "app_de.qm", tmp_path / "b" / "app_de.qm"], (
        f"siblings: {written}"
    )


@REAL_TOOLS
def test_lrelease_run_when_real_tool_then_qm_written(tmp_path):
    (tmp_path / "hello.cpp").write_text(
        'QString s = QObject::tr("Hello");\n', encoding="utf-8"
    )
    lupdate.run([tmp_path], tmp_path / "i18n", prefix="hello", locales=["de"])
    written = lrelease.run([tmp_path / "i18n" / "hello_de.ts"])
    assert written[0].is_file(), f"lrelease must write {written[0]}"
    assert written == [Path(tmp_path / "i18n" / "hello_de.qm")], f"written: {written}"
