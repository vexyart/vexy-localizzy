# this_file: tests/test_pseudo.py
"""Pseudo-localization keeps every token and fills every native target shape."""

import pytest

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.cli import checks
from vexy_localizzy.formats import ts
from vexy_localizzy.pseudo import pseudo_catalog, pseudo_mapping, pseudo_string


def test_pseudo_string_when_accent_then_wrapped_and_longer():
    out = pseudo_string("Settings", expansion=0.4)
    assert out.startswith("⟦") and out.endswith("⟧"), out
    assert len(out) > len("Settings") + 2, "padding must expand the text"


@pytest.mark.parametrize(
    "text, tokens",
    [
        ("Saved %1 of %2", ["%1", "%2"]),
        ("Total: %L1 in %Ln files", ["%L1", "%Ln"]),
        ("%n glyph(s)", ["%n"]),
        ("Count {{count}}", ["{{count}}"]),
        ("Bold <b>x</b>", ["<b>", "</b>"]),
        ("{n, plural, one {x} other {y}}", ["{n, plural, one {", "} other {"]),
        ("%1$s of %(name)s and %s", ["%1$s", "%(name)s", "%s"]),
        ("&Open && save&nbsp;now", ["&O", "&&", "&nbsp;"]),
    ],
)
def test_pseudo_string_when_tokens_present_then_kept_verbatim(text, tokens):
    out = pseudo_string(text)
    for token in tokens:
        assert token in out, f"{token!r} lost in {out!r}"


def test_pseudo_string_when_bracket_or_rtl_then_mode_shape():
    bracket = pseudo_string("Hi", mode="bracket")
    assert bracket.startswith("[") and bracket.endswith("]"), bracket
    rtl = pseudo_string("Hi", mode="rtl")
    assert rtl == "\u202bHi\u202c", "rtl wraps the unchanged text in embedding marks"


def test_pseudo_string_when_mode_unknown_then_value_error():
    with pytest.raises(ValueError, match="mode"):
        pseudo_string("Hi", mode="upside-down")


def test_pseudo_string_when_empty_then_unchanged():
    assert pseudo_string("") == "", "an empty source stays empty"


def test_pseudo_catalog_when_scalar_and_plural_then_all_forms_filled():
    catalog = Catalog(
        source_lang="en",
        target_lang="pl",
        units=[
            Unit(key="k", context="C", source="Open"),
            Unit(
                key="n",
                context="C",
                source="%n files",
                plural=PluralForms(forms={"0": "", "1": "", "2": ""}, indexing="index"),
            ),
            Unit(key="v", context="C", source="Gone", state="vanished"),
        ],
    )
    out = pseudo_catalog(catalog)
    assert out.target_lang == "xx-pseudo", "the pseudo locale is tagged"
    assert out.units[0].target.startswith("⟦") and out.units[0].state == "translated"
    forms = out.units[1].plural.forms
    assert set(forms) == {"0", "1", "2"} and all("%n" in f for f in forms.values())
    assert out.units[2] == catalog.units[2], "vanished messages stay untouched"


def test_pseudo_mapping_when_flat_then_each_value_transformed():
    out = pseudo_mapping({"a": "Open {0}"})
    assert "{0}" in out["a"] and out["a"] != "Open {0}", out


def test_pseudo_command_when_ts_then_placeholders_survive_round_trip(tmp_path):
    source = tmp_path / "app_de.ts"
    source.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n'
        '<TS version="2.1" language="de" sourcelanguage="en"><context><name>C</name>'
        "<message><source>Open %1</source><translation>Öffnen %1</translation></message>"
        '<message numerus="yes"><source>%n file(s)</source><translation>'
        "<numerusform>%n Datei</numerusform><numerusform>%n Dateien</numerusform>"
        "</translation></message></context></TS>\n",
        encoding="utf-8",
    )
    out = tmp_path / "app_pseudo.ts"
    result = checks.pseudo(str(source), str(out), allow_loss=True)
    assert result["units"] == 2, result
    loaded = ts.load(out)
    assert "%1" in loaded.units[0].target and "⟦" in loaded.units[0].target
    assert all("%n" in form for form in loaded.units[1].plural.forms.values())
    assert "Öffnen" in source.read_text(encoding="utf-8"), "the input is not edited"


def test_pseudo_command_when_suffix_unknown_then_usage_exit(tmp_path):
    with pytest.raises(SystemExit) as caught:
        checks.pseudo(str(tmp_path / "in.ts"), str(tmp_path / "out.docx"))
    assert caught.value.code == 2, "an unsupported suffix is a usage error"


@pytest.mark.parametrize(
    "text, tokens",
    [
        ("%u of %x", ["%u", "%x"]),
        ("%ld bytes, %lld total", ["%ld", "%lld"]),
        ("%.2f mm at %-5s", ["%.2f", "%-5s"]),
        ("100% done", []),
    ],
)
def test_pseudo_string_when_printf_specs_then_whole_spec_kept(text, tokens):
    out = pseudo_string(text)
    for token in tokens:
        assert token in out, f"{token!r} lost in {out!r}"
    if not tokens:
        assert "δōņē" in out, "a bare percent sign is not a conversion"


def test_pseudo_string_when_icu_arms_nested_then_keywords_kept_and_arms_accented():
    text = "{n, plural, one {{name} has # file} other {{name} has # files}}"
    out = pseudo_string(text)
    assert "{n, plural, one {" in out and "} other {" in out, out
    assert out.count("{name}") == 2, "placeholders inside arms survive"
    assert "ƒīłēš" in out, "arm text is pseudo-localized"


def test_pseudo_catalog_when_icu_nested_then_plural_forms_kept():
    from vexy_localizzy.plurals import parse_icu_plural

    source = "{n, plural, one {{name} has # file} other {{name} has # files}}"
    unit = Unit(key="k", context="C", source=source, plural=parse_icu_plural(source))
    out = pseudo_catalog(Catalog(source_lang="en", units=[unit])).units[0]
    assert out.plural is not None and set(out.plural.forms) == {"one", "other"}, out


def test_pseudo_command_when_out_is_input_then_refused(tmp_path):
    source = tmp_path / "app_de.ts"
    source.write_text('<TS language="de"><context><name>C</name></context></TS>')
    before = source.read_bytes()
    with pytest.raises(SystemExit) as caught:
        checks.pseudo(str(source), str(source))
    assert caught.value.code == 2 and source.read_bytes() == before, "input kept"
