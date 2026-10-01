# this_file: src/vexy_localizzy/editorial/commit.py
"""Write the corrected catalog and its ledger together, or neither.

Every output is first rendered in full to a hidden sibling of its destination,
so an unwritable ledger directory or a serializer error fails before anything
is replaced. Only then are the destinations replaced in order; if a later
replacement fails, the earlier ones get their original bytes back. Outputs
that would overwrite an input are refused up front.
"""

import os
import secrets
import stat
from collections.abc import Callable
from pathlib import Path

from vexy_localizzy.formats.document import atomic_write

Render = Callable[[Path], None]


def refuse_overwrite(outputs: dict[str, Path], inputs: dict[str, Path | None]) -> None:
    """ValueError when an output path resolves to an input (``out == input``)."""
    resolved = {name: Path(p).resolve() for name, p in inputs.items() if p is not None}
    for out_name, out in outputs.items():
        target = Path(out).resolve()
        for in_name, path in resolved.items():
            if target == path:
                raise ValueError(f"{out_name} {out} is the same file as {in_name}")


def _sibling(path: Path) -> Path:
    return path.parent / f".{path.name}.{secrets.token_hex(8)}.staged"


def _stage(dest: Path, staged: Path, render: Render) -> None:
    """Render ``dest``'s new content at ``staged``, with ``dest``'s permission bits."""
    render(staged)
    if dest.exists():
        os.chmod(staged, stat.S_IMODE(dest.stat().st_mode))


def _restore(dest: Path, original: bytes | None) -> None:
    if original is None:
        dest.unlink(missing_ok=True)
    else:
        atomic_write(dest, original)


def _replace_all(staged: list[tuple[Path, Path]]) -> None:
    """Move every staged file into place; undo the earlier moves if one fails."""
    originals = {
        dest: dest.read_bytes() if dest.exists() else None for dest, _ in staged
    }
    done = []
    try:
        for dest, temporary in staged:
            os.replace(temporary, dest)
            done.append(dest)
    except BaseException:
        for dest in reversed(done):
            _restore(dest, originals[dest])
        raise


def commit_files(outputs: list[tuple[Path, Render]]) -> None:
    """Render every output, then replace the destinations as one unit."""
    staged: list[tuple[Path, Path]] = []
    try:
        for dest, render in outputs:
            dest = Path(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            staged.append((dest, _sibling(dest)))
            _stage(dest, staged[-1][1], render)
        _replace_all(staged)
    finally:
        for _, temporary in staged:
            temporary.unlink(missing_ok=True)
