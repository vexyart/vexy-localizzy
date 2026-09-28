# this_file: tests/memory/test_direct.py
"""Direct memory lookup: verbatim sources, match classes, plurals, precedence."""

import unicodedata
from pathlib import Path

import pytest

from vexy_localizzy.catalog import PluralForms, Unit
from vexy_localizzy.formats.ts import load as load_ts
from vexy_localizzy.memory import DirectMemory, normalize_source
from vexy_localizzy.tmx import read_tmx

FIXTURES = Path(__file__).parent.parent / "fixtures" / "memory"
UI_DE = FIXTURES / "ui-de.tmx"


@pytest.fixture
def memory() -> DirectMemory:
    return DirectMemory.load([UI_DE], source_lang="en", target_lang="de_DE")


def unit(source, context="", key="k", **extra) -> Unit:
    return Unit(key=key, context=context, source=source, **extra)


def numerus(source, context, forms) -> Unit:
    plural = PluralForms(indexing="index", forms={str(i): "" for i in range(forms)})
    return unit(source, context, plural=plural)


def write_tmx(path: Path, rows) -> Path:
    body = "".join(
        f'<tu tuid="{c}|{s}"><prop type="x-context">{c}</prop>'
        f'<tuv xml:lang="en"><seg>{s}</seg></tuv>'
        f'<tuv xml:lang="de"><seg>{t}</seg></tuv></tu>'
        for c, s, t in rows
    )
    path.write_text(
        f'<tmx version="1.4"><header srclang="en"/><body>{body}</body></tmx>'
    )
    return path


def test_load_when_tu_lacks_target_variant_then_skips_and_counts(memory):
    summary = memory.summary()
    assert summary["tus_total"] == 16, summary
    assert (summary["tus_loaded"], summary["tus_skipped"]) == (15, 1), summary
    assert summary["languages"][str(UI_DE)] == {"source": "en", "target": "de"}
    assert len(summary["sha256"][str(UI_DE)]) == 64


def test_lookup_when_context_matches_then_context_beats_source(memory):
    hit = memory.lookup(unit("Save", "Menu"))
    assert hit is not None and hit.match == "context", hit
    assert hit.values == {"scalar": "Sichern"}
    assert hit.entries[0].tuid == "Menu|Save" and hit.entries[0].ordinal == 1


def test_lookup_when_targets_identical_across_contexts_then_source_hit(memory):
    hit = memory.lookup(unit("Open", "Elsewhere"))
    assert hit is not None and hit.match == "source", hit
    assert hit.values == {"scalar": "Öffnen"}
    assert len(hit.entries) == 2


def test_lookup_when_targets_conflict_then_none_and_finding(memory):
    assert memory.lookup(unit("Form", "Elsewhere", key="form")) is None
    (finding,) = memory.conflicts
    assert finding.rule_id == "MEMORY-CONFLICT" and finding.severity == "info"
    assert finding.unit_key == "form"
    assert finding.data["tuids"] == ["Panel|Form", "Tool|Form"]


def test_lookup_when_comment_differs_then_disambiguation_selects(memory):
    hit = memory.lookup(unit("Kern", "Panel", disambiguation="noun"))
    assert hit is not None and hit.match == "context"
    assert hit.values == {"scalar": "Unterschneidung"}


def test_lookup_when_message_id_matches_then_id_class(memory):
    hit = memory.lookup(unit("Open file", "Files", key="id:file.open"))
    assert hit is not None and hit.match == "id", hit
    assert hit.values == {"scalar": "Datei öffnen (per id)"}


def test_lookup_when_two_form_numerus_then_hit_keyed_by_form(memory):
    hit = memory.lookup(numerus("%n file(s)", "Files", 2))
    assert hit is not None and hit.match == "context", hit
    assert hit.values == {"0": "%n Datei", "1": "%n Dateien"}


def test_lookup_when_three_form_catalog_against_two_form_memory_then_no_hit(memory):
    assert memory.lookup(numerus("%n file(s)", "Files", 3)) is None
    assert [f.rule_id for f in memory.conflicts] == ["MEMORY-PLURAL-SHAPE"]


def test_lookup_when_scalar_source_equals_numerus_source_then_pools_stay_apart(
    memory,
):
    assert memory.lookup(unit("%n file(s)", "Files")) is None
    assert memory.conflicts == []


def test_lookup_when_crlf_or_nfd_then_matches_normalized_source(memory):
    crlf = memory.lookup(unit("Line one\r\nLine two", "Text"))
    assert crlf is not None and crlf.values == {"scalar": "Zeile eins\nZeile zwei"}
    nfd = memory.lookup(unit(unicodedata.normalize("NFD", "Größe"), "Metrics"))
    assert nfd is not None and nfd.values == {"scalar": "Größe"}


def test_lookup_when_trailing_colon_differs_then_no_cross_match(memory):
    hit = memory.lookup(unit("Form:", "Elsewhere"))
    assert hit is not None and hit.values == {"scalar": "Form:"}
    assert all(e.source == "Form:" for e in hit.entries)
    assert normalize_source("Form") != normalize_source("Form:")


def test_lookup_when_length_variants_then_never_hits_and_counts(memory):
    assert memory.lookup(unit("Save", "Menu", variants=["Sichern", "S."])) is None
    assert memory.summary()["variant_units_skipped"] == 1


def test_lookup_text_when_no_context_then_source_tier(memory):
    assert memory.lookup_text("Open") == "Öffnen"
    assert memory.lookup_text("Save") is None
    assert memory.lookup_text("Save", context="Dialog") == "Speichern"
    assert memory.lookup_text("Kern", context="Panel", comment="verb") == (
        "Unterschneiden"
    )


def test_lookup_when_equal_class_in_two_files_then_first_file_wins(tmp_path):
    first = write_tmx(tmp_path / "a.tmx", [("Menu", "Quit", "Beenden")])
    second = write_tmx(tmp_path / "b.tmx", [("Menu", "Quit", "Verlassen")])
    memory = DirectMemory.load([first, second], source_lang="en", target_lang="de")
    hit = memory.lookup(unit("Quit", "Menu"))
    assert hit is not None and hit.values == {"scalar": "Beenden"}
    assert hit.entries[0].memory == str(first)
    assert memory.conflicts == []


def test_lookup_when_later_file_has_higher_class_then_it_wins(tmp_path):
    first = write_tmx(tmp_path / "a.tmx", [("Other", "Quit", "Beenden")])
    second = write_tmx(tmp_path / "b.tmx", [("Menu", "Quit", "Verlassen")])
    memory = DirectMemory.load([first, second], source_lang="en", target_lang="de")
    hit = memory.lookup(unit("Quit", "Menu"))
    assert hit is not None and hit.match == "context"
    assert hit.values == {"scalar": "Verlassen"}


def test_lookup_when_ts_catalog_then_units_hit_with_native_form_count(memory):
    catalog = load_ts(FIXTURES / "app_de.ts")
    hits = {u.source: memory.lookup(u) for u in catalog.units}
    assert hits["Save"].match == "context" and hits["Save"].values == {
        "scalar": "Sichern"
    }
    assert hits["%n file(s)"].values == {"0": "%n Datei", "1": "%n Dateien"}
    assert hits["Open file"].match == "id"


def test_load_when_es_mx_catalog_then_reads_es_419():
    memory = DirectMemory.load(
        [FIXTURES / "ui-es419.tmx"], source_lang="en", target_lang="es_MX"
    )
    assert memory.lookup_text("Save", context="Menu") == "Guardar"
    languages = memory.summary()["languages"]
    assert list(languages.values()) == [{"source": "en", "target": "es-419"}]


def test_read_tmx_when_notes_then_retains_tu_and_tuv_notes_not_header():
    units = list(read_tmx(FIXTURES / "core-de.tmx"))
    assert units[0].notes == ("Adjusting space between glyph pairs.",)
    assert units[0].segments[1].notes == ("Established term.",)
    assert units[0].segments[0].notes == ()
    assert all("header" not in n for u in units for n in u.notes)
