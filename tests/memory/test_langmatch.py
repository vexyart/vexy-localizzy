# this_file: tests/memory/test_langmatch.py
"""Catalog locales resolve to the memory's TUV language by an explicit rule."""

import pytest

from vexy_localizzy.memory import select_language


@pytest.mark.parametrize(
    ("available", "wanted", "chosen"),
    [
        (["en", "es-419"], "es_MX", "es-419"),
        (["en", "de"], "de_DE", "de"),
        (["en", "fr"], "fr_FR", "fr"),
        (["en", "no", "nb"], "no", "no"),
        (["en", "pt-BR", "pt-PT"], "pt_BR", "pt-BR"),
    ],
)
def test_select_language_when_catalog_tag_then_picks_memory_variant(
    available, wanted, chosen
):
    assert select_language(available, wanted) == chosen, (available, wanted)


def test_select_language_when_override_present_then_wins():
    assert select_language(["en", "es", "es-419"], "es_MX", override="es") == "es"


def test_select_language_when_override_missing_then_raises():
    with pytest.raises(ValueError, match="no es-ES variant"):
        select_language(["en", "es-419"], "es_MX", override="es-ES")


def test_select_language_when_equally_close_variants_then_raises():
    with pytest.raises(ValueError, match="equally close"):
        select_language(["de-AT", "de-CH"], "de_DE")


@pytest.mark.parametrize(
    ("available", "wanted"),
    [
        (["en", "zh-Hans"], "zh_TW"),
        (["en", "zh-CN"], "zh_TW"),
        (["en", "zh"], "zh_TW"),
        (["en", "zh-Hant"], "zh_CN"),
        (["en", "sr-Latn"], "sr_Cyrl"),
        (["en", "sr"], "sr-Latn"),
        (["en", "pt-BR"], "pt_PT"),
        (["en", "pt-PT"], "pt_BR"),
        (["en", "pt"], "pt_PT"),
        (["en", "es-ES"], "es_MX"),
        (["en", "es-419"], "es_ES"),
        (["es", "es-ES"], "es_MX"),
    ],
)
def test_select_language_when_single_variant_crosses_script_or_region_then_raises(
    available, wanted
):
    with pytest.raises(ValueError, match="pass --memory-lang"):
        select_language(available, wanted)


@pytest.mark.parametrize(
    ("available", "wanted", "chosen"),
    [
        (["en", "zh-Hant"], "zh_TW", "zh-Hant"),
        (["en", "zh-Hans"], "zh_CN", "zh-Hans"),
        (["en", "sr-Latn"], "sr_Latn_RS", "sr-Latn"),
        (["en", "pt"], "pt_BR", "pt"),
        (["en", "de"], "de_CH", "de"),
        (["en", "es-419"], "es_AR", "es-419"),
    ],
)
def test_select_language_when_single_variant_same_script_and_close_then_picks_it(
    available, wanted, chosen
):
    assert select_language(available, wanted) == chosen, (available, wanted)


def test_select_language_when_not_strict_then_single_variant_is_taken():
    assert select_language(["en-GB", "de"], "en", strict=False) == "en-GB"


def test_select_language_when_no_primary_match_then_raises_naming_wanted():
    with pytest.raises(ValueError, match="no pl_PL variant; pass --memory-lang"):
        select_language(["en", "de"], "pl_PL")
