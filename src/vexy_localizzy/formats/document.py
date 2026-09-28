# this_file: src/vexy_localizzy/formats/document.py
"""Self-contained original document snapshots for lossless catalog JSON."""

import base64
import hashlib
import os
import tempfile
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator


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
    """Replace a destination only after its complete output has been prepared."""
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
