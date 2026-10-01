# this_file: tests/test_qa_layers.py
"""Optional QA layers: guards, the judge seam, plural derivation and the qa command."""

import json

import pytest

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.cli import checks
from vexy_localizzy.external import MissingDependencyError
from vexy_localizzy.formats import po
from vexy_localizzy.qa import layers


def _catalog(units, target="de"):
    return Catalog(source_lang="en", target_lang=target, units=units)


def _unit(key="k", source="A", target="A", state="translated", **extra):
    return Unit(
        key=key, context="C", source=source, target=target, state=state, **extra
    )


def test_run_pofilter_when_extra_missing_then_missing_dependency(monkeypatch):
    monkeypatch.setattr(layers, "extra_installed", lambda extra: False)
    with pytest.raises(MissingDependencyError, match="pofilter"):
        layers.run_pofilter(_catalog([_unit()]))


def test_run_qe_when_comet_missing_then_missing_dependency(monkeypatch):
    monkeypatch.setattr(layers.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(MissingDependencyError, match="COMET"):
        layers.run_qe(_catalog([]))


def test_run_judge_when_extra_missing_or_sample_invalid(monkeypatch):
    options = {"model": "m", "endpoint": "e", "api_key": "k"}
    with pytest.raises(ValueError, match="sample"):
        layers.run_judge(_catalog([_unit()]), sample=0, **options)
    monkeypatch.setattr(layers, "extra_installed", lambda extra: False)
    with pytest.raises(MissingDependencyError, match="openai"):
        layers.run_judge(_catalog([]), **options)


def test_run_judge_when_low_score_then_finding_and_approved_skipped(monkeypatch):
    seen = []

    def fake(unit, catalog, **kw):
        seen.append(unit.key)
        return {"score": 40, "errors": [{"category": "Fluency", "severity": "major"}]}

    monkeypatch.setattr(layers, "judge_unit", fake)
    catalog = _catalog(
        [_unit("a"), _unit("b", state="approved"), _unit("c"), _unit("d", target=None)]
    )
    findings = layers.run_judge(
        catalog, model="m", endpoint="e", api_key="k", sample=1.0, ignore_keys=["c"]
    )
    assert seen == ["a"], "approved, ignored and empty units are never judged"
    assert findings[0].rule_id == "MQM-LOW-SCORE" and findings[0].severity == "critical"
    assert findings[0].data["judge_model"] == "m", findings[0].data


def test_judge_unit_when_response_fenced_then_json_extracted(monkeypatch):
    from vexy_localizzy.translate import openai_transport
    from vexy_localizzy.translate.provider_errors import ModelResponse

    def fake(model, system, payload, **kw):
        assert json.loads(payload)["target_language"] == "de", payload
        return ModelResponse('```json\n{"score": 91, "errors": []}\n```', model)

    monkeypatch.setattr(openai_transport, "chat_request", fake)
    result = layers.judge_unit(
        _unit(), _catalog([]), model="m", system="s", endpoint="e", api_key="k"
    )
    assert result == {"score": 91, "errors": []}, result


def test_parse_pofilter_errors_when_multiline_and_non_ascii_then_mapped_to_unit():
    text = (
        'msgid ""\nmsgstr ""\n"Language: de\\n"\n\n'
        '# (pofilter) variables: mismatch\nmsgctxt "C"\nmsgid "Open %1"\nmsgstr "Öffnen"\n\n'
        '# (pofilter) printf: bad\n# (pofilter) escapes: bad\nmsgctxt "C"\n'
        'msgid ""\n"Café %1\\n"\n"second line"\nmsgstr "x"\n'
    )
    units = [_unit("a", "Open %1"), _unit("b", "Café %1\nsecond line")]
    findings = layers.parse_pofilter_errors(text, units)
    assert [(f.rule_id, f.unit_key) for f in findings] == [
        ("POFILTER-VARIABLES", "a"),
        ("POFILTER-PRINTF", "b"),
        ("POFILTER-ESCAPES", "b"),
    ], "multi-line and non-ASCII sources must map to their unit"


def test_write_po_when_category_plurals_then_header_and_plural_entry(tmp_path):
    plural = PluralForms(forms={"one": "{n} Datei", "other": "{n} Dateien"})
    catalog = _catalog(
        [
            _unit("menu.open", "Open", "Öffnen", notes=["A verb."]),
            _unit("n.files", "{n} files", None, plural=plural),
        ]
    )
    path = tmp_path / "de.po"
    layers._write_po(catalog, path)
    text = path.read_text(encoding="utf-8")
    assert "Plural-Forms: nplurals=2" in text and "msgid_plural" in text, text
    assert po.load(path).units[0].notes == ["A verb."], "notes survive the projection"


def test_native_plural_forms_when_indexed_category_or_absent():
    indexed = PluralForms(forms={"0": "a"}, indexing="index")
    named = PluralForms(forms={"one": "a"})
    polish = _catalog([_unit(plural=indexed, target=None)], target="pl_PL")
    assert layers.native_plural_forms(polish) == ("0", "1", "2"), "Qt numerus count"
    assert layers.native_plural_forms(_catalog([_unit(plural=named, target=None)])) == (
        "one",
        "other",
    )
    assert layers.native_plural_forms(_catalog([_unit()])) is None
    mixed = _catalog([_unit(plural=indexed, target=None), _unit("b", plural=named)])
    with pytest.raises(ValueError, match="Mixed"):
        layers.native_plural_forms(mixed)


TS = (
    '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n'
    '<TS version="2.1" language="pl" sourcelanguage="en"><context><name>C</name>'
    "<message><source>Open %1</source><translation>{open}</translation></message>"
    '<message numerus="yes"><source>%n file(s)</source><translation>'
    "<numerusform>%n plik</numerusform><numerusform>%n pliki</numerusform>{third}"
    "</translation></message></context></TS>\n"
)


def _ts(tmp_path, open="Otwórz %1", third="<numerusform>%n plików</numerusform>"):
    path = tmp_path / "app_pl.ts"
    path.write_text(TS.format(open=open, third=third), encoding="utf-8")
    return str(path)


def test_qa_command_when_auto_plurals_complete_then_clean(tmp_path):
    result = checks.qa(_ts(tmp_path), plural_forms="auto")
    assert result["blocking"] == 0 and result["units"] == 2, result


def test_qa_command_when_plural_form_missing_then_exit_1(tmp_path, capsys):
    with pytest.raises(SystemExit) as caught:
        checks.qa(_ts(tmp_path, third=""), plural_forms="auto")
    assert caught.value.code == 1
    assert "PLURAL-MISS" in capsys.readouterr().out, "the missing third form is named"


def _numerus_ts(tmp_path, lang, forms):
    body = "".join(f"<numerusform>{form}</numerusform>" for form in forms)
    path = tmp_path / f"app_{lang}.ts"
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n'
        f'<TS version="2.1" language="{lang}" sourcelanguage="en"><context>'
        '<name>C</name><message numerus="yes"><source>%n file(s)</source>'
        f"<translation>{body}</translation></message></context></TS>\n",
        encoding="utf-8",
    )
    return str(path)


@pytest.mark.parametrize(
    ("lang", "forms"),
    [
        ("ar", ["لا ملفات", "ملف واحد", "ملفان", "%n ملفات", "%n ملفًا", "%n ملف"]),
        ("pl", ["Jeden plik", "%n pliki", "%n plików"]),
        ("en_GB", ["One file", "%n files"]),
    ],
)
def test_qa_command_when_one_count_form_spells_out_the_number_then_clean(
    tmp_path, lang, forms
):
    result = checks.qa(_numerus_ts(tmp_path, lang, forms), plural_forms="auto")
    assert result["blocking"] == 0 and result["findings"] == [], result


@pytest.mark.parametrize(
    ("lang", "forms", "form"),
    [
        ("ar", ["لا ملفات", "ملف واحد", "ملفان", "ملفات", "%n ملفًا", "%n ملف"], "3"),
        ("ru", ["Один файл", "%n файла", "%n файлов"], "0"),
        ("ja", ["ファイル"], "0"),
    ],
)
def test_qa_command_when_form_of_several_counts_omits_the_count_then_exit_1(
    tmp_path, capsys, lang, forms, form
):
    with pytest.raises(SystemExit) as caught:
        checks.qa(_numerus_ts(tmp_path, lang, forms), plural_forms="auto")
    assert caught.value.code == 1, lang
    findings = json.loads(capsys.readouterr().out)["findings"]
    assert [(f["rule_id"], f["data"]["form"]) for f in findings] == [
        ("PH-MISMATCH", form)
    ], findings


def test_qa_command_when_sarif_requested_then_file_and_exit_1(tmp_path):
    out = tmp_path / "qa.sarif"
    with pytest.raises(SystemExit) as caught:
        checks.qa(
            _ts(tmp_path, open="Otwórz"),
            plural_forms="0,1,2",
            format="sarif",
            out=str(out),
        )
    assert caught.value.code == 1, "a lost placeholder blocks"
    run = json.loads(out.read_text())["runs"][0]
    assert any(rule["id"].startswith("PH-") for rule in run["tool"]["driver"]["rules"])
    uri = run["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"][
        "uri"
    ]
    assert uri.endswith("app_pl.ts"), "code scanning needs a file location"


def test_qa_command_when_layer_unknown_or_judge_unconfigured_then_exit_2(tmp_path):
    for layers_flag in ("spellcheck", "judge"):
        with pytest.raises(SystemExit) as caught:
            checks.qa(_ts(tmp_path), plural_forms="auto", layers=layers_flag)
        assert caught.value.code == 2, layers_flag


def test_qa_command_when_layer_dependency_missing_then_exit_3(tmp_path, monkeypatch):
    monkeypatch.setattr(layers, "extra_installed", lambda extra: False)
    with pytest.raises(SystemExit) as caught:
        checks.qa(_ts(tmp_path), plural_forms="auto", layers="pofilter")
    assert caught.value.code == 3, "a missing extra is exit 3, not a finding"


@pytest.mark.skipif(
    not (layers.extra_installed("pofilter") and layers.find_tool("pofilter").found),
    reason="needs the pofilter extra",
)
def test_run_pofilter_when_real_tool_then_placeholder_loss_reported():
    catalog = _catalog(
        [_unit(source="Open %1", target="Öffnen"), _unit("ok", "Save", "Sichern")]
    )
    rules = {finding.rule_id for finding in layers.run_pofilter(catalog)}
    assert "POFILTER-VARIABLES" in rules, f"pofilter must flag the lost %1: {rules}"
    assert all(f.unit_key == "k" for f in layers.run_pofilter(catalog)), (
        "only the bad unit"
    )


def test_qa_command_when_out_is_catalog_then_refused(tmp_path):
    catalog = _ts(tmp_path)
    before = open(catalog, "rb").read()
    with pytest.raises(SystemExit) as caught:
        checks.qa(catalog, plural_forms="auto", format="json", out=catalog)
    assert caught.value.code == 2 and open(catalog, "rb").read() == before


def test_qa_command_when_fail_on_unknown_then_exit_2(tmp_path):
    with pytest.raises(SystemExit) as caught:
        checks.qa(_ts(tmp_path), fail_on="fatal")
    assert caught.value.code == 2, "a bad flag value is a usage error, not exit 1"
