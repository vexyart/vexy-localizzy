# this_file: src/vexy_localizzy/qt/scan_scope.py
"""Scope-level heuristic detectors: class context and namespace context.

These rules need to know which ``class``/``namespace`` body a match sits in,
so they run over the whole comment-stripped file rather than line by line:

- QT-CTX-001: a QObject-derived class that calls ``tr()`` without ``Q_OBJECT``.
- QT-NS-004: ``Q_DECLARE_TR_FUNCTIONS`` with a qualified name or inside a
  named namespace, where lupdate and the runtime may disagree on the context.
- QT-NOOP-008: ``QT_TR_NOOP`` outside any class/struct body, where it has no
  class context (``QT_TRANSLATE_NOOP`` names its context and is not flagged).

Used by ``qt.scan_cpp``; ``QOBJECT_BASES`` is shared with ``qt.scan_clang``.
"""

import re
from pathlib import Path

from vexy_localizzy.catalog import Finding, Severity
from vexy_localizzy.qt.cpp_text import block_span, inside, line_of

QOBJECT_BASES = (
    "QObject",
    "QWidget",
    "QDialog",
    "QMainWindow",
    "QFrame",
    "QAbstractItemModel",
)
_TR_RE = re.compile(r"\b(?:tr|translate|QT_TR_NOOP|QT_TRANSLATE_NOOP)\s*\(")
_QOBJECT_CLASS_RE = re.compile(
    r"\bclass\s+(\w+)\s*(?:final\s*)?:\s*(?:public|protected|private)?\s*([\w:]+)"
)
# class/struct definition head: optional export macro, name, optional bases, "{".
_SCOPE_RE = re.compile(
    r"\b(?:class|struct)\s+(?:\w+\s+)?[\w:]+(?:\s+final)?\s*(?::[^;{}()]*)?\{"
)
_NAMESPACE_RE = re.compile(r"\bnamespace\s+\w+(?:::\w+)*\s*\{")
_DECLARE_TR_RE = re.compile(r"\bQ_DECLARE_TR_FUNCTIONS\s*\(\s*([\w:]+)\s*\)")
_TR_NOOP_RE = re.compile(r"\bQT_TR_NOOP\s*\(")


def heuristic(
    rule_id: str,
    severity: Severity,
    message: str,
    location: str,
    data: dict | None = None,
) -> Finding:
    """A finding from a regex detector; always ``confidence="heuristic"``."""
    return Finding(
        rule_id=rule_id,
        severity=severity,
        message=message,
        location=location,
        confidence="heuristic",
        data=data or {},
    )


def _spans(pattern: re.Pattern[str], code: str) -> list[tuple[int, int]]:
    """Brace-matched bodies opened by each ``pattern`` match."""
    return [
        span for m in pattern.finditer(code) if (span := block_span(code, m.end() - 1))
    ]


def context_findings(path: Path, code: str) -> list[Finding]:
    """QT-CTX-001 over QObject-derived class bodies."""
    findings: list[Finding] = []
    for match in _QOBJECT_CLASS_RE.finditer(code):
        name, base = match.group(1), match.group(2).split("::")[-1]
        span = block_span(code, match.end())
        if base not in QOBJECT_BASES or span is None:
            continue
        body = code[span[0] : span[1]]
        if "Q_OBJECT" in body or not _TR_RE.search(body):
            continue
        findings.append(
            heuristic(
                "QT-CTX-001",
                "critical",
                f"Class '{name}' derives from {base} and calls tr() but lacks Q_OBJECT (context drift).",
                f"{path}:{line_of(code, match.start())}",
                {"class": name, "base": base},
            )
        )
    return findings


def namespace_findings(path: Path, code: str) -> list[Finding]:
    """QT-NS-004 for qualified or namespace-nested ``Q_DECLARE_TR_FUNCTIONS``."""
    namespaces = _spans(_NAMESPACE_RE, code)
    findings: list[Finding] = []
    for match in _DECLARE_TR_RE.finditer(code):
        name = match.group(1)
        if "::" not in name and not inside(match.start(), namespaces):
            continue
        findings.append(
            heuristic(
                "QT-NS-004",
                "major",
                f"Q_DECLARE_TR_FUNCTIONS({name}) in a namespaced context; lupdate may file it under another context.",
                f"{path}:{line_of(code, match.start())}",
                {"context": name},
            )
        )
    return findings


def noop_findings(path: Path, code: str) -> list[Finding]:
    """QT-NOOP-008 for ``QT_TR_NOOP`` outside every class/struct body."""
    classes = _spans(_SCOPE_RE, code)
    return [
        heuristic(
            "QT-NOOP-008",
            "minor",
            "QT_TR_NOOP outside a class has no context; use QT_TRANSLATE_NOOP.",
            f"{path}:{line_of(code, match.start())}",
        )
        for match in _TR_NOOP_RE.finditer(code)
        if not inside(match.start(), classes)
    ]


def scope_findings(path: Path, code: str) -> list[Finding]:
    """All scope-level findings for one comment-stripped file."""
    return (
        context_findings(path, code)
        + namespace_findings(path, code)
        + noop_findings(path, code)
    )
