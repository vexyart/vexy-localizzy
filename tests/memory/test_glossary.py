# this_file: tests/memory/test_glossary.py
"""Glossary: status filter, word-boundary matching, limit and stable ordering."""

from pathlib import Path

import pytest

from vexy_localizzy.memory import Glossary, match_text

CORE_DE = Path(__file__).parent.parent / "fixtures" / "memory" / "core-de.tmx"


@pytest.fixture
def glossary() -> Glossary:
    return Glossary.load([CORE_DE], source_lang="en", target_lang="de_DE")


def test_match_text_when_markup_accelerators_placeholders_then_normalized():
    assert match_text("&Kerning") == "kerning"
    assert match_text("Save && Quit") == "save & quit"
    assert match_text("<b>Glyph</b>") == "glyph"
    assert match_text("Move %1 by {count}") == "move   by  "


def test_relevant_when_word_is_longer_then_boundary_blocks_partial(glossary):
    found = glossary.relevant(["Show kerning"])
    assert "kerning" in found and "kern" not in found, found


def test_relevant_when_accelerator_then_matches(glossary):
    assert glossary.relevant(["&Kerning"]) == {"kerning": "Unterschneidung"}


def test_relevant_when_tags_then_matches(glossary):
    assert glossary.relevant(["<b>Glyph</b> view"]) == {"glyph": "Glyphe"}


def test_relevant_when_do_not_translate_then_maps_to_itself(glossary):
    assert glossary.relevant(["About FontLab"]) == {"FontLab": "FontLab"}


def test_relevant_when_proposed_then_excluded_by_default(glossary):
    assert glossary.relevant(["Open font"]) == {}
    opted = Glossary.load(
        [CORE_DE],
        source_lang="en",
        target_lang="de",
        statuses=frozenset({"approved", "proposed", "do-not-translate"}),
    )
    assert opted.relevant(["Open font"]) == {"font": "Schrift"}


def test_relevant_when_over_limit_then_longest_kept_in_casefold_order(glossary):
    texts = ["Add kerning class to FontLab glyph"]
    everything = glossary.relevant(texts)
    assert list(everything) == ["class", "FontLab", "glyph", "kerning", "kerning class"]
    limited = glossary.relevant(texts, limit=2)
    # "FontLab" and "kerning" tie on length; the casefolded source breaks the tie.
    assert list(limited) == ["FontLab", "kerning class"], limited
    assert list(glossary.relevant(texts, limit=1)) == ["kerning class"]
    assert glossary.relevant(list(reversed(texts * 2)), limit=2) == limited


def test_whole_match_when_whole_string_is_term_then_returns_term(glossary):
    term = glossary.whole_match("&Kerning")
    assert term is not None and term.term_id == "kerning"
    assert term.note == "Adjusting space between glyph pairs."
    assert term.target_note == "Established term."
    assert glossary.whole_match("Kerning:") is None


def test_summary_when_loaded_then_counts_terms_and_exclusions(glossary):
    summary = glossary.summary()
    assert (summary["terms"], summary["terms_excluded"]) == (6, 1), summary
    assert summary["statuses"] == ["approved", "do-not-translate"]


def test_glossary_load_when_unknown_status_then_term_excluded_not_crash(tmp_path):
    path = tmp_path / "g.tmx"
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?><tmx version="1.4">'
        '<header creationtool="t" creationtoolversion="1" segtype="phrase" '
        'o-tmf="tmx" adminlang="en" srclang="en" datatype="plaintext"/><body>'
        '<tu tuid="term:x"><prop type="x-status">deprecated</prop>'
        '<tuv xml:lang="en"><seg>x</seg></tuv><tuv xml:lang="de"><seg>y</seg></tuv></tu>'
        '<tu tuid="term:k"><prop type="x-status">approved</prop>'
        '<tuv xml:lang="en"><seg>kern</seg></tuv>'
        '<tuv xml:lang="de"><seg>unterschneiden</seg></tuv></tu>'
        "</body></tmx>",
        encoding="utf-8",
    )
    glossary = Glossary.load([path], source_lang="en", target_lang="de")
    assert [t.source for t in glossary.terms] == ["kern"]
    assert glossary.excluded == 1
