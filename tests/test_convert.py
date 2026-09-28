# this_file: tests/test_convert.py
"""Conversions expose losses before replacing any user output."""

import pytest

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.conversion import ConversionLoss, convert
from vexy_localizzy.formats import json_io, po, ts


def test_convert_when_ts_json_ts_then_bytes_survive(tmp_path):
    source = tmp_path / "input.ts"
    source.write_bytes(
        b'<TS><context><name>C</name><message id="a"><source>Open</source><translation>Ouvrir</translation><extra-retain>yes</extra-retain></message></context></TS>'
    )
    result = convert(source, "json", tmp_path / "saved.json")
    assert not result.findings
    result = convert(result.out_path, "ts", tmp_path / "out.ts")
    assert not result.findings
    assert result.out_path.read_bytes() == source.read_bytes()


def test_convert_when_loss_unacknowledged_then_report_and_leave_destination(tmp_path):
    source = tmp_path / "input.ts"
    source.write_text(
        '<TS language="pl"><context><name>C</name><message id="a"><source>Open</source><comment>verb</comment><translation>Otwórz</translation><extra-retain>yes</extra-retain></message></context></TS>'
    )
    output = tmp_path / "out.po"
    output.write_bytes(b"existing")
    with pytest.raises(ConversionLoss) as error:
        convert(source, "po", output)
    fields = {finding.data["field"] for finding in error.value.findings}
    assert {"document", "disambiguation", "key"} <= fields
    assert output.read_bytes() == b"existing"
    result = convert(source, "po", output, allow_loss=True)
    assert result.findings
    assert po.load(output).units[0].target == "Otwórz"


def test_convert_when_po_plural_to_ts_then_source_plural_loss_is_explicit(tmp_path):
    source = tmp_path / "input.po"
    source.write_text(
        'msgid ""\nmsgstr "Language: de\\nPlural-Forms: nplurals=2; plural=n!=1;\\n"\n\nmsgid "One item"\nmsgid_plural "Many items"\nmsgstr[0] "Ein Element"\nmsgstr[1] "Viele Elemente"\n'
    )
    with pytest.raises(ConversionLoss) as error:
        convert(source, "ts", tmp_path / "out.ts")
    assert "source_plural" in {
        finding.data["field"] for finding in error.value.findings
    }
    result = convert(source, "ts", tmp_path / "out.ts", allow_loss=True)
    assert ts.load(result.out_path).units[0].plural.forms == {
        "0": "Ein Element",
        "1": "Viele Elemente",
    }


def test_convert_when_qt_plural_to_po_then_shared_source_is_reported(tmp_path):
    source = tmp_path / "input.ts"
    source.write_text(
        '<TS language="de"><context><name>C</name><message numerus="yes"><source>%n items</source><translation><numerusform>%n Element</numerusform><numerusform>%n Elemente</numerusform></translation></message></context></TS>'
    )
    with pytest.raises(ConversionLoss) as error:
        convert(
            source, "po", tmp_path / "out.po", plural_forms="nplurals=2; plural=n!=1;"
        )
    assert "source_plural" in {
        finding.data["field"] for finding in error.value.findings
    }
    result = convert(
        source,
        "po",
        tmp_path / "out.po",
        plural_forms="nplurals=2; plural=n!=1;",
        allow_loss=True,
    )
    assert po.load(result.out_path).units[0].source_plural == "%n items"


def test_convert_when_cldr_plural_then_require_explicit_order(tmp_path):
    source = tmp_path / "input.json"
    json_io.dump(
        Catalog(
            source_lang="en",
            target_lang="pl",
            units=[
                Unit(
                    key="n",
                    context="C",
                    source="%n things",
                    plural=PluralForms(
                        forms={"many": "Wiele", "one": "Jeden", "few": "Kilka"}
                    ),
                )
            ],
        ),
        source,
    )
    with pytest.raises(ValueError, match="plural_order"):
        convert(source, "ts", tmp_path / "out.ts", allow_loss=True)
    convert(
        source,
        "ts",
        tmp_path / "out.ts",
        allow_loss=True,
        plural_order=["one", "few", "many"],
    )
    assert ts.load(tmp_path / "out.ts").units[0].plural.forms == {
        "0": "Jeden",
        "1": "Kilka",
        "2": "Wiele",
    }


def test_convert_when_interleaved_contexts_then_message_order_survives(tmp_path):
    source = tmp_path / "input.json"
    catalog = Catalog(
        source_lang="en",
        units=[
            Unit(key=str(i), context=context, source=str(i))
            for i, context in enumerate(("A", "B", "A"))
        ],
    )
    json_io.dump(catalog, source)
    convert(source, "ts", tmp_path / "out.ts", allow_loss=True)
    assert [unit.source for unit in ts.load(tmp_path / "out.ts").units] == [
        "0",
        "1",
        "2",
    ]


def test_convert_when_unsupported_target_then_no_output(tmp_path):
    source = tmp_path / "input.json"
    json_io.dump(Catalog(source_lang="en"), source)
    with pytest.raises(ValueError, match="target"):
        convert(source, "unknown", tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_catalog_conversion_when_icu_dropped_then_acknowledge_before_replacing(
    tmp_path,
):
    from vexy_localizzy.conversion import convert_catalog

    catalog = Catalog(
        source_lang="en",
        target_lang="de",
        units=[
            Unit(
                key="count",
                context="C",
                source="%n files",
                plural=PluralForms(
                    icu="{n, plural, one {file} other {files}}",
                    forms={"one": "%n Datei", "other": "%n Dateien"},
                ),
            )
        ],
    )
    out = tmp_path / "out.ts"
    out.write_bytes(b"existing")
    with pytest.raises(ConversionLoss):
        convert_catalog(catalog, "ts", out, plural_order=["one", "other"])
    assert out.read_bytes() == b"existing"
    result = convert_catalog(
        catalog, "ts", out, plural_order=["one", "other"], allow_loss=True
    )
    assert any(f.data["field"] == "plural" for f in result.findings)
    assert ts.load(out).units[0].plural.forms == {"0": "%n Datei", "1": "%n Dateien"}
    assert catalog.units[0].plural.icu is not None, "Caller data must remain unchanged"


def test_convert_when_po_plural_rule_changes_then_acknowledgement_required(tmp_path):
    source = tmp_path / "input.po"
    source.write_text(
        'msgid ""\nmsgstr "Plural-Forms: nplurals=2; plural=n!=1;\\n"\n\nmsgid "item"\nmsgid_plural "items"\nmsgstr[0] "one"\nmsgstr[1] "many"\n'
    )
    output = tmp_path / "out.po"
    with pytest.raises(ConversionLoss) as error:
        convert(source, "po", output, plural_forms="nplurals=2; plural=n==1;")
    assert "Plural-Forms" in {finding.data["field"] for finding in error.value.findings}
    assert not output.exists()
    result = convert(
        source, "po", output, plural_forms="nplurals=2; plural=n==1;", allow_loss=True
    )
    assert result.findings


def test_catalog_conversion_when_literal_icu_then_keep_the_complete_sentence(tmp_path):
    from vexy_localizzy.conversion import convert_catalog

    source = "Selected {n, plural, one {one file} other {{n} files}} today."
    target = "Heute {n, plural, =0 {keine Datei} one {eine Datei} other {{n} Dateien}} gewählt."
    catalog = Catalog(
        source_lang="en",
        target_lang="de",
        units=[
            Unit(
                key="selected",
                context="C",
                source=source,
                target=target,
                plural=PluralForms(
                    icu=target,
                    forms={
                        "zero": "keine Datei",
                        "one": "eine Datei",
                        "other": "{n} Dateien",
                    },
                ),
            )
        ],
    )
    result = convert_catalog(catalog, "ts", tmp_path / "out.ts", allow_loss=True)
    unit = ts.load(tmp_path / "out.ts").units[0]
    assert (unit.source, unit.target, unit.plural) == (source, target, None)
    assert any(f.data["field"] == "plural" for f in result.findings)
