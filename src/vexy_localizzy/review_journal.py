# this_file: src/vexy_localizzy/review_journal.py
"""Append-only intent/completion journal; recovery checks hashes and never replays."""

import os

from vexy_localizzy.review_types import JOURNAL_ROW, Completion, Intent, ReviewConflict


def sync_directory(path):
    """Persist directory entries; an unsupported filesystem fails explicitly."""
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def append(path, record):
    """Persist a complete journal row before proceeding to the next write step."""
    with path.open("ab") as stream:
        stream.write(record.model_dump_json().encode() + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def reconcile(path, revision):
    """Under the catalog lock, close a pending intent only if disk proves its state."""
    if not path.exists():
        return
    pending, seen = None, set()
    with path.open("rb") as stream:
        for line in stream:
            try:
                if not line.endswith(b"\n"):
                    raise ValueError("Incomplete journal row")
                record = JOURNAL_ROW.validate_json(line)
            except ValueError as error:
                raise ReviewConflict(
                    "Invalid review journal; preserve it for recovery"
                ) from error
            if isinstance(record, Intent):
                if (
                    pending is not None
                    or record.id in seen
                    or record.old != record.edit.revision
                    or record.old == record.new
                ):
                    raise ReviewConflict("Invalid review journal intent sequence")
                pending = record
                seen.add(record.id)
            else:
                if pending is None or record.id != pending.id:
                    raise ReviewConflict("Invalid review journal completion sequence")
                pending = None
    if pending is None:
        return
    if revision == pending.old:
        status = "unapplied"
    elif revision == pending.new:
        status = "applied"
    else:
        raise ReviewConflict(
            "Incomplete review edit conflicts with an external catalog change"
        )
    sync_directory(path.parent)
    append(path, Completion(id=pending.id, status=status))
