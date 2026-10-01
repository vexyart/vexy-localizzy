# this_file: src/vexy_localizzy/qt/compile_db.py
"""Clang arguments per source file, from ``compile_commands.json`` or defaults.

Used by ``qt.scan_clang``; ``qt.scan`` calls ``load_compile_commands`` up front
so a missing or malformed database is a ``ValueError`` before any scanning.
Relative ``file`` entries resolve against their ``directory``, which also
becomes clang's working directory so relative ``-I`` flags keep working.
"""

import functools
import json
import shlex
from pathlib import Path

DEFAULT_ARGS = ["-std=c++17", "-DQT_CORE_LIB"]
# libclang refuses to load a header as a translation unit unless told its language.
HEADER_SUFFIXES = (".h", ".hh", ".hpp", ".hxx")
HEADER_ARGS = ["-x", "c++-header"]
_DB_CACHE = 4  # compilation databases kept parsed
# Compiler flags that describe outputs, not how to parse the file.
_OUTPUT_FLAGS = ("-o", "-c", "-MF", "-MT", "-MD")
_FLAGS_WITH_VALUE = ("-o", "-MF", "-MT", "-MQ")


def _parse_args(args: list[str], sources: set[str]) -> list[str]:
    """Drop the compiler, output flags (with their values) and the source file."""
    kept: list[str] = []
    skip_next = False
    for arg in args[1:]:
        if skip_next:
            skip_next = False
        elif arg in _FLAGS_WITH_VALUE:
            skip_next = True
        elif not arg.startswith(_OUTPUT_FLAGS) and arg not in sources:
            kept.append(arg)
    return kept


def _default_args(path: Path) -> list[str]:
    """Fallback arguments; headers are parsed as C++ headers."""
    header = path.suffix.lower() in HEADER_SUFFIXES
    return HEADER_ARGS + DEFAULT_ARGS if header else DEFAULT_ARGS


def _entry_args(entry: object, db_dir: Path) -> tuple[str, list[str]]:
    """(resolved file, clang arguments) for one compilation-database entry."""
    if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
        raise ValueError(f"compile commands entry without a 'file': {entry!r}")
    directory = Path(entry.get("directory") or db_dir)
    file = (directory / entry["file"]).resolve()
    args = entry.get("arguments") or shlex.split(entry.get("command", ""))
    parsed = _parse_args(args, {entry["file"], str(file)}) or _default_args(file)
    # Relative -I and source paths in the entry are relative to its directory.
    return str(file), ["-working-directory", str(directory), *parsed]


@functools.lru_cache(maxsize=_DB_CACHE)
def _load_db(path: str, _mtime_ns: int) -> dict[str, list[str]]:
    try:
        db = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"cannot read compile commands {path}: {error}") from error
    if not isinstance(db, list):
        raise ValueError(f"compile commands {path} must be a JSON array")
    found: dict[str, list[str]] = {}
    for entry in db:
        file, args = _entry_args(entry, Path(path).parent)
        found.setdefault(file, args)
    return found


def load_compile_commands(path: Path) -> dict[str, list[str]]:
    """Map each resolved source file to its clang arguments.

    Raises ``ValueError`` for a missing file, invalid JSON or a malformed entry.
    Cached per file and modification time, so a scan reads it once.
    """
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"compile commands file not found: {path}")
    return _load_db(str(path.resolve()), path.stat().st_mtime_ns)


def compile_args_for(path: Path, compile_commands: Path | None) -> list[str]:
    """Clang arguments for ``path`` from ``compile_commands.json``, else defaults."""
    if compile_commands is None:
        return _default_args(path)
    found = load_compile_commands(compile_commands).get(str(path.resolve()))
    return list(found) if found else _default_args(path)
