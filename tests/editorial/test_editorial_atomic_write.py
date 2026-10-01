# this_file: tests/editorial/test_editorial_atomic_write.py
"""``formats.document.atomic_write``: permission bits survive a replacement."""

import os
import stat

import pytest

from vexy_localizzy.formats import document
from vexy_localizzy.formats.document import atomic_write


def _mode(path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _umask() -> int:
    current = os.umask(0)
    os.umask(current)
    return current


@pytest.mark.parametrize("mode", [0o640, 0o755, 0o600])
def test_atomic_write_when_file_exists_then_mode_kept(tmp_path, mode):
    path = tmp_path / "file.txt"
    path.write_bytes(b"old")
    path.chmod(mode)
    atomic_write(path, b"new")
    assert path.read_bytes() == b"new", "content replaced"
    assert _mode(path) == mode, f"mode {oct(_mode(path))} != {oct(mode)}"


def test_atomic_write_when_file_new_then_umask_default(tmp_path):
    path = tmp_path / "new.txt"
    atomic_write(path, b"x")
    assert _mode(path) == 0o666 & ~_umask(), oct(_mode(path))


def test_atomic_write_when_write_fails_then_no_temporary_left(tmp_path, monkeypatch):
    path = tmp_path / "file.txt"
    path.write_bytes(b"old")
    monkeypatch.setattr(
        document.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("full"))
    )
    with pytest.raises(OSError, match="full"):
        atomic_write(path, b"new")
    assert path.read_bytes() == b"old", "destination untouched"
    assert [p.name for p in tmp_path.iterdir()] == ["file.txt"], "temporary removed"
