# this_file: src/vexy_localizzy/external.py
"""External-tool discovery and optional-extra detection.

Qt Linguist binaries (``lupdate``, ``lrelease``, ``lconvert``) and Translate
Toolkit's ``pofilter`` are discovered, never bundled. Optional Python extras are
detected by import probe. Nothing here installs anything; ``localizzy doctor``
prints the command for a person to run. Referenced by ``doctor``, ``qt`` and
``qa.layers``.
"""

import importlib.util
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

PACKAGE = "vexy-localizzy"
QT_BINARIES = ("lupdate", "lrelease", "lconvert")
TT_BINARIES = ("pofilter",)
VERSION_TIMEOUT = 5  # seconds; a version probe must never stall a command

# Optional extra -> the import name that proves it is installed.
EXTRA_IMPORTS = {
    "llm": "openai",
    "sources": "fluent",
    "embeddings": "numpy",
    "clustering": "sklearn",
    "translation": "abersetz",
    "review": "fastapi",
    "clang": "clang",
    "pofilter": "translate",
}


class MissingDependencyError(RuntimeError):
    """A command needs an extra or an external tool that is not installed."""

    def __init__(self, what: str, how: str) -> None:
        super().__init__(f"Missing dependency: {what}. Install with: {how}")
        self.what = what
        self.how = how


@dataclass(frozen=True)
class ToolInfo:
    name: str
    path: str | None
    version: str | None

    @property
    def found(self) -> bool:
        return self.path is not None


def _qt_search_dirs() -> list[Path]:
    """Well-known Qt bin directories to probe after ``$PATH``."""
    dirs: list[Path] = []
    if qt_dir := os.environ.get("QT_DIR"):
        dirs.append(Path(qt_dir) / "bin")
    if platform.system() == "Darwin":
        for formula in ("qt@5", "qt"):
            try:
                prefix = subprocess.run(
                    ["brew", "--prefix", formula],
                    capture_output=True,
                    text=True,
                    timeout=VERSION_TIMEOUT,
                )
            except (FileNotFoundError, subprocess.SubprocessError):
                break
            if prefix.returncode == 0 and prefix.stdout.strip():
                dirs.append(Path(prefix.stdout.strip()) / "bin")
    else:
        dirs += [
            Path("/usr/lib/qt5/bin"),
            Path("/usr/lib/x86_64-linux-gnu/qt5/bin"),
            Path("/usr/lib/qt6/bin"),
        ]
    return [d for d in dirs if d.is_dir()]


def _tool_version(path: str) -> str | None:
    for flag in ("-version", "--version"):
        try:
            result = subprocess.run(
                [path, flag], capture_output=True, text=True, timeout=VERSION_TIMEOUT
            )
        except (subprocess.SubprocessError, OSError):
            continue
        lines = (result.stdout or result.stderr).strip().splitlines()
        if lines and not lines[0].lower().startswith("usage"):
            return lines[0]
    return None


def find_tool(name: str) -> ToolInfo:
    """Locate an external binary: ``$PATH`` first, then well-known Qt directories."""
    path = shutil.which(name)
    if path is None and name in QT_BINARIES:
        for directory in _qt_search_dirs():
            candidate = directory / name
            if candidate.exists():
                path = str(candidate)
                break
    return ToolInfo(name=name, path=path, version=_tool_version(path) if path else None)


def require_tool(name: str) -> str:
    """Return the path of a required external binary or raise with an install hint."""
    tool = find_tool(name)
    if tool.path is None:
        hint = os_install_hint() if name in QT_BINARIES else install_command("pofilter")
        raise MissingDependencyError(name, hint)
    return tool.path


def extra_installed(extra: str) -> bool:
    """True when the import that proves an extra is installed can be found."""
    module = EXTRA_IMPORTS.get(extra)
    return module is not None and importlib.util.find_spec(module) is not None


def install_command(extra: str) -> str:
    """The command that provisions an extra; nothing runs it implicitly."""
    return f"uv pip install '{PACKAGE}[{extra}]'"


def os_install_hint() -> str:
    """Operating-system hint for the Qt Linguist tools."""
    if platform.system() == "Darwin":
        return "brew install qt"
    return "apt-get install qttools5-dev-tools"
