# this_file: tests/memory/test_glossary_json.py
"""Glossary JSON view: status filter, language codes, ordering and file errors."""

import json
from pathlib import Path

import pytest

from vexy_localizzy.memory.glossary_json import (
    build_glossary,
    memory_paths,
    read_terms,
    target_language,
    write_glossary_json,
)


def tu(source: str, target: str, status: str, lang: str) -> str:
    return (
        f'<tu><prop type="x-status">{status}</prop>'
        f'<tuv xml:lang="en"><seg>{source}</seg></tuv>'
        f'<tuv xml:lang="{lang}"><seg>{target}</seg></tuv></tu>'
    )


def tmx(path: Path, lang: str, *units: tuple[str, str, str]) -> Path:
    body = "".join(tu(s, t, status, lang) for s, t, status in units)
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?><tmx version="1.4">'
        '<header srclang="en" datatype="plaintext" segtype="phrase" adminlang="en"'
        ' o-tmf="x" creationtool="t" creationtoolversion="1"/>'
        f"<body>{body}</body></tmx>",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def memories(tmp_path):
    de = tmx(
        tmp_path / "de-core.tmx",
        "de",
        ("layer", "Ebene", "approved"),
        ("Canvas", "Canvas", "do-not-translate"),
        ("brush", "Pinsel", "proposed"),
        ("blank", "", "approved"),
    )
    pl = tmx(tmp_path / "pl-core.tmx", "pl", ("layer", "warstwa", "approved"))
    return de, pl


def test_memory_paths_when_pattern_has_code_then_one_path_per_code(tmp_path):
    paths = memory_paths(tmp_path, "{code}-core.tmx", ["de", "pl"])
    assert paths == [
        ("de", tmp_path / "de-core.tmx"),
        ("pl", tmp_path / "pl-core.tmx"),
    ], "one path per code, in code order"


def test_memory_paths_when_pattern_lacks_code_or_no_codes_then_value_error(tmp_path):
    with pytest.raises(ValueError):
        memory_paths(tmp_path, "core.tmx", ["de"])
    with pytest.raises(ValueError):
        memory_paths(tmp_path, "{code}.tmx", [])


def test_target_language_when_bilingual_then_non_source_language(memories):
    assert target_language(memories[0], "en") == "de", (
        "the only non-source language is the code"
    )


def test_target_language_when_several_targets_then_value_error(tmp_path):
    path = tmp_path / "multi.tmx"
    tmx(path, "de", ("a", "b", "approved"))
    text = path.read_text(encoding="utf-8").replace(
        "</tu>", '<tuv xml:lang="fr"><seg>c</seg></tuv></tu>'
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=r"\['de', 'fr'\]"):
        target_language(path, "en")
    assert target_language(path, "en", "fr") == "fr", "the exact tag wins"
    with pytest.raises(ValueError, match="'es'"):
        target_language(path, "en", "es")


def test_read_terms_when_statuses_filter_then_proposed_and_blank_dropped(memories):
    terms = read_terms(memories[0], source_lang="en", target_lang="de")
    assert terms == {"layer": "Ebene", "Canvas": "Canvas"}, terms
    opted = read_terms(
        memories[0],
        source_lang="en",
        target_lang="de",
        statuses=frozenset({"proposed"}),
    )
    assert opted == {"brush": "Pinsel"}, opted


def test_build_glossary_when_codes_detected_then_merged_and_sorted(memories):
    de, pl = memories
    glossary = build_glossary([(None, pl), ("de", de)])
    assert list(glossary) == ["Canvas", "layer"], "case-insensitive term order"
    assert list(glossary["layer"].items()) == [("de", "Ebene"), ("pl", "warstwa")], (
        "codes sorted within a term"
    )


def test_write_glossary_json_when_memories_then_file_and_summary(tmp_path, memories):
    out = tmp_path / "derived" / "glossary.json"
    summary = write_glossary_json(out, [("de", memories[0]), ("pl", memories[1])])
    assert summary["terms"] == 2 and summary["codes"] == ["de", "pl"], summary
    assert json.loads(out.read_text(encoding="utf-8"))["layer"]["pl"] == "warstwa", (
        "the view is written as JSON"
    )


def test_write_glossary_json_when_memory_missing_or_none_then_error(tmp_path):
    out = tmp_path / "glossary.json"
    with pytest.raises(FileNotFoundError):
        write_glossary_json(out, [("de", tmp_path / "missing.tmx")])
    with pytest.raises(ValueError):
        write_glossary_json(out, [])
    assert not out.exists(), "nothing is written on error"


def multi(path: Path, *langs: str) -> Path:
    """A memory with one unit carrying every language in ``langs``."""
    tuvs = "".join(
        f'<tuv xml:lang="{lang}"><seg>t-{lang}</seg></tuv>' for lang in langs
    )
    tmx(path, langs[0], ("layer", "x", "approved"))
    text = path.read_text(encoding="utf-8")
    text = text.replace(f'<tuv xml:lang="{langs[0]}"><seg>x</seg></tuv>', tuvs)
    path.write_text(text, encoding="utf-8")
    return path


def test_target_language_when_only_regional_variant_then_used(tmp_path):
    path = tmx(tmp_path / "es-core.tmx", "es-419", ("layer", "capa", "approved"))
    assert target_language(path, "en", "es") == "es-419", "the only target answers"


def test_target_language_when_several_targets_then_closest_variant(tmp_path):
    path = multi(tmp_path / "m.tmx", "de-CH", "fr")
    assert target_language(path, "en", "de") == "de-CH", "closest regional variant"


def test_build_glossary_when_memory_tagged_es_419_then_keyed_by_code(tmp_path):
    path = tmx(tmp_path / "es-core.tmx", "es-419", ("layer", "capa", "approved"))
    de = tmx(tmp_path / "de-core.tmx", "de", ("Layer", "Ebene", "approved"))
    memories = memory_paths(tmp_path, "{code}-core.tmx", ["de", "es"])
    assert memories[1] == ("es", path), memories
    glossary = build_glossary(memories)
    assert glossary == {
        "layer": {"es": "capa"},
        "Layer": {"de": "Ebene"},
    }, "the code is the output key; raw spellings stay separate"
    assert list(glossary) == ["Layer", "layer"], "casefold ties keep memory order"
    assert de.exists(), "fixture written"


def test_build_glossary_when_original_shaped_memories_then_same_structure(tmp_path):
    """The original script's shape: {English: {code: translation}}, terms by
    casefold, codes sorted, approved and do-not-translate only."""
    tmx(
        tmp_path / "pl-core.tmx",
        "pl",
        ("zoom", "powiększenie", "approved"),
        ("Bezier", "Bezier", "do-not-translate"),
        ("anchor", "kotwica", "approved"),
        ("draft", "szkic", "proposed"),
    )
    tmx(tmp_path / "de-core.tmx", "de", ("anchor", "Anker", "approved"))
    glossary = build_glossary(memory_paths(tmp_path, "{code}-core.tmx", ["pl", "de"]))
    assert list(glossary.items()) == [
        ("anchor", {"de": "Anker", "pl": "kotwica"}),
        ("Bezier", {"pl": "Bezier"}),
        ("zoom", {"pl": "powiększenie"}),
    ], glossary


def test_write_glossary_json_when_out_is_a_memory_then_refused_untouched(memories):
    de, pl = memories
    before = de.read_bytes()
    with pytest.raises(ValueError, match="input memory"):
        write_glossary_json(de, [("de", de), ("pl", pl)])
    assert de.read_bytes() == before, "the memory is not replaced by JSON"
