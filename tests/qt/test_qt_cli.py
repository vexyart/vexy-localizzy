# this_file: tests/qt/test_qt_cli.py
"""``localizzy qt`` command functions: usage errors exit 2 before any work."""

import inspect
from pathlib import Path

import pytest

from vexy_localizzy.cli import qt as cli
from vexy_localizzy.qt import lupdate

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "qt"


@pytest.fixture(autouse=True)
def no_project_file(tmp_path, monkeypatch):
    """Run where no localizzy.toml can be discovered."""
    monkeypatch.chdir(tmp_path)


def _exit_code(func, *args, **kwargs) -> int:
    with pytest.raises(SystemExit) as exc:
        func(*args, **kwargs)
    return exc.value.code


def test_scan_when_path_missing_then_exit_2(tmp_path, capsys):
    code = _exit_code(cli.scan, str(tmp_path / "nonexistent"), min_coverage=0.9)
    assert code == cli.EXIT_USAGE, f"missing path must be a usage error, got {code}"
    assert "not found" in capsys.readouterr().err, "the message must say why"


def test_scan_when_format_unknown_then_exit_2_before_scanning(monkeypatch, capsys):
    monkeypatch.setattr(
        "vexy_localizzy.qt.scan.run", lambda *a, **k: pytest.fail("scan must not run")
    )
    assert _exit_code(cli.scan, str(FIXTURES), format="xml") == cli.EXIT_USAGE, (
        "bad format exits 2"
    )
    assert "--format" in capsys.readouterr().err, "the message must name the flag"


def test_scan_when_out_directory_missing_then_exit_2(tmp_path):
    code = _exit_code(
        cli.scan, str(FIXTURES / "fake_dialog.ui"), out=str(tmp_path / "no" / "r.json")
    )
    assert code == cli.EXIT_USAGE, (
        f"--out into a missing directory must exit 2, got {code}"
    )


def test_scan_when_min_coverage_and_no_cpp_files_then_exit_2(capsys):
    code = _exit_code(cli.scan, str(FIXTURES / "fake_dialog.ui"), min_coverage=0.9)
    assert code == cli.EXIT_USAGE, (
        f"coverage over zero files is a usage error, got {code}"
    )
    assert "C++" in capsys.readouterr().err, (
        "the message must explain the zero-file case"
    )


def test_scan_when_json_out_then_file_written(tmp_path):
    out = tmp_path / "scan.json"
    assert (
        _exit_code(
            cli.scan, str(FIXTURES / "fake_widget.cpp"), format="json", out=str(out)
        )
        == cli.EXIT_FINDINGS
    ), "critical findings exit 1"
    assert '"overall_coverage"' in out.read_text(encoding="utf-8"), (
        "JSON report must be written"
    )


def test_extract_when_no_obsolete_flag_then_passed_to_lupdate(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(lupdate, "run", lambda *a, **kw: seen.update(kw) or {})
    cli.extract(
        str(tmp_path), out_dir=str(tmp_path / "out"), prefix="app", no_obsolete=True
    )
    assert seen["no_obsolete"] is True, f"--no-obsolete must reach lupdate: {seen}"
    cli.extract(str(tmp_path), out_dir=str(tmp_path / "out"), prefix="app")
    assert seen["no_obsolete"] is False, "obsolete translations are kept by default"


def test_extract_when_source_missing_then_exit_2(tmp_path):
    code = _exit_code(
        cli.extract, str(tmp_path / "typo"), out_dir=str(tmp_path / "out"), prefix="app"
    )
    assert code == cli.EXIT_USAGE, f"missing source must exit 2, got {code}"


def test_release_when_outputs_clash_then_exit_2(tmp_path):
    code = _exit_code(
        cli.release,
        str(tmp_path / "a" / "x_de.ts"),
        str(tmp_path / "b" / "x_de.ts"),
        out_dir=str(tmp_path),
    )
    assert code == cli.EXIT_USAGE, f"clashing outputs must exit 2, got {code}"


def test_applang_list_when_inspected_then_flag_is_source_lang():
    params = inspect.signature(cli.applang_list).parameters
    assert "source_lang" in params and "source_language" not in params, (
        f"flag name: {list(params)}"
    )
