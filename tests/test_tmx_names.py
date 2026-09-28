# this_file: tests/test_tmx_names.py
"""Explicit filename policy preserves scripts and refuses ambiguous destinations."""

from pathlib import Path

import pytest

from vexy_localizzy.tmx_names import parse_tag, plan_folder, top_territory


@pytest.mark.parametrize(
    "source,expected",
    [
        ("en-US", "en"),
        ("en-uk", "en-gb"),
        ("de-DE", "de"),
        ("de-AT", "de-at"),
        ("es-MX", "es"),
        ("iw", "he"),
        ("zh-CN", "zh-hans"),
        ("zh-TW", "zh-hant"),
        ("zh-HK", "zh-hant-hk"),
        ("pa-PK", "pa-pk"),
        ("yue-CN", "yue-cn"),
        ("bs-Cyrl-BA", "bs-cyrl"),
        ("sr-Latn-RS", "sr-latn"),
    ],
)
def test_plan_when_locale_variants_then_explicit_legacy_naming(source, expected):
    path = Path(source + ".tmx")
    assert plan_folder([path]) == [(path, expected + ".tmx", "")]


def test_plan_when_two_names_converge_then_skip_both():
    files = [Path("en-US.tmx"), Path("en.tmx")]
    result = plan_folder(files)
    assert all(
        name is None and note == "collision: 2 files -> en.tmx"
        for _, name, note in result
    )
    assert {path for path, _, _ in result} == set(files)


def test_parse_when_legacy_territory_then_only_use_configured_alias():
    assert parse_tag("sr-Cyrl-SP") is None
    assert str(parse_tag("sr-Cyrl-SP", territory_aliases={"sp": "rs"})) == "sr-Cyrl-RS"
    assert str(parse_tag("de-x-sp", territory_aliases={"sp": "rs"})) == "de-x-sp", (
        "Private-use tags are not territories"
    )


@pytest.mark.parametrize("value", ["", "???", "invalid_language_name", "und"])
def test_parse_when_invalid_then_no_rename(value):
    assert parse_tag(value) is None


def test_plan_when_folders_differ_then_refuse_misleading_collisions():
    with pytest.raises(ValueError, match="one folder"):
        plan_folder([Path("one/en-US.tmx"), Path("two/en.tmx")])


def test_population_when_tied_or_missing_then_keep_territories(monkeypatch):
    from vexy_localizzy import tmx_names

    monkeypatch.setattr(
        tmx_names, "LANGUAGE_SPEAKING_POPULATION", {"en-US": 10, "en-GB": 10}
    )
    top_territory.cache_clear()
    try:
        assert top_territory("en") is None
        assert top_territory("de") is None
        path = Path("en-US.tmx")
        assert plan_folder([path]) == [(path, "en-us.tmx", "")]
    finally:
        top_territory.cache_clear()
