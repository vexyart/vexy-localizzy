# this_file: src/vexy_localizzy/formats/document.py
"""Self-contained original document snapshots for lossless catalog JSON."""

import base64
import hashlib
import os
import secrets
import stat
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

NEW_FILE_MODE = 0o666
TEMPORARY_ATTEMPTS = 100


class SourceDocument(BaseModel):
    """Original bytes, verified independently of their editable projection."""

    format: Literal["ts", "po", "xliff", "android", "i18next", "tmx"]
    content_base64: str
    sha256: str
    model_config = ConfigDict(frozen=True, extra="forbid")

    @property
    def content(self) -> bytes:
        return base64.b64decode(self.content_base64, validate=True)

    @model_validator(mode="after")
    def verify_content(self) -> Self:
        if hashlib.sha256(self.content).hexdigest() != self.sha256:
            raise ValueError("Original document checksum mismatch")
        return self

    @classmethod
    def capture(cls, raw: bytes, format: str) -> Self:
        return cls(
            format=format,
            content_base64=base64.b64encode(raw).decode("ascii"),
            sha256=hashlib.sha256(raw).hexdigest(),
        )


def atomic_write(path: Path, content: bytes) -> None:
    """Replace a destination only after its complete output has been prepared.

    The replacement keeps the destination's permission bits; a new file gets the
    umask default, because the temporary file is created with mode 0o666 (not
    ``mkstemp``'s 0o600) and the process umask applies to it.
    """
    path = Path(path)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    fd, temporary = _create_sibling(path)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _create_sibling(path: Path) -> tuple[int, Path]:
    """Open a new hidden file next to ``path``; the umask applies to its mode."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    for _ in range(TEMPORARY_ATTEMPTS):
        temporary = path.parent / f".{path.name}.{secrets.token_hex(8)}.tmp"
        try:
            return os.open(temporary, flags, NEW_FILE_MODE), temporary
        except FileExistsError:
            continue
    raise FileExistsError(f"Could not create a temporary file next to {path}")
