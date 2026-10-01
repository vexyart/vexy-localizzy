# this_file: src/vexy_localizzy/qt/process.py
"""Run a Qt Linguist binary with a deadline and a readable failure message.

``qt.lupdate`` and ``qt.lrelease`` share this so a hung or failing tool always
surfaces as ``RuntimeError`` carrying the tool's own stderr.
"""

import subprocess
from pathlib import Path

ERROR_TAIL = 2000  # characters of tool output kept in an error message


def _tail(output: str | bytes | None) -> str:
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")
    return (output or "").strip()[-ERROR_TAIL:]


def run_tool(
    name: str, command: list[str], *, timeout: float, cwd: Path | None = None
) -> str:
    """Run ``command``; return stdout, or raise ``RuntimeError`` on failure or timeout."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd is not None else None,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"{name} timed out after {timeout} s: {_tail(exc.stderr)}"
        ) from exc
    if result.returncode != 0:
        detail = _tail(result.stderr) or _tail(result.stdout)
        raise RuntimeError(
            f"{name} failed with exit code {result.returncode}: {detail}"
        )
    return result.stdout
