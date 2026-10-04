# this_file: tests/memory/test_glossary.py
"""Glossary: status filter, word-boundary matching, limit and stable ordering."""

from pathlib import Path

import pytest

from vexy_localizzy.memory import Glossary, match_text
from vexy_localizzy.memory.glossary import capitalize_first

CORE_DE = Path(__file__).parent.parent / "fixtures" / "memory" / "core-de.tmx"


@pytest.mark.parametrize(
    ("text", "lang", "expected"),
    [
        ("удалить наложение", "ru", "Удалить наложение"),
        ("ábra", "hu", "Ábra"),
        ("Öffnen", "de", "Öffnen"),
        ("", "de", ""),
        ("カーニング", "ja", "カーニング"),
        ("كيرنينغ", "ar", "كيرنينغ"),
        ("კერნინგი", "ka", "კერნინგი"),
        ("«кернинг»", "ru", "«кернинг»"),
        (" kerning", "en", " kerning"),
        ("ßtest", "de", "ßtest"),
        ("içe aktar", "tr", "İçe aktar"),
        ("içe aktar", "tr_TR", "İçe aktar"),
        ("idxal", "az", "İdxal"),
        ("ışık", "tr", "Işık"),
        ("import", "en", "Import"),
        ("import", None, "Import"),
        ("ijken", "nl-NL", "IJken"),
        ("ijken", "de", "Ijken"),
    ],
)
def test_capitalize_first_when_given_text_then_only_a_cased_first_letter_changes(
    text, lang, expected
):
    assert capitalize_first(text, lang) == expected, (text, lang)


@pytest.fixture
def glossary() -> Glossary:
    return Glossary.load([CORE_DE], source_lang="en", target_lang="de_DE")


def test_match_text_when_markup_accelerators_placeholders_then_normalized():
    assert match_text("&Kerning") == "kerning"
    assert match_text("Save && Quit") == "save & quit"
    assert match_text("<b>Glyph</b>") == "glyph"
    assert match_text("Move %1 by {count}") == "move   by  "


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("字形(&G)", "字形"),
        ("フォントオーディット (&F)", "フォントオーディット"),
        ("열기（&O）…", "열기…"),
        ("เปิด (&O)...", "เปิด..."),
        ("Name (&N):", "name:"),
        ("名称（&N）：", "名称："),
        ("Power Nu&dge", "power nudge"),
        ("Name (G)", "name (g)"),
        ("Name (&&G)", "name (&g)"),
        ("Name (&G) suffix", "name (g) suffix"),
        ("Name (&Go)", "name (go)"),
    ],
)
def test_match_text_when_qt_suffix_then_ignore_only_single_key_annotation(
    label, expected
):
    assert match_text(label) == expected, (
        "A Qt shortcut suffix must not become part of the glossary term."
    )


def test_whole_match_when_appended_accelerator_then_find_canonical_term(glossary):
    term = glossary.whole_match("Kerning (&K)")
    assert term is not None and term.term_id == "kerning", (
        "Appended accelerators must match like embedded accelerators."
    )


def test_relevant_when_word_is_longer_then_boundary_blocks_partial(glossary):
    found = glossary.relevant(["Show kerning"])
    assert "kerning" in found and "kern" not in found, found


def test_relevant_when_accelerator_then_matches(glossary):
    assert glossary.relevant(["&Kerning"]) == {"kerning": "Unterschneidung"}


def test_relevant_when_tags_then_matches(glossary):
    assert glossary.relevant(["<b>Glyph</b> view"]) == {"glyph": "Glyphe"}


def test_relevant_when_do_not_translate_then_maps_to_itself(glossary):
    assert glossary.relevant(["About DemoApp"]) == {"DemoApp": "DemoApp"}


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
    texts = ["Add kerning class to DemoApp glyph"]
    everything = glossary.relevant(texts)
    assert list(everything) == ["class", "DemoApp", "glyph", "kerning", "kerning class"]
    limited = glossary.relevant(texts, limit=2)
    # "DemoApp" and "kerning" tie on length; the casefolded source breaks the tie.
    assert list(limited) == ["DemoApp", "kerning class"], limited
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


def _core(tmp_path: Path, units: str) -> Path:
    path = tmp_path / "core.tmx"
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<tmx version="1.4"><header creationtool="t" '
        'creationtoolversion="1" segtype="phrase" o-tmf="tmx" adminlang="en" srclang="en" '
        'datatype="plaintext"/><body>' + units + "</body></tmx>\n",
        encoding="utf-8",
    )
    return path


def test_hint_when_target_empty_and_fallback_then_fallback_phrase(tmp_path):
    core = _core(
        tmp_path,
        '<tu tuid="term:stem"><prop type="x-term-id">stem</prop>'
        '<prop type="x-translatable">yes</prop><prop type="x-fallback">main stroke</prop>'
        '<prop type="x-status">proposed</prop><tuv xml:lang="en"><seg>stem</seg></tuv>'
        '<tuv xml:lang="pl"><seg></seg></tuv></tu>'
        '<tu tuid="term:overshoot"><prop type="x-term-id">overshoot</prop>'
        '<prop type="x-translatable">yes</prop><prop type="x-fallback">optical surplus</prop>'
        '<prop type="x-status">approved</prop><tuv xml:lang="en"><seg>overshoot</seg></tuv>'
        '<tuv xml:lang="pl"><seg>naddatek</seg></tuv></tu>',
    )
    glossary = Glossary.load(
        [core],
        source_lang="en",
        target_lang="pl",
        statuses=frozenset({"approved", "proposed"}),
    )
    by_id = {t.term_id: t for t in glossary.terms}
    assert by_id["stem"].fallback == "main stroke"
    assert by_id["overshoot"].hint == "naddatek", "a real target wins over the fallback"
    assert glossary.relevant(["Stem overshoot"]) == {
        "overshoot": "naddatek",
        "stem": "(translate the plain phrase: main stroke)",
    }
