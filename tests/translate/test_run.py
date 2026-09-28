# this_file: tests/translate/test_run.py
"""translate_file: kept targets, memory classes, QA gate, glossary context, provenance."""

import json

import pytest
from translate_fixtures import (
    CORE_DE,
    GERMAN_TS,
    SOURCE_TS,
    FakeProvider,
    needs_abersetz,
    tmx,
    tu,
    ui_memory,
    write,
)

from vexy_localizzy.catalog import Catalog, Unit
from vexy_localizzy.formats import ts
from vexy_localizzy.memory import DirectMemory, Glossary
from vexy_localizzy.qa.text import TextPolicy
from vexy_localizzy.translate import (
    EngineSpec,
    MemoryPolicy,
    memory_prefill,
    open_cache,
    translate_file,
)
from vexy_localizzy.translate.engine import abersetz_request, engine_identity
from vexy_localizzy.translate.run import same_language
from vexy_localizzy.translate.types import TranslationBatch, TranslationItem

ENGINE = EngineSpec(endpoint="http://fake.invalid/v1", models=("m1", "m2"))


def run_new_language(tmp_path, provider=None, **options):
    source = write(tmp_path / "app.ts", SOURCE_TS)
    options.setdefault("out", tmp_path / "app_de.ts")
    report = translate_file(
        source,
        target="de",
        direct_memories=[ui_memory(tmp_path)],
        glossary_memories=[CORE_DE],
        engine=ENGINE if provider else None,
        cache_path=tmp_path / "cache.sqlite",
        request=provider,
        **options,
    )
    return report, {u.key: u for u in ts.load(options["out"]).units}


def by_source(report_units, units):
    return {units[row.key].source: row for row in report_units}


@needs_abersetz
def test_translate_file_when_memory_hits_then_written_and_never_sent(tmp_path):
    provider = FakeProvider()
    report, units = run_new_language(tmp_path, provider)
    rows = by_source(report.units, units)
    assert rows["Save"].origin == "memory" and rows["Save"].match == "context"
    assert rows["%n file(s)"].match == "context"
    assert rows["Kerning"].match == "term"
    sent = provider.sources
    for source in ("Save", "Open", "Kerning", "%n file(s)"):
        assert source not in sent, f"{source} was answered by memory"
    units_by_source = {u.source: u for u in units.values()}
    assert units_by_source["Save"].target == "Sichern"
    assert units_by_source["Save"].state == "translated", "context hit is finished"
    assert units_by_source["Kerning"].target == "Unterschneidung"
    assert units_by_source["%n file(s)"].plural.forms == {
        "0": "%n Datei",
        "1": "%n Dateien",
    }


@needs_abersetz
def test_translate_file_when_source_only_hit_then_unfinished(tmp_path):
    report, units = run_new_language(tmp_path, FakeProvider())
    rows = by_source(report.units, units)
    assert rows["Open"].match == "source"
    assert set(rows["Open"].tuids) == {"Toolbar|Open", "Dialog|Open"}
    unit = next(u for u in units.values() if u.source == "Open")
    assert unit.target == "Öffnen" and unit.state == "untranslated"
    assert (
        b'<translation type="unfinished">\xc3\x96ffnen</translation>'
        in (tmp_path / "app_de.ts").read_bytes()
    )


@needs_abersetz
def test_translate_file_when_memory_hit_fails_qa_then_engine_translates(tmp_path):
    provider = FakeProvider()
    report, units = run_new_language(tmp_path, provider)
    assert "Move %1" in provider.sources
    rows = by_source(report.units, units)
    assert rows["Move %1"].origin == "engine"
    rejected = [f for f in report.findings if f.rule_id == "MEMORY-QA-REJECT"]
    assert len(rejected) == 1 and "PH-MISMATCH" in rejected[0].message
    assert report.counts["memory_rejected_qa"] == 1


@needs_abersetz
def test_translate_file_when_batch_sent_then_glossary_has_only_its_terms_sorted(
    tmp_path,
):
    provider = FakeProvider()
    report, units = run_new_language(tmp_path, provider)
    assert len(provider.batches) == 1
    glossary = provider.batches[0].glossary
    assert list(glossary) == ["glyph", "kerning"], "only occurring terms, sorted"
    assert glossary == {"glyph": "Glyphe", "kerning": "Unterschneidung"}
    rows = by_source(report.units, units)
    assert rows["Glyph kerning for %1"].glossary_terms == ("glyph", "kerning")
    assert rows["Move %1"].glossary_terms == ()
    assert rows["Move %1"].requested_model == "m1"
    assert rows["Move %1"].reported_model == "m1-reported"
    assert rows["Move %1"].request_sha256


@needs_abersetz
def test_translate_file_when_run_twice_then_second_run_served_from_cache(tmp_path):
    first = FakeProvider()
    run_new_language(tmp_path, first)
    before = (tmp_path / "app_de.ts").read_bytes()
    second = FakeProvider()
    report, _ = run_new_language(tmp_path, second)
    assert first.batches, "the first run must call the provider"
    assert second.batches == [], "identical batches must come from the cache"
    assert (tmp_path / "app_de.ts").read_bytes() == before
    assert report.counts["engine"] == 2


@needs_abersetz
def test_translate_file_when_counted_then_sum_is_eligible_plus_excluded(tmp_path):
    report, units = run_new_language(tmp_path, FakeProvider())
    classes = ("kept", "memory_id", "memory_context", "memory_source", "memory_term")
    total = sum(report.counts[k] for k in (*classes, "engine", "pending", "excluded"))
    assert total == len(units) == len(report.units) == 8
    assert report.counts["excluded"] == 2
    assert report.counts == {
        "kept": 0,
        "memory_id": 0,
        "memory_context": 2,
        "memory_source": 1,
        "memory_term": 1,
        "engine": 2,
        "pending": 0,
        "excluded": 2,
        "memory_rejected_qa": 1,
        "memory_conflict": 0,
    }
    assert report.ready


def test_translate_file_when_memory_only_then_pending_without_network(tmp_path):
    report, units = run_new_language(tmp_path)
    assert report.counts["pending"] == 2 and report.counts["engine"] == 0
    assert not report.ready
    rows = by_source(report.units, units)
    assert rows["Move %1"].origin == "pending"


@needs_abersetz
def test_translate_file_when_same_language_then_existing_translations_kept(tmp_path):
    source = write(tmp_path / "de.ts", GERMAN_TS)
    memory = tmx(tmp_path / "m.tmx", tu("Menu", "Save", "Sichern"))
    provider = FakeProvider()
    report = translate_file(
        source,
        target="de",
        out=source,
        direct_memories=[memory],
        engine=ENGINE,
        cache_path=tmp_path / "c.sqlite",
        request=provider,
    )
    assert provider.sources == ["Quit"], "kept and untouched units are never sent"
    assert report.target_lang == "de_DE"
    expected = GERMAN_TS.replace(
        '<translation type="unfinished"></translation>',
        '<translation type="unfinished">DE Quit</translation>',
    )
    assert source.read_text(encoding="utf-8") == expected
    assert report.counts["kept"] == 3 and report.counts["engine"] == 1
    fail = [f for f in report.findings if f.rule_id == "KEPT-QA-FAIL"]
    assert [f.unit_key for f in fail] == ["Menu.close_1"]
    assert not report.ready, "an existing target failing QA blocks readiness"


@needs_abersetz
def test_translate_file_when_no_keep_existing_then_memory_and_engine_replace(
    tmp_path,
):
    source = write(tmp_path / "de.ts", GERMAN_TS)
    memory = tmx(tmp_path / "m.tmx", tu("Menu", "Save", "Sichern"))
    out = tmp_path / "out.ts"
    report = translate_file(
        source,
        target="de_DE",
        out=out,
        direct_memories=[memory],
        keep_existing=False,
        engine=ENGINE,
        cache_path=tmp_path / "cache.sqlite",
        request=FakeProvider(),
    )
    units = {u.source: u for u in ts.load(out).units}
    assert units["Save"].target == "Sichern"
    assert units["Open"].target == "DE Open"
    assert report.counts["kept"] == 0 and report.counts["engine"] == 3


@pytest.mark.parametrize("same_out", [False, True])
def test_translate_file_when_no_keep_existing_without_engine_then_refuses(
    tmp_path, same_out
):
    source = write(tmp_path / "de.ts", GERMAN_TS)
    out = source if same_out else tmp_path / "out.ts"
    with pytest.raises(ValueError, match="nokeep-existing"):
        translate_file(source, target="de_DE", out=out, keep_existing=False)
    assert source.read_text(encoding="utf-8") == GERMAN_TS
    assert same_out or not out.exists()


def test_translate_file_when_no_keep_existing_and_out_is_input_then_refuses(tmp_path):
    source = write(tmp_path / "de.ts", GERMAN_TS)
    with pytest.raises(ValueError, match="nokeep-existing"):
        translate_file(
            source,
            target="de_DE",
            out=source,
            keep_existing=False,
            engine=ENGINE,
            cache_path=tmp_path / "cache.sqlite",
            request=FakeProvider(),
        )
    assert source.read_text(encoding="utf-8") == GERMAN_TS


def test_translate_file_when_provenance_extra_then_origin_element_and_same_units(
    tmp_path,
):
    sidecar, _ = run_new_language(tmp_path, out=tmp_path / "plain.ts")
    extra, _ = run_new_language(tmp_path, out=tmp_path / "extra.ts", provenance="extra")
    plain = (tmp_path / "plain.ts").read_text(encoding="utf-8")
    marked = (tmp_path / "extra.ts").read_text(encoding="utf-8")
    assert "extra-localizzy-origin" not in plain, "sidecar mode adds no TS extras"
    assert (
        "<extra-localizzy-origin>memory:ui-de.tmx#Menu|Save;match=context"
        "</extra-localizzy-origin>" in marked
    )
    assert marked.count("<extra-localizzy-origin>") == 4
    assert ts.load(tmp_path / "extra.ts").units == ts.load(tmp_path / "plain.ts").units
    assert extra.counts == sidecar.counts


def test_translate_file_when_report_path_absent_then_sidecar_next_to_out(tmp_path):
    run_new_language(tmp_path)
    data = json.loads((tmp_path / "app_de.ts.localizzy.json").read_text())
    assert data["schema_id"] == "localizzy-translate/1"
    assert [m["role"] for m in data["memories"]] == ["direct", "glossary"]
    custom = tmp_path / "r.json"
    run_new_language(tmp_path, report=custom)
    assert json.loads(custom.read_text())["units"]


def test_translate_file_when_target_needs_three_forms_then_two_form_memory_misses(
    tmp_path,
):
    source = write(tmp_path / "app.ts", SOURCE_TS)
    memory = tmx(
        tmp_path / "pl.tmx",
        tu("Files", "%n file(s)", "%n plik", lang="pl", numerus_form="0"),
        tu("Files", "%n file(s)", "%n pliki", lang="pl", numerus_form="1"),
    )
    out = tmp_path / "pl.ts"
    report = translate_file(source, target="pl", out=out, direct_memories=[memory])
    unit = next(u for u in ts.load(out).units if u.plural is not None)
    assert unit.plural.forms == {"0": "", "1": "", "2": ""}, "Qt Polish has 3 forms"
    assert any(f.rule_id == "MEMORY-PLURAL-SHAPE" for f in report.findings)


def test_translate_file_when_output_is_input_in_another_language_then_refuse(
    tmp_path,
):
    source = write(tmp_path / "app.ts", SOURCE_TS)
    with pytest.raises(ValueError, match="overwrite the input"):
        translate_file(source, target="de", out=source)


def test_translate_file_when_finish_on_empty_then_hits_unfinished(tmp_path):
    report, units = run_new_language(
        tmp_path, policy=MemoryPolicy(finish_on=frozenset())
    )
    save = next(u for u in units.values() if u.source == "Save")
    assert save.state == "untranslated", "unfinished in TS"
    assert report.counts["memory_context"] == 2


def test_translate_file_when_source_class_unused_then_no_source_hits(tmp_path):
    report, _ = run_new_language(
        tmp_path, policy=MemoryPolicy(use=frozenset({"id", "context", "term"}))
    )
    assert report.counts["memory_source"] == 0 and report.counts["pending"] == 3


def test_memory_prefill_when_term_is_lowercase_then_capitalize_for_label():
    glossary = Glossary.load([CORE_DE], source_lang="en", target_lang="de")
    catalog = Catalog(
        source_lang="en",
        target_lang="de",
        units=[
            Unit(key="a", context="C", source="Kern", target=""),
            Unit(key="b", context="C", source="kern", target=""),
            Unit(key="c", context="C", source="&Kerning", target=""),
        ],
    )
    prefills, rows, findings = memory_prefill(
        catalog, direct=None, glossary=glossary, policy=MemoryPolicy(), qa=TextPolicy()
    )
    assert prefills["a"].values == {"scalar": "Unterschneiden"}
    assert prefills["b"].values == {"scalar": "unterschneiden"}
    assert "c" not in prefills, "a term without the accelerator fails the QA gate"
    assert [f.rule_id for f in findings] == ["MEMORY-QA-REJECT"]
    assert rows[0].memory == "core-de.tmx" and rows[0].tuids == ("term:kern",)


def test_memory_prefill_when_context_hit_and_term_then_context_wins(tmp_path):
    memory = DirectMemory.load(
        [tmx(tmp_path / "m.tmx", tu("C", "Kerning", "Kerning (UI)"))],
        source_lang="en",
        target_lang="de",
    )
    glossary = Glossary.load([CORE_DE], source_lang="en", target_lang="de")
    catalog = Catalog(
        source_lang="en",
        target_lang="de",
        units=[Unit(key="k", context="C", source="Kerning", target="")],
    )
    prefills, rows, _ = memory_prefill(
        catalog,
        direct=memory,
        glossary=glossary,
        policy=MemoryPolicy(),
        qa=TextPolicy(),
    )
    assert prefills["k"].values == {"scalar": "Kerning (UI)"}
    assert rows[0].match == "context"


@pytest.mark.parametrize(
    ("catalog", "wanted", "same"),
    [
        ("de_DE", "de", True),
        ("de", "de", True),
        ("es_MX", "es", True),
        ("de_DE", "de-AT", False),
        ("de", "de-DE", False),
        (None, "de", False),
        ("pt_BR", "pt", True),
    ],
)
def test_same_language_when_region_less_target_then_matches(catalog, wanted, same):
    assert same_language(catalog, wanted) is same


@needs_abersetz
def test_open_cache_when_first_model_fails_then_fallback_model_answers(tmp_path):
    calls = []

    def request(model, batch):
        calls.append(model)
        if model == "m1":
            raise ValueError("malformed")
        return FakeProvider()(model, batch)

    batch = TranslationBatch(
        source_lang="en",
        target_lang="de",
        items=[TranslationItem(id="a", source="Save")],
    )
    with open_cache(
        ENGINE, tmp_path / "sub" / "c.sqlite", validation_identity="v", request=request
    ) as cache:
        result = cache.translate(batch)
    assert calls == ["m1", "m1", "m1", "m2"], "three attempts, then the fallback"
    assert result.reported_model == "m2-reported"


def test_engine_identity_when_temperature_changes_then_identity_changes():
    pytest.importorskip("abersetz")
    from vexy_localizzy.translate.abersetz_transport import TRANSPORT_ID

    warm = ENGINE.model_copy(update={"temperature": 0.7})
    assert engine_identity(ENGINE).startswith(TRANSPORT_ID)
    assert engine_identity(ENGINE) != engine_identity(warm)


def test_abersetz_request_when_key_missing_then_config_error(monkeypatch):
    pytest.importorskip("abersetz")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        abersetz_request(ENGINE)


@pytest.mark.parametrize(
    ("catalog", "wanted"),
    [("sr_Latn", "sr"), ("zh_Hant_TW", "zh"), ("de_DE_1996", "de")],
)
def test_same_language_when_script_or_variant_differs_then_other_language(
    catalog, wanted
):
    assert not same_language(catalog, wanted)
    assert same_language("zh_Hant_TW", "zh-Hant")


PO = """msgid ""
msgstr ""
"Language: de\\n"
"Content-Type: text/plain; charset=UTF-8\\n"

msgctxt "Menu"
msgid "Save"
msgstr ""

msgctxt "Menu"
msgid "Open"
msgstr ""

msgctxt "Menu"
msgid "Quit"
msgstr "Beenden"
"""


def test_translate_file_when_po_catalog_then_converted_with_fuzzy_source_hit(
    tmp_path,
):
    source = write(tmp_path / "app.po", PO)
    out = tmp_path / "out.po"
    report = translate_file(
        source, target="de", out=out, direct_memories=[ui_memory(tmp_path)]
    )
    assert report.counts["kept"] == 1
    assert report.counts["memory_context"] == 1
    assert report.counts["memory_source"] == 1
    text = out.read_text(encoding="utf-8")
    assert 'msgid "Save"\nmsgstr "Sichern"' in text
    assert '#, fuzzy\nmsgctxt "Menu"\nmsgid "Open"\nmsgstr "Öffnen"' in text
    assert 'msgstr "Beenden"' in text


def test_translate_file_when_po_in_other_language_then_refuse(tmp_path):
    source = write(tmp_path / "app.po", PO)
    with pytest.raises(ValueError, match="Only TS catalogs"):
        translate_file(source, target="fr", out=tmp_path / "fr.po")


@pytest.mark.parametrize(
    ("memory_lang", "target", "text"),
    [("zh-Hans", "zh_TW", "保存"), ("pt-BR", "pt_PT", "Guardar BR")],
)
def test_translate_file_when_memory_is_other_script_or_portuguese_then_refuses(
    tmp_path, memory_lang, target, text
):
    catalog = write(tmp_path / "src.ts", SOURCE_TS)
    memory = tmx(tmp_path / "m.tmx", tu("Menu", "Save", text, lang=memory_lang))
    out = tmp_path / "out.ts"
    with pytest.raises(ValueError, match="pass --memory-lang"):
        translate_file(catalog, target=target, out=out, direct_memories=[memory])
    assert not out.exists(), "Nothing may be written when the memory language is wrong"


def test_translate_file_when_memory_lang_override_then_uses_other_variant(tmp_path):
    catalog = write(tmp_path / "src.ts", SOURCE_TS)
    memory = tmx(tmp_path / "m.tmx", tu("Menu", "Save", "保存", lang="zh-Hans"))
    report = translate_file(
        catalog,
        target="zh_TW",
        out=tmp_path / "out.ts",
        direct_memories=[memory],
        memory_lang="zh-Hans",
    )
    assert report.memories[0]["languages"][str(memory)]["target"] == "zh-Hans"


@pytest.mark.parametrize(
    ("policy", "finished"),
    [
        (MemoryPolicy(), False),
        (MemoryPolicy(finish_on=frozenset({"id", "context", "term"})), True),
    ],
)
def test_translate_file_when_glossary_term_hit_then_unfinished_by_default(
    tmp_path, policy, finished
):
    source = write(tmp_path / "app.ts", SOURCE_TS)
    out = tmp_path / "de.ts"
    report = translate_file(
        source, target="de", out=out, glossary_memories=[CORE_DE], policy=policy
    )
    rows = {row.key: row for row in report.units}
    units = {u.key: u for u in ts.load(out).units}
    terms = [key for key, row in rows.items() if row.match == "term"]
    assert terms, "the fixture must produce a term hit"
    assert {units[key].state == "translated" for key in terms} == {finished}, (
        "term hits ignore context, so they are written unfinished unless asked"
    )
