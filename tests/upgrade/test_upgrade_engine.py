# this_file: tests/upgrade/test_upgrade_engine.py
"""Tier 9 through a fake request callable: no network, batches recorded."""

from upgrade_helpers import (
    APPROVED,
    FRESH,
    FakeEngine,
    by_source,
    context,
    doc,
    fake_cache,
    glossary,
    message,
    new_message,
)

from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.upgrade import UpgradeOptions, upgrade_ts


def run(tmp_path, engine, fresh=None, approved=None, **kw):
    with fake_cache(tmp_path / "cache.sqlite", engine) as cache:
        return upgrade_ts(
            fresh or FRESH.read_bytes(),
            approved or APPROVED.read_bytes(),
            cache=cache,
            options=UpgradeOptions(batch_size=1),
            **kw,
        )


def test_engine_when_no_hit_then_machine_with_only_relevant_glossary(tmp_path):
    engine = FakeEngine()
    result = run(tmp_path, engine, glossary=glossary())
    outcome = by_source(result.report)["Open the kerning class editor"]
    assert outcome.category == "machine"
    assert outcome.state == "unfinished"
    assert outcome.model == "synthetic-model-reported"
    assert outcome.glossary_terms == ["kerning class"]
    batch = next(
        b
        for b in engine.batches
        if b.items[0].source == "Open the kerning class editor"
    )
    assert batch.glossary == {"kerning class": "Kerning-Klasse"}, (
        "only this batch's terms"
    )
    element = new_message(result.new_bytes, "Open the kerning class editor")
    assert (
        xml.text(element.find("translation"), "") == "DE Open the kerning class editor"
    )
    assert element.find("translation").get("type") == "unfinished"


def test_engine_when_fuzzy_tie_then_machine(tmp_path):
    result = run(tmp_path, FakeEngine())
    assert by_source(result.report)["Snap to grid X"].category == "machine"


def test_engine_when_memory_or_exact_then_never_sent(tmp_path):
    engine = FakeEngine()
    run(tmp_path, engine, glossary=glossary())
    sent = {item.source for batch in engine.batches for item in batch.items}
    assert not sent & {"Open", "Glyph", "Save as…", "Metrics"}


def test_engine_when_numerus_flip_then_approved_text_sent_as_example(tmp_path):
    engine = FakeEngine()
    result = run(tmp_path, engine)
    outcome = by_source(result.report)["%n master(s)"]
    assert outcome.category == "shape_changed"
    assert outcome.filled, "the engine filled the flipped message"
    batch = next(b for b in engine.batches if b.items[0].source == "%n master(s)")
    assert [e.target for e in batch.examples] == ["%n Master"]
    assert batch.examples[0].provenance == "approved:Counts|%n master(s)"
    forms = [
        f for f in new_message(result.new_bytes, "%n master(s)").iter("numerusform")
    ]
    assert len(forms) == 2 and all(xml.text(f, "") for f in forms)


def test_engine_when_provider_fails_then_pending_and_unfilled(tmp_path):
    fresh = doc(context("C", message("Brand new text", unfinished=True)))
    approved = doc(context("C", message("Other", "Anderes")))
    result = run(tmp_path, FakeEngine(fail=True), fresh=fresh, approved=approved)
    outcome = result.report.messages[0]
    assert outcome.category == "pending"
    assert result.report.unfilled == 1
