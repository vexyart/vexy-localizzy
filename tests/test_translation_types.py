# this_file: tests/test_translation_types.py
"""Exact numbered coverage and full input identity for translation requests."""

import json

import pytest
from pydantic import ValidationError
from translation_fixtures import batch

from vexy_localizzy.translate.types import TranslationBatch, parse_targets


def test_translation_payload_requires_exact_message_ids():
    result = parse_targets(
        '[{"id":"second","target":"Linia bazowa"},{"id":"first","target":"Przesuń %1."}]',
        batch(),
    )
    assert result == {"first": "Przesuń %1.", "second": "Linia bazowa"}


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [{"id": "first", "target": "Good"}],
        [{"id": "first", "target": "Good"}, {"id": "first", "target": "Other"}],
        [{"id": "first", "target": "Good"}, {"id": "extra", "target": "Other"}],
        [{"id": "first", "target": "Good"}, {"id": "second", "target": " "}],
        [
            {"id": "first", "target": "Good", "source": "Changed"},
            {"id": "second", "target": "Other"},
        ],
    ],
)
def test_bad_output_is_never_a_completed_translation(rows):
    with pytest.raises(ValueError):
        parse_targets(json.dumps(rows), batch())


@pytest.mark.parametrize("change", ["duplicate", "empty", "too_many", "same_locale"])
def test_bad_translation_input_rejected_before_transport(change):
    data = batch().model_dump()
    if change == "duplicate":
        data["items"][1]["id"] = "first"
    elif change == "empty":
        data["items"] = []
    elif change == "too_many":
        data["items"] = data["items"] * 51
    else:
        data["target_lang"] = "en"
    with pytest.raises(ValidationError):
        TranslationBatch.model_validate(data)


@pytest.mark.parametrize(
    "text",
    [
        '[{"id":"unexpected","id":"first","target":"Good"},{"id":"second","target":"Fine"}]',
        '[{"id":"first","target":"Bad","target":"Good"},{"id":"second","target":"Fine"}]',
    ],
)
def test_duplicate_json_fields_are_rejected(text):
    with pytest.raises(ValueError, match="Duplicate"):
        parse_targets(text, batch())


def test_item_when_no_length_constraint_then_original_cache_payload_unchanged():
    from vexy_localizzy.translate.types import TranslationItem

    item = TranslationItem(id="m", source="Open")
    assert "max_length" not in item.model_dump(), (
        "Default optional constraints must not invalidate prior batch identities"
    )
    assert (
        TranslationItem(id="m", source="Open", max_length=4).model_dump()["max_length"]
        == 4
    )
