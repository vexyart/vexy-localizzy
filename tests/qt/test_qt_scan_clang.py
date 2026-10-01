# this_file: tests/qt/test_qt_scan_clang.py
"""Real libclang pass: incomplete ASTs are flagged, clean parses give exact findings."""

from pathlib import Path

import pytest

from vexy_localizzy.external import extra_installed
from vexy_localizzy.qt import compile_db, scan, scan_clang
from vexy_localizzy.report import RULES

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "qt"


def _ids(findings) -> set[str]:
    return {f.rule_id for f in findings}


CLANG = pytest.mark.skipif(
    not extra_installed("clang"), reason="clang extra not installed"
)
SELF_CONTAINED = FIXTURES / "clang_selfcontained.cpp"


@CLANG
def test_scan_cpp_file_clang_when_includes_missing_then_only_incomplete_finding():
    findings = scan_clang.scan_cpp_file_clang(FIXTURES / "fake_widget.cpp")
    assert [f.rule_id for f in findings] == ["QT-CLANG-012"], (
        f"degraded AST must not invent findings: {findings}"
    )
    incomplete = findings[0]
    assert (incomplete.severity, incomplete.confidence) == ("major", "exact"), (
        f"wrong grading: {incomplete}"
    )
    assert "fake_widget.h" in incomplete.message, (
        f"must name the unresolved include: {incomplete.message}"
    )
    assert "--compile-commands" in incomplete.message, (
        f"must point to the fix: {incomplete.message}"
    )
    assert "QT-CLANG-012" in RULES, "SARIF needs a description for QT-CLANG-012"


@CLANG
def test_run_when_clang_engine_and_includes_missing_then_heuristic_fallback():
    report = scan.run([FIXTURES / "fake_widget.cpp"], engine="clang")
    ids = _ids(report.findings)
    assert {"QT-CLANG-012", "QT-CTX-001", "QT-TR-002"} <= ids, (
        f"file must not read as clean: {ids}"
    )
    assert report.counts_by_severity["critical"] >= 1, (
        f"fallback keeps critical findings: {report.counts_by_severity}"
    )


@CLANG
def test_run_when_both_engine_and_includes_missing_then_incomplete_added():
    ids = _ids(scan.run([FIXTURES / "fake_widget.cpp"], engine="both").findings)
    assert {"QT-CLANG-012", "QT-CTX-001", "QT-TR-002"} <= ids, (
        f"both must keep heuristic and flag the AST: {ids}"
    )


@CLANG
def test_scan_cpp_file_clang_when_clean_parse_then_exact_findings_with_columns():
    findings = scan_clang.scan_cpp_file_clang(SELF_CONTAINED)
    got = sorted((f.rule_id, f.location, f.confidence) for f in findings)
    expected = [
        ("QT-CTX-001", f"{SELF_CONTAINED}:17:7", "exact"),
        ("QT-TR-002", f"{SELF_CONTAINED}:21:9", "exact"),
    ]
    assert got == expected, f"literal tr() and GoodDialog must stay silent; got {got}"


@CLANG
def test_run_when_clang_engine_and_clean_parse_then_no_heuristic_fallback():
    report = scan.run([SELF_CONTAINED], engine="clang")
    assert all(f.confidence == "exact" for f in report.findings), (
        f"clean parse reports clang only: {report.findings}"
    )
    assert "QT-CLANG-012" not in _ids(report.findings), (
        "clean parse must not be marked incomplete"
    )


@CLANG
def test_scan_cpp_file_clang_when_header_then_parsed_as_cpp_header():
    header = FIXTURES / "clang_selfcontained.h"
    assert compile_db.compile_args_for(header, None)[:2] == ["-x", "c++-header"], (
        "headers need a language flag"
    )
    got = sorted(
        (f.rule_id, f.location) for f in scan_clang.scan_cpp_file_clang(header)
    )
    assert got == [("QT-CTX-001", f"{header}:17:7"), ("QT-TR-002", f"{header}:21:9")], (
        f"header findings: {got}"
    )


@CLANG
def test_run_when_translation_unit_fails_to_load_then_incomplete_and_fallback(
    monkeypatch,
):
    import clang.cindex as cindex

    def refuse(self, *args, **kwargs):
        raise cindex.TranslationUnitLoadError("Error parsing translation unit.")

    monkeypatch.setattr(cindex.Index, "parse", refuse)
    report = scan.run([FIXTURES / "fake_widget.cpp"], engine="clang")
    incomplete = [f for f in report.findings if f.rule_id == "QT-CLANG-012"]
    assert len(incomplete) == 1, (
        f"load error must become one QT-CLANG-012: {report.findings}"
    )
    assert "not loaded" in incomplete[0].message, (
        f"message must say why: {incomplete[0].message}"
    )
    assert {"QT-CTX-001", "QT-TR-002"} <= _ids(report.findings), (
        "heuristic fallback must be reported"
    )
