# this_file: tests/test_review_paths.py
"""Catalogs and sidecars must never alias before a lock can truncate its file."""

import os

import pytest
from review_fixtures import store

from vexy_localizzy.review.store import ReviewStore


@pytest.mark.parametrize("suffix", [".review.lock", ".review.jsonl"])
def test_store_when_sidecar_is_another_catalog_then_reject_without_changes(
    tmp_path, suffix
):
    store(tmp_path)
    original = (tmp_path / "catalog.json").read_bytes()
    other = tmp_path / ("catalog.json" + suffix)
    other.write_bytes(original)
    with pytest.raises(ValueError, match="collid|alias"):
        ReviewStore(tmp_path, {"first": "catalog.json", "second": other.name})
    assert other.read_bytes() == original


@pytest.mark.parametrize("link", ["symlink", "hardlink"])
def test_open_when_lock_is_linked_to_catalog_then_reject_before_truncation(
    tmp_path, link
):
    saved = store(tmp_path)
    path = tmp_path / "catalog.json"
    original = path.read_bytes()
    lock = tmp_path / "catalog.json.review.lock"
    if link == "symlink":
        lock.symlink_to(path)
    else:
        os.link(path, lock)
    with pytest.raises(ValueError, match="collid|alias"):
        saved.open("main")
    assert path.read_bytes() == original
