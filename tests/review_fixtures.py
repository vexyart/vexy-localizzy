# this_file: tests/review_fixtures.py
"""Revision checks, native form edits and crash reconciliation for review storage."""

from vexy_localizzy.catalog import Catalog, Unit
from vexy_localizzy.formats import json_io
from vexy_localizzy.review_store import ReviewEdit, ReviewStore


def store(tmp_path):
    path = tmp_path / "catalog.json"
    json_io.dump(
        Catalog(
            source_lang="en",
            target_lang="pl",
            units=[
                Unit(
                    key="open",
                    context="Menu",
                    source="Open %1",
                    target="Otwórz %1",
                    state="needs_review",
                )
            ],
        ),
        path,
    )
    return ReviewStore(tmp_path, {"main": "catalog.json"})


def edit(revision, target="Otwórz plik %1", action="draft"):
    return ReviewEdit(
        key="open", revision=revision, targets={"scalar": target}, action=action
    )
