# this_file: tests/test_review_store.py
"""Revision checks, native form edits and crash reconciliation for review storage."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from review_fixtures import edit, store

from vexy_localizzy.formats import json_io
from vexy_localizzy.review.store import ReviewConflict, ReviewEdit, ReviewStore


def test_save_when_valid_then_reopen_preserves_draft_and_approval(tmp_path):
    saved = store(tmp_path)
    initial = saved.open("main")
    changed = saved.save("main", edit(initial.revision))
    assert changed.revision != initial.revision
    assert changed.catalog.units[0].state == "needs_review"
    approved = saved.save("main", edit(changed.revision, action="approve"))
    assert approved.catalog.units[0].state == "approved"
    reopened = ReviewStore(tmp_path, {"main": "catalog.json"}).open("main")
    assert reopened == approved
    rows = [
        json.loads(line)
        for line in (tmp_path / "catalog.json.review.jsonl").read_text().splitlines()
    ]
    assert [r["kind"] for r in rows] == ["intent", "complete", "intent", "complete"]


def test_save_when_stale_or_invalid_then_no_catalog_or_journal_changes(tmp_path):
    saved = store(tmp_path)
    original = saved.open("main")
    raw = (tmp_path / "catalog.json").read_bytes()
    for request in (
        edit("0" * 64),
        edit(original.revision, "Missing argument"),
        edit(original.revision).model_copy(update={"targets": {"other": "Wrong"}}),
    ):
        with pytest.raises((ReviewConflict, ValueError)):
            saved.save("main", request)
        assert (tmp_path / "catalog.json").read_bytes() == raw
        assert not (tmp_path / "catalog.json.review.jsonl").exists()


def test_save_when_concurrent_revision_then_exactly_one_writer_wins(tmp_path):
    saved = store(tmp_path)
    revision = saved.open("main").revision

    def attempt(target):
        try:
            return saved.save("main", edit(revision, target)).catalog.units[0].target
        except ReviewConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["Pierwszy %1", "Drugi %1"]))
    assert results.count("conflict") == 1
    assert saved.open("main").catalog.units[0].target in results


@pytest.mark.parametrize("after_replace", [False, True])
def test_reopen_when_interrupted_then_reconcile_without_replaying(
    tmp_path, monkeypatch, after_replace
):
    import vexy_localizzy.review.store as module

    saved = store(tmp_path)
    before = saved.open("main")
    original = module.atomic_write

    def interrupted(path, content):
        if after_replace:
            original(path, content)
        raise OSError("Simulated interruption")

    with monkeypatch.context() as patch:
        patch.setattr(module, "atomic_write", interrupted)
        with pytest.raises(OSError, match="interruption"):
            saved.save("main", edit(before.revision))
    current = saved.open("main")
    assert (current.revision != before.revision) == after_replace
    rows = [
        json.loads(line)
        for line in (tmp_path / "catalog.json.review.jsonl").read_text().splitlines()
    ]
    assert rows[-1]["status"] == ("applied" if after_replace else "unapplied")
    assert saved.open("main") == current


def test_reopen_when_incomplete_intent_and_external_change_then_explicit_conflict(
    tmp_path, monkeypatch
):
    import vexy_localizzy.review.store as module

    saved = store(tmp_path)
    before = saved.open("main")
    with monkeypatch.context() as patch:
        patch.setattr(
            module,
            "atomic_write",
            lambda *_: (_ for _ in ()).throw(OSError("Interrupted")),
        )
        with pytest.raises(OSError):
            saved.save("main", edit(before.revision))
    path = tmp_path / "catalog.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ReviewConflict, match="external"):
        saved.open("main")


def test_store_when_configured_path_escapes_root_then_reject(tmp_path):
    with pytest.raises(ValueError, match="root"):
        ReviewStore(tmp_path, {"main": "../outside.json"})
    saved = store(tmp_path)
    with pytest.raises(KeyError):
        saved.open("../catalog.json")


def test_save_when_existing_variant_alias_invalid_then_reject_before_reconstruction(
    tmp_path,
):
    saved = store(tmp_path)
    path = tmp_path / "catalog.json"
    current = json_io.load(path)
    broken = current.units[0].model_copy(
        update={"target": "Alias %1", "variants": ["Other %1", "Short %1"]}
    )
    json_io.dump(current.model_copy(update={"units": [broken]}), path)
    revision = saved.open("main").revision
    request = ReviewEdit(
        key="open",
        revision=revision,
        targets={"variant:0": "Long %1", "variant:1": "Short %1"},
    )
    with pytest.raises(ValueError, match="shape"):
        saved.save("main", request)


def test_save_when_unchanged_approval_then_require_and_record_reason(tmp_path):
    saved = store(tmp_path)
    revision = saved.open("main").revision
    request = edit(revision, "Open %1", action="approve")
    with pytest.raises(ValueError, match="TARGET-UNCHANGED"):
        saved.save("main", request)
    changed = saved.save(
        "main", request.model_copy(update={"reason": "Reviewed product label"})
    )
    assert changed.catalog.units[0].state == "approved"
    journal = (tmp_path / "catalog.json.review.jsonl").read_text()
    assert "Reviewed product label" in journal


def test_reopen_when_journal_truncated_then_no_automatic_replay(tmp_path):
    saved = store(tmp_path)
    path = tmp_path / "catalog.json"
    raw = path.read_bytes()
    journal = tmp_path / "catalog.json.review.jsonl"
    journal.write_bytes(b'{"kind":"intent"')
    with pytest.raises(ReviewConflict, match="journal"):
        saved.open("main")
    assert path.read_bytes() == raw
    assert journal.read_bytes() == b'{"kind":"intent"'


def test_open_when_catalog_symlink_changes_to_outside_then_reject(tmp_path):
    from tempfile import TemporaryDirectory

    saved = store(tmp_path)
    path = tmp_path / "catalog.json"
    raw = path.read_bytes()
    with TemporaryDirectory() as directory:
        outside = Path(directory) / "outside.json"
        outside.write_bytes(raw)
        path.unlink()
        path.symlink_to(outside)
        with pytest.raises(ValueError, match="root"):
            saved.open("main")
