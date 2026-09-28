# this_file: tests/test_review_durability.py
"""Assert the ordering of durable journal and catalog directory entries."""

import os
import stat

from review_fixtures import edit, store


def test_save_when_committing_then_sync_directories_before_completion(
    tmp_path, monkeypatch
):
    saved = store(tmp_path)
    revision = saved.open("main").revision
    events = []
    fsync, replace = os.fsync, os.replace

    def sync(fd):
        events.append("directory" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file")
        return fsync(fd)

    def rename(source, target):
        events.append("replace")
        return replace(source, target)

    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(os, "replace", rename)
    saved.save("main", edit(revision))
    assert events == [
        "file",
        "directory",
        "file",
        "replace",
        "directory",
        "file",
        "directory",
    ], "Intent creation and catalog replacement must be durable before completion"
