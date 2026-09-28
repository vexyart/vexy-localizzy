# this_file: tests/test_tmx.py
"""Streaming TMX records retain literal content and source ordinals."""

import pytest

from vexy_localizzy.memory.tmx_read import read_tmx


@pytest.mark.parametrize(
    ("raw", "canonical"),
    [
        ("sr-ijekavian", "sr-ijekavsk"),
        ("sr-ijekavianlatin", "sr-Latn-ijekavsk"),
        ("mni-meiteimayek", "mni-Mtei"),
    ],
)
def test_read_tmx_when_legacy_locale_then_preserves_spelling_and_indexes_canonical(
    tmp_path, raw, canonical
):
    path = tmp_path / "legacy.tmx"
    path.write_text(
        f'<tmx><body><tu><tuv lang="en"><seg>Moon</seg></tuv><tuv lang="{raw}"><seg>Target</seg></tuv></tu></body></tmx>'
    )
    target = next(read_tmx(path)).segments[1]
    assert target.language == canonical and target.raw_language == raw


def test_read_tmx_when_english_is_second_then_selects_by_tag(tmp_path):
    path = tmp_path / "source.tmx"
    path.write_text(
        '<tmx><header srclang="en"/><body><tu tuid="moon"><prop type="origin">sample</prop><tuv xml:lang="pl"><seg>Księżyc</seg></tuv><tuv xml:lang="en"><seg>Moon</seg></tuv></tu></body></tmx>'
    )
    unit = next(read_tmx(path))
    assert unit.ordinal == 1 and unit.tuid == "moon"
    assert unit.english().text == "Moon"
    assert unit.properties == (("origin", "sample"),)
    assert unit.segments[0].language == "pl"


def test_read_tmx_when_inline_then_retains_codes_and_tail(tmp_path):
    path = tmp_path / "inline.tmx"
    path.write_text(
        '<tmx><body><tu><tuv lang="en"><seg>A <bpt i="1">&lt;b&gt;</bpt>moon<ept i="1">&lt;/b&gt;</ept> rises.</seg></tuv></tu></body></tmx>'
    )
    source = next(read_tmx(path)).english()
    assert source.text == "A <b>moon</b> rises."
    assert '<bpt i="1">' in source.xml
    assert source.inline


def test_read_tmx_when_no_english_then_does_not_guess(tmp_path):
    path = tmp_path / "pl.tmx"
    path.write_text(
        '<tmx><body><tu><tuv lang="pl"><seg>Księżyc</seg></tuv></tu></body></tmx>'
    )
    assert next(read_tmx(path)).english() is None


def test_read_tmx_when_regional_english_ambiguous_then_requires_selection(tmp_path):
    path = tmp_path / "variants.tmx"
    path.write_text(
        '<tmx><body><tu><tuv lang="en-US"><seg>Color</seg></tuv><tuv lang="en-GB"><seg>Colour</seg></tuv></tu></body></tmx>'
    )
    with pytest.raises(ValueError, match="Ambiguous"):
        next(read_tmx(path)).english()


@pytest.mark.parametrize(
    "content", ["<other/>", '<!DOCTYPE tmx [<!ENTITY x "hidden">]><tmx><body/></tmx>']
)
def test_read_tmx_when_invalid_root_or_entities_then_rejects(tmp_path, content):
    path = tmp_path / "invalid.tmx"
    path.write_text(content)
    with pytest.raises(ValueError):
        list(read_tmx(path))


def test_read_tmx_when_streamed_then_previous_record_stays_intact(tmp_path):
    path = tmp_path / "many.tmx"
    path.write_text(
        '<tmx xmlns="urn:tmx"><body>'
        + "".join(
            f'<tu><tuv lang="en"><seg>Text {i}</seg></tuv></tu>' for i in range(2000)
        )
        + "</body></tmx>"
    )
    rows = read_tmx(path)
    first = next(rows)
    last = None
    for last in rows:
        pass
    assert first.english().text == "Text 0" and last.ordinal == 2000
