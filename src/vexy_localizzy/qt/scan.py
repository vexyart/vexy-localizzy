# this_file: src/vexy_localizzy/qt/scan.py
"""Localizability scan over Qt C++ source and ``.ui`` forms.

The ``heuristic`` engine is a fast regex pass (``qt.scan_cpp``). The optional
``clang`` engine (``qt.scan_clang``) uses libclang for exact QT-TR-002 and
QT-CTX-001 detection; ``both`` runs the heuristic pass everywhere and adds the
clang pass for files with critical findings. Scanning never edits source; it
reports findings as data for ``vexy_localizzy.report``.
"""

from pathlib import Path

from lxml import etree
from pydantic import BaseModel, ConfigDict, Field

from vexy_localizzy.catalog import Finding
from vexy_localizzy.external import (
    MissingDependencyError,
    extra_installed,
    install_command,
)
from vexy_localizzy.qt import ui as ui_io
from vexy_localizzy.qt.compile_db import load_compile_commands
from vexy_localizzy.qt.scan_clang import INCOMPLETE_RULE, scan_cpp_file_clang
from vexy_localizzy.qt.scan_cpp import FileCoverage, scan_cpp_file
from vexy_localizzy.report import SEVERITY_RANK

__all__ = [
    "CPP_EXTS",
    "ENGINES",
    "FileCoverage",
    "ScanReport",
    "run",
    "scan_cpp_file",
    "scan_ui_file",
]

CPP_EXTS = (".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx")
ENGINES = ("heuristic", "clang", "both")
# .ui properties that carry user-visible text.
VISIBLE_PROPS = frozenset(
    {
        "text",
        "title",
        "toolTip",
        "windowTitle",
        "statusTip",
        "placeholderText",
        "whatsThis",
    }
)
_PREVIEW = 40  # characters of a flagged .ui string quoted in the message


class ScanReport(BaseModel):
    repos: list[str]
    engine: str = "heuristic"
    files: list[FileCoverage] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)

    @property
    def overall_coverage(self) -> float:
        marked = sum(f.marked for f in self.files)
        denom = marked + sum(f.hardcoded_candidates for f in self.files)
        return (marked / denom) if denom else 1.0

    @property
    def counts_by_severity(self) -> dict[str, int]:
        out = dict.fromkeys(SEVERITY_RANK, 0)
        for finding in self.findings:
            out[finding.severity] += 1
        return out

    model_config = ConfigDict(frozen=True)


def scan_ui_file(path: Path) -> list[Finding]:
    """QT-UI-009 for user-visible ``notr`` strings, plus an embedded-image note."""
    try:
        form = ui_io.load(path)
    except (OSError, etree.XMLSyntaxError) as exc:
        return [
            Finding(
                rule_id="QT-UI-009",
                severity="info",
                message=f"Could not parse .ui file: {exc}",
                location=str(path),
            )
        ]
    findings: list[Finding] = []
    for s in form.strings:
        text = s.text.strip()
        # "@context.Name" strings are context markers, not labels.
        if (
            s.prop not in VISIBLE_PROPS
            or not text
            or text.startswith("@")
            or not s.notr
        ):
            continue
        findings.append(
            Finding(
                rule_id="QT-UI-009",
                severity="major",
                message=f"User-visible {s.prop} marked notr=\"true\": '{text[:_PREVIEW]}'",
                location=f"{path}:{s.line}",
                data={"widget": s.widget, "prop": s.prop},
            )
        )
    if form.image_count:
        findings.append(
            Finding(
                rule_id="QT-UI-009",
                severity="info",
                message=f"{form.image_count} embedded image(s); review for RTL mirroring.",
                location=str(path),
                data={"images": form.image_count},
            )
        )
    return findings


def _collect(repo: Path, include_ui: bool) -> tuple[list[Path], list[Path]]:
    """C++ and ``.ui`` paths under one file or directory."""
    if repo.is_file():
        return ([repo] if repo.suffix in CPP_EXTS else []), (
            [repo] if repo.suffix == ".ui" else []
        )
    cpp = [p for ext in CPP_EXTS for p in sorted(repo.rglob(f"*{ext}"))]
    return cpp, (sorted(repo.rglob("*.ui")) if include_ui else [])


def _scan_cpp(
    path: Path, engine: str, compile_commands: Path | None
) -> tuple[FileCoverage, list[Finding]]:
    """Heuristic pass, then clang per ``engine``.

    In ``clang`` a file whose AST is incomplete (QT-CLANG-012) falls back to
    its heuristic findings, so it never reads as clean.
    """
    coverage, found = scan_cpp_file(path)
    if engine == "heuristic" or (
        engine == "both" and not any(f.severity == "critical" for f in found)
    ):
        return coverage, found
    exact = scan_cpp_file_clang(path, compile_commands)
    degraded = any(f.rule_id == INCOMPLETE_RULE for f in exact)
    if engine == "clang" and not degraded:
        return coverage, exact
    return coverage, found + exact


def run(
    repos: list[Path],
    *,
    engine: str = "heuristic",
    include_ui: bool = True,
    compile_commands: Path | None = None,
) -> ScanReport:
    """Scan files or directories with ``engine`` in ``ENGINES``.

    Raises ``ValueError`` for an unknown engine, a missing path or an
    unreadable ``compile_commands`` file, and
    ``MissingDependencyError`` when ``clang``/``both`` is requested without
    the ``clang`` extra.
    """
    if engine not in ENGINES:
        raise ValueError(
            f"unknown scan engine {engine!r}; choose one of {', '.join(ENGINES)}"
        )
    if missing := [str(r) for r in repos if not Path(r).exists()]:
        raise ValueError(f"scan path(s) not found: {', '.join(missing)}")
    if engine != "heuristic" and not extra_installed("clang"):
        raise MissingDependencyError("clang", install_command("clang"))
    if compile_commands is not None:
        load_compile_commands(compile_commands)
    files: list[FileCoverage] = []
    findings: list[Finding] = []
    for repo in map(Path, repos):
        cpp_paths, ui_paths = _collect(repo, include_ui)
        for path in cpp_paths:
            coverage, found = _scan_cpp(path, engine, compile_commands)
            files.append(coverage)
            findings += found
        for path in ui_paths:
            findings += scan_ui_file(path)
    return ScanReport(
        repos=[str(r) for r in repos], engine=engine, files=files, findings=findings
    )
