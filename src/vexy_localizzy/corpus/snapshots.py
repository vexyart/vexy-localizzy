# this_file: src/vexy_localizzy/corpus/snapshots.py
"""Content-addressed compressed source snapshots for recoverable provenance."""

import gzip
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

from vexy_localizzy.inventory import CHUNK_BYTES, _identity


def adopt_snapshot(path: Path, digest: str, directory: Path) -> Path:
    """Copy and verify an exported raw snapshot into the receiving corpus."""
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Invalid lineage snapshot hash")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{digest}.tmx.gz"
    if target.exists():
        with gzip.open(target, "rb") as existing:
            if hashlib.file_digest(existing, "sha256").hexdigest() != digest:
                raise ValueError("Corrupt lineage source snapshot")
        return target
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as output:
            temporary = Path(output.name)
            with path.open("rb") as source:
                shutil.copyfileobj(source, output, CHUNK_BYTES)
            output.flush()
            os.fsync(output.fileno())
        with gzip.open(temporary, "rb") as raw:
            if hashlib.file_digest(raw, "sha256").hexdigest() != digest:
                raise ValueError("Corrupt lineage source snapshot")
        os.link(temporary, target)
        return target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def snapshot(path: Path, directory: Path) -> tuple[str, Path]:
    """Copy stable bytes once; verify existing snapshots before trusting them."""
    before = path.stat()
    directory.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as output:
            temporary = Path(output.name)
            digest = hashlib.sha256()
            with (
                path.open("rb") as source,
                gzip.GzipFile(
                    filename="", mode="wb", fileobj=output, compresslevel=1, mtime=0
                ) as compressed,
            ):
                while chunk := source.read(CHUNK_BYTES):
                    digest.update(chunk)
                    compressed.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if _identity(before) != _identity(path.stat()):
            raise ValueError("Source changed while creating its snapshot")
        key = digest.hexdigest()
        target = directory / f"{key}.tmx.gz"
        try:
            os.link(temporary, target)
        except FileExistsError:
            with gzip.open(target, "rb") as existing:
                if hashlib.file_digest(existing, "sha256").hexdigest() != key:
                    raise ValueError("Existing source snapshot is corrupt") from None
        return key, target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
