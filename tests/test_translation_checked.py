# this_file: tests/test_translation_checked.py
"""Additional acceptance rules must participate in fallback and cache identity."""

from collections import Counter

import pytest
from test_translation_cache import cache
from translation_fixtures import batch, reply

from vexy_localizzy.translation_cache import TranslationPending


def test_checked_when_policy_changes_then_isolate_selection_and_preserve_owner(
    tmp_path,
):
    calls = Counter()

    def request(model, value):
        calls[model] += 1
        return reply(model, value)

    def require_alternate(value, result):
        if result.requested_model != "alternate":
            raise ValueError("Additional acceptance rule")

    with cache(tmp_path / "cache.sqlite", request) as store:
        original = store.identity, store.validate
        assert store.translate(batch()).requested_model == "preferred"
        for _ in range(2):
            result = store.translate_checked(
                batch(), validation_identity="extra:1", validate=require_alternate
            )
            assert result.requested_model == "alternate"
        assert (store.identity, store.validate) == original
        assert store.translate(batch()).requested_model == "preferred"
        assert store.db.execute("SELECT COUNT(*) FROM selections").fetchone()[0] == 2
    assert calls == {"preferred": 4, "alternate": 1}


def test_checked_when_additional_validator_accepts_then_original_rules_still_apply(
    tmp_path,
):
    def request(model, value):
        result = reply(model, value)
        if model == "preferred":
            result.targets["first"] = "Missing placeholder"
        return result

    with cache(tmp_path / "cache.sqlite", request) as store:
        result = store.translate_checked(
            batch(), validation_identity="extra:1", validate=lambda *_: None
        )
        assert result.requested_model == "alternate"


def test_checked_when_validator_mutates_then_no_result_is_cached(tmp_path):
    def mutate(value, result):
        result.targets["first"] = "Modified %1"

    with cache(tmp_path / "cache.sqlite", reply) as store:
        with pytest.raises(TranslationPending):
            store.translate_checked(
                batch(), validation_identity="extra:1", validate=mutate
            )
        assert store.db.execute("SELECT COUNT(*) FROM responses").fetchone()[0] == 0


@pytest.mark.parametrize("identity", [None, "", "  "])
def test_checked_when_identity_invalid_then_no_requests(tmp_path, identity):
    with cache(
        tmp_path / "cache.sqlite", lambda *_: pytest.fail("No requests")
    ) as store:
        with pytest.raises(ValueError, match="identity"):
            store.translate_checked(
                batch(), validation_identity=identity, validate=lambda *_: None
            )
