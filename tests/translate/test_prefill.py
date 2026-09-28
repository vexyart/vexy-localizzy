# this_file: tests/translate/test_prefill.py
"""translate_catalog(prefilled=...): memory and kept dispositions, cache=None."""

import pytest

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.catalog_translation import translate_catalog
from vexy_localizzy.catalog_translation_types import InvariantApproval, Prefill
from vexy_localizzy.qa.text import validate_batch
from vexy_localizzy.translation_cache import TranslationCache
from vexy_localizzy.translation_types import TranslationResult

PLURALS = {"0": "", "1": ""}


def template(**overrides) -> Catalog:
    units = [
        Unit(key="save", context="Menu", source="Save", target=""),
        Unit(key="move", context="Menu", source="Move %1", target=""),
        Unit(
            key="files",
            context="Files",
            source="%n file(s)",
            plural=PluralForms(indexing="index", forms={"0": "", "1": ""}),
        ),
        Unit(key="empty", context="C", source="", target="keep"),
        Unit(key="old", context="C", source="Old", target="alt", state="vanished"),
    ]
    units = [overrides.get(u.key, u) for u in units]
    return Catalog(source_lang="en", target_lang="de", units=units)


def memory(values, state="translated", status="memory") -> Prefill:
    return Prefill(values=values, state=state, status=status, reason="ui.tmx#x")


def status(result) -> dict[str, str]:
    return {d.key: d.status for d in result.dispositions}


def test_translate_catalog_when_everything_prefilled_and_no_cache_then_ready():
    result = translate_catalog(
        template(),
        None,
        plural_forms=PLURALS,
        prefilled={
            "save": memory({"scalar": "Sichern"}),
            "move": memory({"scalar": "%1 verschieben"}, state="needs_review"),
            "files": memory({"0": "%n Datei", "1": "%n Dateien"}),
        },
    )
    assert status(result) == {
        "save": "memory",
        "move": "memory",
        "files": "memory",
        "empty": "excluded_empty",
        "old": "excluded_vanished",
    }, "prefilled units must carry the memory disposition"
    units = {u.key: u for u in result.catalog.units}
    assert units["save"].target == "Sichern" and units["save"].state == "translated"
    assert units["move"].state == "needs_review"
    assert units["files"].plural.forms == {"0": "%n Datei", "1": "%n Dateien"}
    assert result.ready and result.pending_messages == 0
    assert result.dispositions[0].reason == "ui.tmx#x"


def test_translate_catalog_when_no_cache_and_units_remain_then_pending_without_calls():
    result = translate_catalog(
        template(),
        None,
        plural_forms=PLURALS,
        prefilled={"save": memory({"scalar": "Sichern"})},
    )
    assert status(result)["move"] == "pending"
    assert status(result)["files"] == "pending"
    assert result.pending_messages == 2 and not result.ready
    assert result.providers == [], "no provider may be called without a cache"


def test_translate_catalog_when_prefilled_then_engine_gets_only_the_rest(tmp_path):
    seen = []

    def request(model, batch):
        seen.extend(item.source for item in batch.items)
        return TranslationResult(
            targets={i.id: "DE " + i.source for i in batch.items},
            requested_model=model,
            reported_model=model,
        )

    with TranslationCache(
        tmp_path / "c.sqlite",
        models=("m",),
        request=request,
        endpoint_identity="fake",
        engine_identity="fake:1",
        validation_identity="v:1",
        validate=validate_batch,
    ) as cache:
        result = translate_catalog(
            template(),
            cache,
            plural_forms=PLURALS,
            prefilled={"save": memory({"scalar": "Sichern"})},
        )
    assert "Save" not in seen, "a prefilled unit must not reach the provider"
    assert status(result)["save"] == "memory"
    assert status(result)["move"] == "candidate"
    assert result.ready


def test_translate_catalog_when_kept_targets_present_then_empty_check_skipped():
    existing = Unit(
        key="save",
        context="Menu",
        source="Save",
        target="Speichern",
        state="translated",
    )
    result = translate_catalog(
        template(save=existing),
        None,
        plural_forms=PLURALS,
        prefilled={"save": memory({"scalar": "Speichern"}, status="kept")},
    )
    assert status(result)["save"] == "kept"
    assert result.catalog.units[0].target == "Speichern"


def test_translate_catalog_when_unprefilled_target_present_then_still_rejected():
    existing = Unit(key="save", context="Menu", source="Save", target="Speichern")
    with pytest.raises(ValueError, match="empty eligible targets"):
        translate_catalog(template(save=existing), None, plural_forms=PLURALS)


def test_translate_catalog_when_prefill_unchanged_text_then_not_blocking():
    result = translate_catalog(
        template(),
        None,
        plural_forms=PLURALS,
        prefilled={"save": memory({"scalar": "Save"})},
    )
    assert status(result)["save"] == "memory"
    assert any(f.rule_id == "TARGET-UNCHANGED" for f in result.findings)


@pytest.mark.parametrize(
    ("prefill", "message"),
    [
        ({"move": memory({"scalar": "Verschieben"})}, "fails shape or QA"),
        ({"files": memory({"0": "%n Datei"})}, "shape differs"),
        ({"files": memory({"scalar": "x"})}, "shape differs"),
        ({"nope": memory({"scalar": "x"})}, "Unknown prefilled"),
        ({"old": memory({"scalar": "x"})}, "Excluded message"),
    ],
)
def test_translate_catalog_when_prefill_invalid_then_raise(prefill, message):
    with pytest.raises(ValueError, match=message):
        translate_catalog(template(), None, plural_forms=PLURALS, prefilled=prefill)


def test_translate_catalog_when_prefilled_and_invariant_then_raise():
    unit = template().units[0]
    approval = InvariantApproval(source_hash=unit.source_hash, reason="brand")
    with pytest.raises(ValueError, match="both prefilled and invariant"):
        translate_catalog(
            template(),
            None,
            plural_forms=PLURALS,
            invariants={"save": approval},
            prefilled={"save": memory({"scalar": "Sichern"})},
        )


def test_prefill_when_state_or_status_unknown_then_reject():
    with pytest.raises(ValueError):
        Prefill(values={}, state="untranslated", status="memory")
    with pytest.raises(ValueError):
        Prefill(values={}, state="translated", status="engine")
