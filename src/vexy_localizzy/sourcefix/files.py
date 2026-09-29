# this_file: src/vexy_localizzy/sourcefix/files.py
"""Stage all source/catalog outputs before replacing any file."""

import hashlib
import os
import stat
import tempfile
from pathlib import Path

from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.sourcefix.progress import report


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def confined(path: Path, root: Path) -> Path:
    path = path.resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path outside source root: {path}")
    return path


def commit(outputs: dict[Path, bytes], originals: dict[Path, bytes | None]) -> None:
    """Preserve modes, detect intervening edits and roll back handled write failures.

    Each replacement is atomic; the batch is not power-loss atomic. Originals
    remain in memory until the complete batch has succeeded.
    """
    report(f"Staging {len(outputs)} output files on disk")
    staged = {}
    replaced = []
    modes = {}
    try:
        for path, content in outputs.items():
            modes[path] = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
            fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
            staged[path] = Path(temporary)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            staged[path].chmod(modes[path])
        report("Checking originals for concurrent edits before writing")
        for path, original in originals.items():
            current = path.read_bytes() if path.exists() else None
            if current != original:
                raise ValueError(f"File changed while preparing edits: {path}")
        report(f"Writing {len(staged)} validated files", state="writing")
        for path, temporary in staged.items():
            os.replace(temporary, path)
            replaced.append(path)
        report("All files written", state="committed")
    except BaseException:
        report(
            "Restoring originals after an interrupted or failed write",
            state="restoring",
        )
        for path in reversed(replaced):
            if originals[path] is None:
                path.unlink()
            else:
                atomic_write(path, originals[path])
                path.chmod(modes[path])
        report("Originals restored", state="restored")
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)
