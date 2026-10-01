# this_file: src/vexy_localizzy/qt/lrelease.py
"""Compile Qt TS catalogs to binary ``.qm`` files with the native ``lrelease``."""

from pathlib import Path

from vexy_localizzy.external import require_tool
from vexy_localizzy.qt.process import run_tool

LRELEASE_TIMEOUT = 300  # seconds per catalog


def run(catalogs: list[Path], *, out_dir: Path | None = None) -> list[Path]:
    """Release each ``.ts`` to a sibling ``.qm`` (or one in ``out_dir``).

    Raises ``ValueError`` when two catalogs would write the same ``.qm`` in
    ``out_dir``, ``MissingDependencyError`` without ``lrelease`` and
    ``RuntimeError`` when a catalog fails to compile or the tool times out.
    """
    if out_dir is not None:
        stems = [Path(c).stem for c in catalogs]
        if clashes := sorted({s for s in stems if stems.count(s) > 1}):
            raise ValueError(
                f"catalogs would overwrite each other in {out_dir}: {', '.join(clashes)}"
            )
    tool = require_tool("lrelease")
    written: list[Path] = []
    for catalog in catalogs:
        src = Path(catalog).resolve()
        dest_dir = Path(out_dir) if out_dir is not None else src.parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{src.stem}.qm"
        run_tool(
            f"lrelease ({src.name})",
            [tool, str(src), "-qm", str(dest)],
            timeout=LRELEASE_TIMEOUT,
        )
        written.append(dest)
    return written
