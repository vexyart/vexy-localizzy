# this_file: src/vexy_localizzy/qa/printf.py
"""Delegate C printf argument/type validation to GNU gettext instead of reimplementing it."""

import os
import subprocess
import tempfile
from pathlib import Path

import polib


def printf_error(source: str, target: str, *, executable: str = "msgfmt") -> str | None:
    """Check one pair with native positional/star/length-modifier support.

    A missing executable or timeout is an operational failure, never a clean QA
    result. This optional check is only called by an explicitly selected policy.
    """
    with tempfile.TemporaryDirectory(prefix="localizzy-printf-") as directory:
        path = Path(directory) / "pair.po"
        po = polib.POFile()
        po.metadata = {"Content-Type": "text/plain; charset=UTF-8"}
        po.append(polib.POEntry(msgid=source, msgstr=target, flags=["c-format"]))
        po.save(path)
        result = subprocess.run(
            [executable, "--check-format", "-o", os.devnull, str(path)],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "LC_ALL": "C"},
        )
        if result.returncode:
            return result.stderr.replace(str(path), "translation")[:2000]
        # msgfmt skips both sides when the source format is malformed. A known
        # invalid target must fail, proving that this source was actually checked.
        po[0].msgstr = "%"
        po.save(path)
        probe = subprocess.run(
            [executable, "--check-format", "-o", os.devnull, str(path)],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "LC_ALL": "C"},
        )
        if probe.returncode == 0:
            return "Source printf syntax is invalid or native format validation was skipped."
        if probe.returncode != 1:
            raise RuntimeError("Native printf validation probe failed unexpectedly")
    return None
