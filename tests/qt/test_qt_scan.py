# this_file: tests/qt/test_qt_scan.py
"""Heuristic Qt scan over small C++ and .ui fixtures, plus SARIF output."""

import json
from pathlib import Path

import pytest

from vexy_localizzy.external import MissingDependencyError
from vexy_localizzy.qt import compile_db, scan, scan_clang
from vexy_localizzy.report import RULES, findings_sarif

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "qt"


def _ids(findings) -> set[str]:
    return {f.rule_id for f in findings}


def _lines(findings, rule_id: str) -> list[int]:
    return sorted(
        int(f.location.rsplit(":", 1)[1]) for f in findings if f.rule_id == rule_id
    )


def _scan_source(tmp_path: Path, source: str):
    path = tmp_path / "snippet.cpp"
    path.write_text(source, encoding="utf-8")
    return scan.scan_cpp_file(path)[1]


def test_scan_cpp_file_when_widget_fixture_then_core_rules_found():
    coverage, findings = scan.scan_cpp_file(FIXTURES / "fake_widget.cpp")
    ids = _ids(findings)
    expected = {
        "QT-CTX-001",
        "QT-HARD-003",
        "QT-TR-002",
        "QT-ARG-006",
        "QT-CONCAT-007",
        "QT-TRUTF8-011",
    }
    assert expected <= ids, f"missing rules {expected - ids}"
    assert coverage.marked >= 1, f"literal tr() calls must count as marked: {coverage}"


def test_scan_ui_file_when_notr_visible_string_then_flagged():
    findings = scan.scan_ui_file(FIXTURES / "fake_dialog.ui")
    assert "QT-UI-009" in _ids(findings), f"expected QT-UI-009 in {_ids(findings)}"
    assert any("Apply Now" in f.message for f in findings), (
        "notr button text must be flagged"
    )
    assert not any("font-size" in f.message for f in findings), (
        "notr styleSheet is not user-visible"
    )


def test_scan_ui_file_when_whitespace_label_then_nothing_blocking():
    findings = scan.scan_ui_file(FIXTURES / "fake_empty_label.ui")
    blocking = [f for f in findings if f.severity in ("major", "critical")]
    assert blocking == [], (
        f"clean form must not produce major/critical findings: {blocking}"
    )


def test_scan_ui_file_when_malformed_then_info_finding(tmp_path):
    bad = tmp_path / "bad.ui"
    bad.write_text("<ui><widget>", encoding="utf-8")
    findings = scan.scan_ui_file(bad)
    assert [f.severity for f in findings] == ["info"], (
        f"parse failure is reported as info: {findings}"
    )


def test_run_when_fixture_dir_then_report_has_critical_findings():
    report = scan.run([FIXTURES], engine="heuristic", include_ui=True)
    assert report.findings, "fixture scan must produce findings"
    assert 0.0 <= report.overall_coverage <= 1.0, (
        f"coverage out of range: {report.overall_coverage}"
    )
    assert report.counts_by_severity["critical"] >= 1, (
        f"counts: {report.counts_by_severity}"
    )


def test_scan_cpp_file_when_namespaced_fixture_then_ns_and_noop_found():
    _, findings = scan.scan_cpp_file(FIXTURES / "fake_namespaced.cpp")
    assert _lines(findings, "QT-NS-004") == [7, 19], f"NS-004 lines wrong: {findings}"
    assert _lines(findings, "QT-NOOP-008") == [15], f"NOOP-008 lines wrong: {findings}"
    severities = {f.rule_id: f.severity for f in findings}
    assert severities["QT-NS-004"] == "major", "QT-NS-004 is major"
    assert severities["QT-NOOP-008"] == "minor", "QT-NOOP-008 is minor"
    assert all(f.confidence == "heuristic" for f in findings), (
        "regex findings are heuristic"
    )


@pytest.mark.parametrize(
    "source",
    [
        'static const char *a = QT_TRANSLATE_NOOP("Ctx", "Fine");\n',
        'class Holder {\n    const char *b = QT_TR_NOOP("In class");\n};\n',
        'struct Item {\n    static constexpr const char *c = QT_TR_NOOP("In struct");\n};\n',
        "class Plain {\n    Q_DECLARE_TR_FUNCTIONS(Plain)\n};\n",
        '// static const char *d = QT_TR_NOOP("commented out");\n',
        "namespace {\nclass Hidden {\n    Q_DECLARE_TR_FUNCTIONS(Hidden)\n};\n}\n",
    ],
)
def test_scan_cpp_file_when_context_is_explicit_then_ns_and_noop_silent(
    tmp_path, source
):
    ids = _ids(_scan_source(tmp_path, source))
    assert not ids & {"QT-NS-004", "QT-NOOP-008"}, (
        f"false positive {ids} for {source!r}"
    )


def test_scan_cpp_file_when_nested_namespace_then_ns_flagged(tmp_path):
    source = "namespace a::b {\nclass X {\n    Q_DECLARE_TR_FUNCTIONS(X)\n};\n}\n"
    findings = _scan_source(tmp_path, source)
    assert _lines(findings, "QT-NS-004") == [3], (
        f"nested namespace must be flagged: {findings}"
    )


def test_scan_cpp_file_when_not_utf8_then_info_finding(tmp_path):
    path = tmp_path / "latin.cpp"
    path.write_bytes(b'// caf\xe9\nQString s = tr("x");\n')
    _, findings = scan.scan_cpp_file(path)
    assert "QT-UTF8-010" in _ids(findings), f"Latin-1 file must be flagged: {findings}"


def test_run_when_unknown_engine_then_value_error():
    with pytest.raises(ValueError, match="unknown scan engine"):
        scan.run([FIXTURES], engine="fast")


@pytest.mark.parametrize("engine", ["clang", "both"])
def test_run_when_clang_extra_missing_then_missing_dependency(monkeypatch, engine):
    monkeypatch.setattr(scan, "extra_installed", lambda extra: False)
    with pytest.raises(MissingDependencyError, match="clang"):
        scan.run([FIXTURES], engine=engine)


def test_scan_cpp_file_clang_when_extra_missing_then_missing_dependency(monkeypatch):
    monkeypatch.setattr(scan_clang, "extra_installed", lambda extra: False)
    with pytest.raises(MissingDependencyError, match="clang"):
        scan_clang.scan_cpp_file_clang(FIXTURES / "fake_widget.cpp")


def _db(tmp_path: Path, entries: list[dict]) -> Path:
    db = tmp_path / "compile_commands.json"
    db.write_text(json.dumps(entries), encoding="utf-8")
    return db


def test_compile_args_for_when_entry_matches_then_output_flags_dropped(tmp_path):
    source = tmp_path / "a.cpp"
    source.write_text("", encoding="utf-8")
    args = ["c++", "-Iinc", "-c", "-o", "a.o", str(source.resolve())]
    db = _db(
        tmp_path,
        [
            {
                "directory": str(tmp_path),
                "file": str(source.resolve()),
                "arguments": args,
            }
        ],
    )
    expected = ["-working-directory", str(tmp_path), "-Iinc"]
    assert compile_db.compile_args_for(source, db) == expected, (
        "only parse flags must remain"
    )
    assert compile_db.compile_args_for(source, None) == compile_db.DEFAULT_ARGS, (
        "no database uses defaults"
    )


def test_compile_args_for_when_relative_file_and_command_then_resolved_and_split(
    tmp_path,
):
    build = tmp_path / "build"
    build.mkdir()
    (tmp_path / "src").mkdir()
    source = tmp_path / "src" / "my file.cpp"
    source.write_text("", encoding="utf-8")
    command = 'c++ -DNAME="a b" -I../inc -c "../src/my file.cpp"'
    db = _db(
        tmp_path,
        [{"directory": str(build), "file": "../src/my file.cpp", "command": command}],
    )
    got = compile_db.compile_args_for(source, db)
    assert got == ["-working-directory", str(build), "-DNAME=a b", "-I../inc"], (
        f"args: {got}"
    )


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (None, "not found"),
        ("{not json", "cannot read"),
        ('{"a": 1}', "JSON array"),
        ('[{"x": 1}]', "file"),
    ],
)
def test_run_when_compile_commands_bad_then_value_error(tmp_path, content, message):
    db = tmp_path / "compile_commands.json"
    if content is not None:
        db.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        scan.run([FIXTURES / "fake_widget.cpp"], compile_commands=db)


def test_run_when_path_missing_then_value_error(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        scan.run([tmp_path / "nonexistent"])


def test_findings_sarif_when_fixture_scan_then_rule_catalog_complete():
    report = scan.run([FIXTURES], engine="heuristic", include_ui=True)
    sarif = json.loads(findings_sarif(report.findings))
    rules = sarif["runs"][0]["tool"]["driver"]["rules"]
    emitted = _ids(report.findings)
    assert {r["id"] for r in rules} == emitted, (
        f"rule catalog must match emitted ids {emitted}"
    )
    assert emitted <= set(RULES), (
        f"ids without a RULES description: {emitted - set(RULES)}"
    )
    assert {"QT-NS-004", "QT-NOOP-008"} <= emitted, "new detectors must reach SARIF"
    assert all(r["name"] != r["id"] for r in rules), (
        "every rule must carry its descriptive name"
    )
