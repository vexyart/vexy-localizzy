# this_file: tests/test_vocab.py
"""The example vocabulary corpus loads, validates, exports and reports stats."""

from pathlib import Path

import pytest

from vexy_localizzy import vocab
from vexy_localizzy.cli import checks
from vexy_localizzy.formats import json_io

CORPUS = Path(__file__).resolve().parents[1] / "examples/vocabulary/translations.js"


def test_load_when_example_corpus_then_units_plurals_and_disambiguation():
    catalog = vocab.load(CORPUS)
    keys = {unit.key for unit in catalog.units}
    assert len(catalog.units) > 40, "the corpus is a real vocabulary, not a stub"
    assert {"menu.file.open", "msg.selectedGlyphsCount"} <= keys, sorted(keys)[:5]
    plural = [unit.key for unit in catalog.units if unit.plural]
    assert "msg.selectedGlyphsCount" in plural, plural
    assert any(unit.disambiguation for unit in catalog.units), (
        "disambig keys carry hints"
    )


def test_load_when_locale_given_then_bilingual():
    german = {unit.key: unit.target for unit in vocab.load(CORPUS, locale="de").units}
    assert german["menu.file.open"] == "Schriftart &öffnen...", german["menu.file.open"]


def test_validate_when_example_corpus_then_clean():
    assert vocab.validate(CORPUS) == [], "the golden corpus must stay valid"


def test_validate_when_context_or_other_missing_then_findings(tmp_path):
    corpus = tmp_path / "corpus.json"
    corpus.write_text(
        '{"a": {"en": "Open"}, "b": {"en": "{n, plural, one {x}}", "context": "c"}}'
    )
    rules = {finding.rule_id for finding in vocab.validate(corpus)}
    assert rules == {"VOCAB-CONTEXT", "VOCAB-PLURAL"}, rules
    with pytest.raises(SystemExit) as caught:
        checks.vocab("validate", str(corpus), format="json")
    assert caught.value.code == 1, "findings exit 1"


def test_export_when_written_then_canonical_json_round_trips(tmp_path):
    out = tmp_path / "vocab.json"
    catalog = vocab.export(out, CORPUS)
    assert len(json_io.load(out).units) == len(catalog.units), "export must round-trip"


def test_stats_when_example_corpus_then_families_and_coverage():
    stats = vocab.stats(CORPUS)
    assert stats.total > 40 and "menu" in stats.families, stats
    assert stats.plural_units >= 1 and stats.disambiguation_units >= 1, stats
    assert set(stats.locale_coverage) >= {"de", "fr", "ja"}, stats.locale_coverage


def test_vocab_command_when_action_unknown_then_usage_exit():
    with pytest.raises(SystemExit) as caught:
        checks.vocab("explode", str(CORPUS))
    assert caught.value.code == 2, "an unknown action is a usage error"


def test_compare_when_candidate_differs_then_rate_and_pairs(tmp_path):
    reference = vocab.load(CORPUS, locale="de")
    units = [unit for unit in reference.units if unit.target]
    changed = units[0].model_copy(update={"target": "anders"})
    candidate = reference.model_copy(update={"units": [changed, *units[2:]]})
    result = vocab.compare(CORPUS, candidate, "de")
    assert result["total"] == len(units) and result["exact"] == len(units) - 2, result
    assert result["missing"] == [units[1].key], "a key the candidate lacks is missing"
    assert result["different"][0]["candidate"] == "anders", result["different"]
    with pytest.raises(ValueError, match="no 'xx' references"):
        vocab.compare(CORPUS, candidate, "xx")


def test_vocab_command_when_compare_below_threshold_then_exit_1(tmp_path):
    out = tmp_path / "de.json"
    vocab.export(out, CORPUS, locale="de")
    result = checks.vocab("compare", str(CORPUS), locale="de", candidate=str(out))
    assert result["exact_rate"] == 1.0, "the corpus matches its own export"
    source_only = tmp_path / "en.json"
    vocab.export(source_only, CORPUS)
    with pytest.raises(SystemExit) as caught:
        checks.vocab(
            "compare",
            str(CORPUS),
            locale="de",
            candidate=str(source_only),
            min_exact=0.5,
        )
    assert caught.value.code == 1, "an untranslated candidate fails the threshold"


def test_vocab_command_when_flat_round_trip_then_compare_accepts_mapping(tmp_path):
    source = tmp_path / "en.json"
    result = checks.vocab("export", str(CORPUS), out=str(source), flat=True)
    assert result["units"] > 40, "the flat export holds every source text"
    german = tmp_path / "de.json"
    checks.vocab("export", str(CORPUS), out=str(german), flat=True, locale="de")
    score = checks.vocab("compare", str(CORPUS), locale="de", candidate=str(german))
    assert score["exact_rate"] == 1.0 and not score["missing"], score


def test_load_raw_when_js_has_urls_comments_and_trailing_commas(tmp_path):
    corpus = tmp_path / "corpus.js"
    corpus.write_text(
        'const v = {\n  // a comment\n  "a": {"en": "See https://example.org/x", '
        '"de": "Siehe https://example.org/x", "notes": "n", "context": "c",},\n};\n'
    )
    raw = vocab.load_raw(corpus)
    assert raw["a"]["en"] == "See https://example.org/x", "// inside a string survives"
    assert vocab.available_locales(corpus) == ["de"], "only language tags are locales"
