# this_file: tests/test_i18next_formats.py
"""Application JSON must retain native paths, plural suffixes and untouched bytes."""

import json

import pytest

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.conversion import ConversionLoss, convert
from vexy_localizzy.formats import i18next, json_io

RAW = rb"""{
  "menu": {"open": "Open {{ user.name }}", "empty": ""},
  "menu.open": "Literal dotted key",
  "a/b~c": "Escaped key", "\u0061": "Unicode key",
  "items_one": "{{count}} item", "between": "Keep order",
  "items_other": "{{count}} items", "items_zero": "No items",
  "rank_ordinal_one": "{{count}}st", "rank_ordinal_two": "{{count}}nd",
  "rank_ordinal_few": "{{count}}rd", "rank_ordinal_other": "{{count}}th",
  "friend_male_one": "A friend", "friend_male_other": "Friends",
  "choices": ["First", {"label":"Second"}, null, 1.234567890123456789],
  "meta": {"enabled": true, "empty": {}, "list": []},
  "raw": "{{- markup}} {{value, number}} $t(menu.open)",
  "legacy_plural": "Legacy suffix"
}"""


def changed(catalog, key, **updates):
    return catalog.model_copy(
        update={
            "units": [
                unit.model_copy(update=updates) if unit.key == key else unit
                for unit in catalog.units
            ]
        }
    )


def test_i18next_when_retained_roundtrip_then_all_bytes_and_native_forms_survive(
    tmp_path,
):
    source = tmp_path / "en.json"
    source.write_bytes(RAW)
    catalog = i18next.load(source)
    by = {unit.key: unit for unit in catalog.units}
    assert by['["items"]'].plural.forms == {
        "one": "{{count}} item",
        "other": "{{count}} items",
        "zero": "No items",
    }
    assert by['["rank_ordinal"]'].plural.forms["one"] == "{{count}}st"
    assert by['["choices",1,"label"]'].source == "Second"
    assert by['["a"]'].source == "Unicode key"
    assert {p.token for p in by['["raw"]'].placeholders if p.style == "i18next"} == {
        "{{- markup}}",
        "{{value, number}}",
    }
    json_io.dump(catalog, tmp_path / "catalog.json")
    i18next.dump(json_io.load(tmp_path / "catalog.json"), tmp_path / "out.json")
    assert (tmp_path / "out.json").read_bytes() == RAW


def test_i18next_when_editing_then_only_selected_string_bytes_change(tmp_path):
    source = tmp_path / "en.json"
    source.write_bytes(RAW)
    catalog = changed(i18next.load(source), '["menu","open"]', target="")
    catalog = changed(catalog, '["choices",1,"label"]', target="Deuxième 😀")
    catalog = changed(
        catalog,
        '["items"]',
        plural=PluralForms(
            forms={
                "one": "{{count}} élément",
                "other": "{{count}} éléments",
                "zero": "Aucun",
            }
        ),
    )
    i18next.dump(catalog, tmp_path / "out.json")
    expected = (
        RAW.replace(b'"Open {{ user.name }}"', b'""')
        .replace(b'"Second"', '"Deuxième 😀"'.encode())
        .replace(b'"{{count}} item"', '"{{count}} élément"'.encode())
        .replace(b'"{{count}} items"', '"{{count}} éléments"'.encode())
        .replace(b'"No items"', b'"Aucun"')
    )
    assert (tmp_path / "out.json").read_bytes() == expected


def test_i18next_when_fresh_then_nested_arrays_and_plurals_roundtrip(tmp_path):
    catalog = Catalog(
        source_lang="en",
        units=[
            Unit(key='["menu","open"]', context="", source="Open", target="Ouvrir"),
            Unit(key='["choices",0]', context="", source="First"),
            Unit(key='["choices",1]', context="", source="Second"),
            Unit(
                key='["items"]',
                context="",
                source="Items",
                plural=PluralForms(forms={"one": "Item", "other": "Items"}),
            ),
        ],
    )
    i18next.dump(catalog, tmp_path / "out.json")
    assert json.loads((tmp_path / "out.json").read_bytes()) == {
        "menu": {"open": "Ouvrir"},
        "choices": ["First", "Second"],
        "items_one": "Item",
        "items_other": "Items",
    }


def test_i18next_when_explicit_input_format_then_json_cli_conversion_is_unambiguous(
    tmp_path,
):
    source = tmp_path / "en.json"
    source.write_bytes(RAW)
    with pytest.raises(ValueError):
        convert(source, "json", tmp_path / "canonical.json")
    convert(source, "json", tmp_path / "canonical.json", source_format="i18next")
    convert(tmp_path / "canonical.json", "i18next", tmp_path / "out.json")
    assert (tmp_path / "out.json").read_bytes() == RAW


@pytest.mark.parametrize(
    "raw",
    [b'{"a":"x","a":"y"}', b'{"n":NaN}', b"[]", b'{"a":null,}', b'{"a":"\\ud800"}'],
)
def test_i18next_when_invalid_or_ambiguous_then_reject(tmp_path, raw):
    source = tmp_path / "en.json"
    source.write_bytes(raw)
    with pytest.raises(ValueError):
        i18next.load(source)


@pytest.mark.parametrize(
    "updates",
    [
        {"source": "changed"},
        {"state": "translated"},
        {"plural": PluralForms(forms={"other": "changed"})},
        {"target": "scalar"},
    ],
)
def test_i18next_when_unsupported_plural_edit_then_preserve_destination(
    tmp_path, updates
):
    source = tmp_path / "en.json"
    source.write_bytes(RAW)
    output = tmp_path / "out.json"
    output.write_bytes(b"existing")
    with pytest.raises(ValueError):
        i18next.dump(changed(i18next.load(source), '["items"]', **updates), output)
    assert output.read_bytes() == b"existing"


def test_i18next_when_cross_format_then_losses_require_acknowledgement(tmp_path):
    source = tmp_path / "en.json"
    source.write_text('{"open":"Open"}')
    with pytest.raises(ConversionLoss):
        convert(source, "android", tmp_path / "out.xml", source_format="i18next")


def test_i18next_when_fresh_plural_key_empty_then_preserve_destination(tmp_path):
    catalog = Catalog(
        source_lang="en",
        units=[
            Unit(
                key='[""]',
                context="",
                source="Items",
                plural=PluralForms(forms={"one": "Item", "other": "Items"}),
            )
        ],
    )
    output = tmp_path / "out.json"
    output.write_bytes(b"existing")
    with pytest.raises(ValueError, match="plural"):
        i18next.dump(catalog, output)
    assert output.read_bytes() == b"existing"


@pytest.mark.parametrize("path", ['["a",2]', '["a",true]', '["a",-1]', "[0]", "[]"])
def test_i18next_when_fresh_path_invalid_then_reject(tmp_path, path):
    catalog = Catalog(source_lang="en", units=[Unit(key=path, context="", source="x")])
    with pytest.raises(ValueError):
        i18next.dump(catalog, tmp_path / "out.json")
    assert not (tmp_path / "out.json").exists()


def test_i18next_when_scalar_and_plural_share_base_then_distinct_ids_and_edits(
    tmp_path,
):
    source = tmp_path / "en.json"
    source.write_text('{"item":"Base","item_one":"One","item_other":"Many"}')
    catalog = i18next.load(source)
    assert {unit.key for unit in catalog.units} == {'["item"]', 'plural:["item"]'}
    i18next.dump(changed(catalog, '["item"]', target="Changed"), tmp_path / "out.json")
    assert json.loads((tmp_path / "out.json").read_bytes()) == {
        "item": "Changed",
        "item_one": "One",
        "item_other": "Many",
    }


def test_i18next_when_cli_selects_application_json_then_exact_roundtrip(
    tmp_path, monkeypatch, capsys
):
    from vexy_localizzy.cli import main

    source = tmp_path / "en.json"
    source.write_bytes(RAW)
    canonical = tmp_path / "catalog.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "localizzy",
            "convert",
            str(source),
            "json",
            str(canonical),
            "--source_format=i18next",
        ],
    )
    main()
    assert "entries:" in capsys.readouterr().out
    convert(canonical, "i18next", tmp_path / "out.json")
    assert (tmp_path / "out.json").read_bytes() == RAW
