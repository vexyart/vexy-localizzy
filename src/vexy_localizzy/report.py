# this_file: src/vexy_localizzy/report.py
"""Render findings as a text table, JSON or SARIF 2.1.0.

One renderer set over the shared ``Finding`` type, so every command that
reports findings (``qa``, ``qt scan``, ``vocab validate``) offers the same
formats. SARIF is what code-scanning services ingest.
"""

import json
from collections.abc import Sequence
from pathlib import Path

from vexy_localizzy.catalog import Finding
from vexy_localizzy.formats.document import atomic_write

FORMATS = ("table", "json", "sarif")
SEVERITY_RANK = {"info": 0, "minor": 1, "major": 2, "critical": 3}
SARIF_LEVEL = {"info": "note", "minor": "note", "major": "warning", "critical": "error"}
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"

# Rule descriptions for SARIF ``tool.driver.rules``; other rules get a stub.
RULES: dict[str, tuple[str, str]] = {
    "QT-CTX-001": (
        "MissingQObject",
        "QObject-derived class calls tr() but lacks the Q_OBJECT macro.",
    ),
    "QT-TR-002": (
        "NonLiteralTrArgument",
        "tr()/translate() called with a non-literal argument; lupdate cannot extract it.",
    ),
    "QT-HARD-003": (
        "HardcodedUiString",
        "Hardcoded user-visible string in a UI setter without tr().",
    ),
    "QT-NS-004": (
        "NamespacedTrContext",
        "Q_DECLARE_TR_FUNCTIONS in a namespaced context; lupdate may mis-file the context.",
    ),
    "QT-STATIC-005": (
        "StaticScopeTr",
        "tr() at static-initialization scope runs before a translator is installed.",
    ),
    "QT-ARG-006": (
        "ChainedArg",
        "Chained .arg().arg() can substitute a placeholder injected by an earlier value.",
    ),
    "QT-CONCAT-007": (
        "ConcatenatedFragments",
        "Translatable fragments are concatenated; word order cannot be translated.",
    ),
    "QT-NOOP-008": (
        "TrNoopOutsideClass",
        "QT_TR_NOOP outside a class has no context; use QT_TRANSLATE_NOOP.",
    ),
    "QT-UI-009": (
        "UiStringIssue",
        "User-visible string in a .ui form is marked notr or needs review.",
    ),
    "QT-UTF8-010": ("NonUtf8SourceFile", "Source file is not UTF-8 encoded."),
    "QT-TRUTF8-011": ("DeprecatedTrUtf8", "trUtf8() was removed; use tr()."),
    "QT-CLANG-012": (
        "IncompleteClangAst",
        "clang could not fully parse the file (e.g. missing includes); heuristic findings are reported instead.",
    ),
}


def blocking(findings: Sequence[Finding], fail_on: str) -> list[Finding]:
    """Findings at or above ``fail_on``; an unknown level raises ValueError."""
    if fail_on not in SEVERITY_RANK:
        raise ValueError(f"fail_on must be one of {', '.join(SEVERITY_RANK)}")
    threshold = SEVERITY_RANK[fail_on]
    return [f for f in findings if SEVERITY_RANK[f.severity] >= threshold]


def findings_json(findings: Sequence[Finding]) -> str:
    return json.dumps([f.model_dump() for f in findings], indent=2, ensure_ascii=False)


def findings_table(findings: Sequence[Finding], *, title: str = "Findings") -> str:
    """A plain aligned table with a severity summary line."""
    rows = [
        (f.rule_id, f.severity, f.location or f.unit_key or "", f.message)
        for f in findings
    ]
    widths = [max((len(r[i]) for r in rows), default=0) for i in range(3)]
    lines = [title] + [
        "  ".join(cell.ljust(width) for cell, width in zip(row[:3], widths))
        + "  "
        + row[3]
        for row in rows
    ]
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    summary = ", ".join(f"{n} {severity}" for severity, n in sorted(counts.items()))
    lines.append(f"{len(findings)} finding(s)" + (f": {summary}" if summary else ""))
    return "\n".join(lines)


def _sarif_location(location: str) -> dict:
    parts = location.split(":")
    # A Windows drive letter ("C:\\path\\file:10:5") is part of the file name.
    if len(parts) >= 2 and len(parts[0]) == 1 and parts[0].isalpha():
        parts = [parts[0] + ":" + parts[1], *parts[2:]]
    region: dict = {}
    if len(parts) > 1 and parts[1].isdigit():
        region["startLine"] = int(parts[1])
        if len(parts) > 2 and parts[2].isdigit():
            region["startColumn"] = int(parts[2])
    physical: dict = {"artifactLocation": {"uri": parts[0]}}
    if region:
        physical["region"] = region
    return {"physicalLocation": physical}


def findings_sarif(findings: Sequence[Finding], *, tool_name: str = "localizzy") -> str:
    """SARIF 2.1.0 with one rule descriptor per rule that occurs."""
    rules: dict[str, dict] = {}
    results = []
    for finding in findings:
        level = SARIF_LEVEL[finding.severity]
        if finding.rule_id not in rules:
            name, text = RULES.get(finding.rule_id, (finding.rule_id, finding.rule_id))
            rules[finding.rule_id] = {
                "id": finding.rule_id,
                "name": name,
                "shortDescription": {"text": text},
                "defaultConfiguration": {"level": level},
            }
        result: dict = {
            "ruleId": finding.rule_id,
            "level": level,
            "message": {"text": finding.message},
        }
        if finding.location:
            result["locations"] = [_sarif_location(finding.location)]
        results.append(result)
    sarif = {
        "version": "2.1.0",
        "$schema": SARIF_SCHEMA,
        "runs": [
            {
                "tool": {"driver": {"name": tool_name, "rules": list(rules.values())}},
                "results": results,
            }
        ],
    }
    return json.dumps(sarif, indent=2)


def render(findings: Sequence[Finding], format: str, *, title: str = "Findings") -> str:
    """Render findings in one of ``FORMATS``."""
    if format == "json":
        return findings_json(findings)
    if format == "sarif":
        return findings_sarif(findings)
    if format == "table":
        return findings_table(findings, title=title)
    raise ValueError(f"format must be one of {', '.join(FORMATS)}")


def emit(
    findings: Sequence[Finding],
    format: str,
    out: str | Path | None = None,
    *,
    title: str = "Findings",
) -> None:
    """Write the rendering to ``out`` atomically, or print it."""
    text = render(findings, format, title=title)
    if out:
        atomic_write(Path(out), (text + "\n").encode("utf-8"))
        print(f"wrote {out}")
    else:
        print(text)
