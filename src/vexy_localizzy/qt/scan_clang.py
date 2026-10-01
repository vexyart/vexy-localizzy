# this_file: src/vexy_localizzy/qt/scan_clang.py
"""AST-level C++ pass using libclang (the optional ``clang`` extra).

Detects QT-TR-002 (non-literal ``tr()`` argument) and QT-CTX-001 (missing
``Q_OBJECT``) with ``confidence="exact"``. ``clang.cindex`` is imported inside
the function so this module, and ``qt.scan``, load without libclang.

A translation unit with error diagnostics (typically Qt headers not found)
has unresolved ``tr`` calls and unknown base classes, so walking it would read
as clean. Such a file yields only QT-CLANG-012 and no AST findings; ``qt.scan``
then reports the heuristic findings for it instead.
"""

from pathlib import Path

from vexy_localizzy.catalog import Finding
from vexy_localizzy.external import (
    MissingDependencyError,
    extra_installed,
    install_command,
)
from vexy_localizzy.qt.compile_db import (
    DEFAULT_ARGS,
    HEADER_ARGS,
    compile_args_for,
    load_compile_commands,
)
from vexy_localizzy.qt.scan_scope import QOBJECT_BASES

__all__ = [
    "DEFAULT_ARGS",
    "HEADER_ARGS",
    "INCOMPLETE_RULE",
    "load_compile_commands",
    "scan_cpp_file_clang",
]

_TR_NAMES = ("tr", "translate")
INCOMPLETE_RULE = "QT-CLANG-012"
_ERROR_SEVERITY = 3  # clang.cindex.Diagnostic.Error; Fatal is 4


def _unwrap(cursor, wrapper):
    """Skip implicit-conversion wrappers, e.g. array-to-pointer around a literal."""
    while cursor.kind == wrapper:
        children = list(cursor.get_children())
        if len(children) != 1:
            break
        cursor = children[0]
    return cursor


def _diagnostic_where(path: Path, diagnostic) -> str:
    loc = diagnostic.location
    return f"{loc.file.name}:{loc.line}:{loc.column}" if loc.file else str(path)


def _incomplete(path: Path, problem: str, where: str) -> Finding:
    """QT-CLANG-012: the AST is missing or unreliable; the file must not read as clean."""
    return Finding(
        rule_id=INCOMPLETE_RULE,
        severity="major",
        message=(
            f"clang AST is incomplete ({problem} at {where}); "
            "pass --compile-commands so clang finds the include paths. "
            "Heuristic findings are reported for this file instead."
        ),
        location=str(path),
        data={"diagnostic": problem, "at": where},
    )


def scan_cpp_file_clang(
    path: Path, compile_commands: Path | None = None
) -> list[Finding]:
    """Parse one C++ file with libclang and report QT-TR-002 / QT-CTX-001.

    A file that libclang cannot load, or whose parse has error diagnostics,
    returns only one QT-CLANG-012 finding.
    Raises ``MissingDependencyError`` when the ``clang`` extra is absent.
    """
    if not extra_installed("clang"):
        raise MissingDependencyError("clang", install_command("clang"))
    import clang.cindex as cindex  # intentional lazy import: optional extra

    kinds = cindex.CursorKind
    index = cindex.Index.create()
    try:
        tu = index.parse(str(path), args=compile_args_for(path, compile_commands))
    except cindex.TranslationUnitLoadError as error:
        return [_incomplete(path, f"translation unit not loaded: {error}", str(path))]
    errors = [d for d in tu.diagnostics if d.severity >= _ERROR_SEVERITY]
    if errors:
        first = errors[0]
        return [_incomplete(path, first.spelling, _diagnostic_where(path, first))]
    findings: list[Finding] = []

    def location(cursor) -> str:
        loc = cursor.location
        return f"{loc.file.name if loc.file else path}:{loc.line}:{loc.column}"

    def is_tr_call(cursor) -> bool:
        return cursor.kind == kinds.CALL_EXPR and cursor.spelling in _TR_NAMES

    def check_tr(cursor) -> None:
        args = list(cursor.get_arguments())
        if not args:
            return
        first = _unwrap(args[0], kinds.UNEXPOSED_EXPR)
        literal = first.kind == kinds.STRING_LITERAL or (
            first.kind == kinds.CALL_EXPR and first.spelling == "QStringLiteral"
        )
        if literal:
            return
        findings.append(
            Finding(
                rule_id="QT-TR-002",
                severity="critical",
                message="tr()/translate() called with a non-literal argument (silent extraction failure) [clang].",
                location=location(cursor),
                data={"arg_kind": str(first.kind)},
            )
        )

    def check_class(cursor) -> None:
        bases = {
            child.spelling.split("::")[-1]
            for child in cursor.get_children()
            if child.kind == kinds.CXX_BASE_SPECIFIER
        }
        if not bases & set(QOBJECT_BASES):
            return
        has_tr = any(is_tr_call(c) for c in cursor.walk_preorder())
        has_qobject = any(tok.spelling == "Q_OBJECT" for tok in cursor.get_tokens())
        if not has_tr or has_qobject:
            return
        findings.append(
            Finding(
                rule_id="QT-CTX-001",
                severity="critical",
                message=f"Class '{cursor.spelling}' derives from a QObject base and calls tr() but lacks Q_OBJECT [clang].",
                location=location(cursor),
                data={"class": cursor.spelling},
            )
        )

    for cursor in tu.cursor.walk_preorder():
        if is_tr_call(cursor):
            check_tr(cursor)
        elif cursor.kind == kinds.CLASS_DECL:
            check_class(cursor)
    return findings
