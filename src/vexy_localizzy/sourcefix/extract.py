# this_file: src/vexy_localizzy/sourcefix/extract.py
"""Ask Qt for current contexts and locations instead of trusting stale TS lines."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from vexy_localizzy.sourcefix.catalog import Catalog, Key


def current_locations(
    paths: set[Path], root: Path, lupdate: str
) -> dict[Key, list[tuple[Path, int | None]]]:
    executable = shutil.which(lupdate)
    if executable is None:
        raise ValueError(
            "Qt lupdate is required to apply source fixes; install Qt Linguist tools or pass --lupdate /path/to/lupdate"
        )
    with tempfile.TemporaryDirectory(prefix="localizzy-source-fix-") as directory:
        out = Path(directory).resolve() / "current.ts"
        command = [
            executable,
            *(str(p) for p in sorted(paths)),
            "-I",
            str(root),
            "-locations",
            "absolute",
            "-no-obsolete",
            "-source-language",
            "en_US",
            "-target-language",
            "en_US",
            "-ts",
            str(out),
        ]
        result = subprocess.run(
            command, cwd=root, capture_output=True, text=True, timeout=120
        )
        if result.returncode:
            raise ValueError(f"Qt extraction failed: {result.stderr}")
        return {
            key: [(p, n) for p, n in refs if p in paths]
            for key, refs in Catalog(out).locations().items()
        }
