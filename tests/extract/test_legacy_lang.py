# this_file: tests/extract/test_legacy_lang.py
"""The legacy tag policy keeps scripts, numeric regions and both Portugueses apart."""

import pytest

from vexy_localizzy.extract import lproj, ts2tmx
from vexy_localizzy.extract.legacy_lang import norm_lang, stem_lang
from vexy_localizzy.extract.lproj import lproj_lang


@pytest.mark.parametrize(
    ("raw", "tag"),
    [
        ("sr_Latn", "sr-Latn"),
        ("sr-latn-RS", "sr-Latn-RS"),
        ("es_419", "es-419"),
        ("es-419.lproj", "es-419"),
        ("pt", "pt-PT"),
        ("pt_PT", "pt-PT"),
        ("pt_BR", "pt-BR"),
        ("pt.lproj", "pt-BR"),
        ("pt-PT.lproj", "pt-PT"),
        ("zh-Hant-HK", "zh-Hant-HK"),
        ("zh_Hans", "zh-CN"),
        ("zh-Hant", "zh-TW"),
        ("de_DE", "de"),
        ("es_ES", "es"),
        ("en_GB", "en-GB"),
    ],
)
def test_norm_lang_when_script_numeric_region_or_portuguese_then_kept_distinct(
    raw, tag
):
    assert norm_lang(raw) == tag, raw


@pytest.mark.parametrize(
    ("name", "tag"),
    [
        ("pt.lproj", "pt-BR"),
        ("Portuguese.lproj", "pt-BR"),
        ("pt-PT.lproj", "pt-PT"),
        ("pt_PT.lproj", "pt-PT"),
        ("sr-Latn.lproj", "sr-Latn"),
        ("es-419.lproj", "es-419"),
    ],
)
def test_lproj_lang_when_apple_folder_then_apple_meaning(name, tag):
    assert lproj_lang(name) == (tag, False), name


def test_stem_lang_when_script_or_numeric_region_then_kept():
    assert stem_lang("app_sr_Latn") == "sr-Latn"
    assert stem_lang("app_es_419") == "es-419"


def test_ts2tmx_when_sr_latn_catalog_then_tagged_sr_latn(tmp_path):
    ts = tmp_path / "app_sr_Latn.ts"
    ts.write_text(
        '<?xml version="1.0" encoding="utf-8"?><!DOCTYPE TS>'
        '<TS version="2.1" sourcelanguage="en"><context><name>C</name>'
        "<message><source>Save</source><translation>Sačuvaj</translation></message>"
        "</context></TS>",
        encoding="utf-8",
    )
    result = ts2tmx.run(str(ts), str(tmp_path / "out.tmx"))
    assert [row["lang"] for row in result["files"]] == ["sr-Latn"]
    assert 'xml:lang="sr-Latn"' in (tmp_path / "out.tmx").read_text(encoding="utf-8")


def test_lproj_run_when_pt_and_pt_pt_folders_then_two_languages(tmp_path):
    res = tmp_path / "Example.app" / "Contents" / "Resources"
    for folder, text in [
        ("en", "Save"),
        ("pt", "Salvar"),
        ("pt-PT", "Guardar"),
    ]:
        path = res / f"{folder}.lproj" / "Localizable.strings"
        path.parent.mkdir(parents=True)
        path.write_text(f'"save" = "{text}";', encoding="utf-8")
    lproj.run(str(tmp_path / "Example.app"), str(tmp_path / "out"))
    names = sorted(p.name for p in (tmp_path / "out").glob("*.tmx"))
    assert names == ["en.tmx", "pt-BR.tmx", "pt-PT.tmx"], names
    assert "Salvar" in (tmp_path / "out" / "pt-BR.tmx").read_text(encoding="utf-8")
    assert "Guardar" not in (tmp_path / "out" / "pt-BR.tmx").read_text(encoding="utf-8")
