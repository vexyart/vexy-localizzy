# this_file: src/vexy_localizzy/qt/scan_cpp.py
"""Heuristic per-file pass over one C++ source file.

A fast line/regex pass with known false positives (``tr`` in block comments,
multi-line literals), so its findings are marked ``heuristic``. Line rules
live here; rules that need class or namespace scope live in
``qt.scan_scope``. ``FileCoverage`` counts marked versus hardcoded strings.
Used by ``qt.scan``.
"""

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from vexy_localizzy.catalog import Finding
from vexy_localizzy.qt.cpp_text import code_text, strip_comment
from vexy_localizzy.qt.scan_scope import heuristic, scope_findings

# UI setters that take user-facing text (QT-HARD-003).
_UI_SETTERS = (
    "setText",
    "setWindowTitle",
    "setToolTip",
    "setPlaceholderText",
    "setStatusTip",
    "setWhatsThis",
    "addItem",
    "setTitle",
    "setLabel",
)
_SETTER_RE = re.compile(r"\b(" + "|".join(_UI_SETTERS) + r")\s*\(\s*(.*?)\s*\)")
_TR_ANY_RE = re.compile(r"\b(tr|translate)\s*\(\s*([^)]*)")
_STRING_LITERAL_RE = re.compile(r'"(?:[^"\\]|\\.)*"')
_IDENTIFIER_USE_RE = re.compile(r"^[A-Za-z_]\w*(\s*[\.\->]|\s*\()")
_ARG_PREVIEW = 60  # characters of a non-literal tr() argument kept in the finding

# (pattern, rule id, severity, message) for rules that need only one line.
_LINE_RULES = (
    (
        re.compile(r"\btrUtf8\s*\("),
        "QT-TRUTF8-011",
        "minor",
        "Use of removed trUtf8() (use tr() in Qt 5/6).",
    ),
    (
        re.compile(r"\bstatic\b.*\b(?:tr|QObject::tr)\s*\("),
        "QT-STATIC-005",
        "major",
        "tr() at static-init scope locks in the C locale.",
    ),
    (
        re.compile(r"\.arg\s*\([^)]*\)\s*\.arg\s*\("),
        "QT-ARG-006",
        "minor",
        "Chained .arg().arg() risks recursive % injection.",
    ),
    (
        re.compile(r"\b(?:tr|translate)\s*\([^)]*\)\s*\+"),
        "QT-CONCAT-007",
        "minor",
        "Concatenation of translatable fragments (never concat).",
    ),
)


class FileCoverage(BaseModel):
    """Marked (``tr``-wrapped) versus hardcoded user-facing strings in one file."""

    path: str
    tr_calls: int = 0
    marked: int = 0
    hardcoded_candidates: int = 0

    @property
    def coverage(self) -> float:
        denom = self.marked + self.hardcoded_candidates
        return (self.marked / denom) if denom else 1.0

    model_config = ConfigDict(frozen=True)


def _is_nonliteral_tr_arg(arg: str) -> bool:
    """A tr() argument that is not a string literal: lupdate silently skips it."""
    arg = arg.strip()
    if not arg or arg.startswith(('"', 'QStringLiteral("', 'QStringLiteral( "')):
        return False
    return bool(_IDENTIFIER_USE_RE.match(arg)) or arg[0].isalpha()


def _read(path: Path) -> tuple[str, bool]:
    """File text and whether it decoded as UTF-8 (otherwise Latin-1)."""
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8"), True
    except UnicodeDecodeError:
        return raw.decode("latin-1"), False


def _line_findings(line: str, loc: str) -> tuple[list[Finding], int, int, int]:
    """Findings plus (tr_calls, marked, hardcoded) counts for one stripped line."""
    findings = [
        heuristic(rule, sev, msg, loc)
        for rx, rule, sev, msg in _LINE_RULES
        if rx.search(line)
    ]
    tr_calls = marked = hardcoded = 0
    for m in _TR_ANY_RE.finditer(line):
        tr_calls += 1
        if not _is_nonliteral_tr_arg(m.group(2)):
            marked += 1
            continue
        findings.append(
            heuristic(
                "QT-TR-002",
                "critical",
                "tr()/translate() called with a non-literal argument (silent extraction failure).",
                loc,
                {"arg": m.group(2)[:_ARG_PREVIEW]},
            )
        )
    for m in _SETTER_RE.finditer(line):
        inner = m.group(2)
        if (
            not _STRING_LITERAL_RE.search(inner)
            or "tr(" in inner
            or "translate(" in inner
        ):
            continue
        hardcoded += 1
        findings.append(
            heuristic(
                "QT-HARD-003",
                "major",
                f"Hardcoded literal in {m.group(1)}() without tr().",
                loc,
                {"setter": m.group(1)},
            )
        )
    return findings, tr_calls, marked, hardcoded


def scan_cpp_file(path: Path) -> tuple[FileCoverage, list[Finding]]:
    """Heuristic scan of one C++ source file."""
    text, utf8_ok = _read(path)
    findings: list[Finding] = []
    if not utf8_ok:
        findings.append(
            Finding(
                rule_id="QT-UTF8-010",
                severity="info",
                message=f"Source file is not UTF-8: {path.name}",
                location=str(path),
            )
        )
    findings += scope_findings(path, code_text(text))
    tr_calls = marked = hardcoded = 0
    for idx, raw in enumerate(text.splitlines(), start=1):
        found, calls, ok, hard = _line_findings(strip_comment(raw), f"{path}:{idx}")
        findings += found
        tr_calls, marked, hardcoded = tr_calls + calls, marked + ok, hardcoded + hard
    coverage = FileCoverage(
        path=str(path), tr_calls=tr_calls, marked=marked, hardcoded_candidates=hardcoded
    )
    return coverage, findings
