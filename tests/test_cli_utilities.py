# this_file: tests/test_cli_utilities.py
"""Fire boundary of the utility commands: argument parsing, output and exit codes."""

import json
from pathlib import Path

import pytest

from vexy_localizzy.cli import utilities
from vexy_localizzy.formats.ts import load
from vexy_localizzy.translate import json_file, json_request
from vexy_localizzy.translate.provider_errors import ModelResponse


def ts(body: str, language: str = "fr_FR") -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n'
        f'<TS version="2.1" language="{language}" sourcelanguage="en">\n{body}</TS>\n'
    )


def context(name: str, source: str, target: str = "") -> str:
    return (
        f"<context><name>{name}</name><message><source>{source}</source>"
        f"<translation>{target}</translation></message></context>\n"
    )


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def exit_code(call) -> int:
    with pytest.raises(SystemExit) as caught:
        call()
    return caught.value.code


def test_diff_when_catalogs_then_markdown_printed_and_counts_returned(tmp_path, capsys):
    old = write(tmp_path / "old.ts", ts(context("A", "Open", "Ouvrir")))
    new = write(tmp_path / "new.ts", ts(context("A", "Save")))
    report = tmp_path / "out" / "report.json"
    counts = utilities.diff(str(old), str(new), report=str(report))
    assert (counts["removed"], counts["new_untranslated"]) == (1, 1), counts
    assert "## Removed from the fresh catalog (1)" in capsys.readouterr().out, (
        "the Markdown report is printed"
    )
    assert json.loads(report.read_text(encoding="utf-8"))["counts"] == counts, (
        "--report holds the same counts"
    )


def test_diff_when_file_missing_or_malformed_then_exit_2(tmp_path):
    new = write(tmp_path / "new.ts", ts(""))
    assert exit_code(lambda: utilities.diff(str(tmp_path / "x.ts"), str(new))) == 2, (
        "a missing catalog is a usage error"
    )
    bad = write(tmp_path / "bad.ts", "<TS><context>")
    assert exit_code(lambda: utilities.diff(str(bad), str(new))) == 2, "XML error"


def test_shard_split_when_parts_invalid_then_exit_2_else_rows(tmp_path):
    source = write(tmp_path / "app.ts", ts(context("A", "Open")))
    assert (
        exit_code(lambda: utilities.shard_split(str(source), str(tmp_path), 0)) == 2
    ), "--parts 0 is a usage error"
    result = utilities.shard_split(str(source), str(tmp_path / "s"), 2)
    assert len(result["shards"]) == 1, "one context fills one shard"


def test_shard_merge_when_unfilled_then_exit_1_then_2_then_force_0(tmp_path):
    en = write(
        tmp_path / "app_en.ts",
        ts(context("A", "Open") + context("B", "Save"), language="en"),
    )
    a = write(tmp_path / "a.ts", ts(context("A", "Open", "Ouvrir")))
    b = write(tmp_path / "b.ts", ts(context("B", "Save", "Enregistrer")))
    out = tmp_path / "app_fr.ts"

    def merge(shards, force=False):
        return utilities.shard_merge(str(en), shards, "fr_FR", 2, str(out), force)

    assert exit_code(lambda: merge(str(a))) == 1, "a partial merge is a failure"
    assert exit_code(lambda: merge(str(a))) == 2, "the output now exists"
    summary = merge((str(a), str(b)), force=True)
    assert summary["unfilled"] == 0, summary
    assert {u.target for u in load(out).units} == {"Ouvrir", "Enregistrer"}, (
        "the forced merge fills both messages"
    )


def test_shard_merge_when_no_shards_or_bad_language_then_exit_2(tmp_path):
    en = write(tmp_path / "en.ts", ts(context("A", "Open"), language="en"))
    out = str(tmp_path / "o.ts")
    assert exit_code(lambda: utilities.shard_merge(str(en), "", "fr", 2, out)) == 2, (
        "no shards is a usage error"
    )
    a = write(tmp_path / "a.ts", ts(context("A", "Open", "Ouvrir")))
    assert (
        exit_code(lambda: utilities.shard_merge(str(en), str(a), "??", 2, out)) == 2
    ), "an invalid language tag is a usage error"


def fake_request(spec):
    def request(system, payload):
        rows = json.loads(payload.split("\n\nItems:\n", 1)[1])
        items = [{"id": r["id"], "text": r["text"].upper()} for r in rows]
        return ModelResponse(json.dumps(items), "fake-model")

    return request


def test_translate_json_when_endpoint_or_model_missing_then_exit_2(tmp_path):
    source = write(tmp_path / "help.json", '{"a": "Alpha"}')
    out = str(tmp_path / "help_pl.json")
    code = exit_code(lambda: utilities.translate_json(str(source), "pl", out))
    assert code == 2, "no endpoint and no model"


def test_translate_json_when_transport_faked_then_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(json_file, "openai_request", fake_request)
    source = write(tmp_path / "help.json", '{"a": "Alpha", "b": "Beta"}')
    out = tmp_path / "help_pl.json"
    summary = utilities.translate_json(
        str(source),
        "pl",
        str(out),
        endpoint="http://localhost:1/v1",
        model="m",
        product="a drawing tool",
        batch_size=1,
        workers=1,
    )
    assert summary["complete"], summary
    assert json.loads(out.read_text(encoding="utf-8")) == {"a": "ALPHA", "b": "BETA"}, (
        "the translated file is written"
    )


def test_translate_json_when_batch_fails_then_exit_1(tmp_path, monkeypatch):
    def failing(spec):
        return lambda system, payload: ModelResponse("[]", "m")

    monkeypatch.setattr(json_file, "openai_request", failing)
    monkeypatch.setattr(json_request.time, "sleep", lambda _: None)
    source = write(tmp_path / "help.json", '{"a": "Alpha"}')
    out = tmp_path / "help_pl.json"
    code = exit_code(
        lambda: utilities.translate_json(
            str(source), "pl", str(out), endpoint="http://x", model="m"
        )
    )
    assert code == 1 and not out.exists(), "the output is never written with gaps"


def test_translate_json_when_titles_unpairable_then_exit_2(tmp_path, monkeypatch):
    monkeypatch.setattr(json_file, "openai_request", fake_request)
    source = write(tmp_path / "tips.json", '{"T1": "a", "T2": "b"}')
    out = write(tmp_path / "tips_pl.json", '{"PL T1": "a"}')
    code = exit_code(
        lambda: utilities.translate_json(
            str(source), "pl", str(out), endpoint="http://x", model="m", titles=True
        )
    )
    assert code == 2, "a titles file without sidecar and wrong length is refused"


def test_translate_json_when_glossary_status_unknown_then_exit_2(tmp_path):
    source = write(tmp_path / "help.json", '{"a": "Alpha"}')
    code = exit_code(
        lambda: utilities.translate_json(
            str(source),
            "pl",
            str(tmp_path / "o.json"),
            endpoint="http://x",
            model="m",
            glossary_status="approved,deprecated",
        )
    )
    assert code == 2, "an unknown glossary status is a usage error"


TMX = (
    '<?xml version="1.0" encoding="UTF-8"?><tmx version="1.4">'
    '<header srclang="en" datatype="plaintext" segtype="phrase" adminlang="en"'
    ' o-tmf="x" creationtool="t" creationtoolversion="1"/><body>'
    '<tu><prop type="x-status">approved</prop><tuv xml:lang="en"><seg>layer</seg>'
    '</tuv><tuv xml:lang="{lang}"><seg>{target}</seg></tuv></tu></body></tmx>'
)


def test_glossary_json_when_folder_and_codes_then_written(tmp_path):
    write(tmp_path / "de-core.tmx", TMX.format(lang="de", target="Ebene"))
    write(tmp_path / "pl-core.tmx", TMX.format(lang="pl", target="warstwa"))
    out = tmp_path / "glossary.json"
    summary = utilities.glossary_json(str(out), folder=str(tmp_path), codes="de,pl")
    assert summary["codes"] == ["de", "pl"], summary
    assert json.loads(out.read_text(encoding="utf-8")) == {
        "layer": {"de": "Ebene", "pl": "warstwa"}
    }, "terms from both memories"


def test_glossary_json_when_folder_memory_tagged_es_419_then_code_es(tmp_path):
    write(tmp_path / "es-core.tmx", TMX.format(lang="es-419", target="capa"))
    out = tmp_path / "glossary.json"
    utilities.glossary_json(str(out), folder=str(tmp_path), codes="es")
    assert json.loads(out.read_text(encoding="utf-8")) == {"layer": {"es": "capa"}}, (
        "the requested code keys the regional memory"
    )


def test_glossary_json_when_memory_files_then_codes_detected(tmp_path):
    pl = write(tmp_path / "terms.tmx", TMX.format(lang="pl", target="warstwa"))
    out = tmp_path / "g.json"
    assert utilities.glossary_json(str(out), memory=str(pl))["codes"] == ["pl"], (
        "the code is read from the memory"
    )


def test_glossary_json_when_both_or_neither_source_or_codes_mismatch_then_exit_2(
    tmp_path,
):
    pl = write(tmp_path / "pl-core.tmx", TMX.format(lang="pl", target="warstwa"))
    out = str(tmp_path / "g.json")
    assert exit_code(lambda: utilities.glossary_json(out)) == 2, "neither"
    both = lambda: utilities.glossary_json(out, memory=str(pl), folder=str(tmp_path))  # noqa: E731
    assert exit_code(both) == 2, "both"
    mismatch = lambda: utilities.glossary_json(out, memory=str(pl), codes="pl,de")  # noqa: E731
    assert exit_code(mismatch) == 2, "one code per memory"
    missing = lambda: utilities.glossary_json(out, folder=str(tmp_path), codes="fr")  # noqa: E731
    assert exit_code(missing) == 2, "a missing memory file"


def test_utility_commands_when_listed_then_fire_tree_shape():
    assert set(utilities.UTILITY_COMMANDS) == {
        "diff",
        "shard",
        "translate_json",
        "glossary_json",
    }, "top-level commands"
    assert set(utilities.UTILITY_COMMANDS["shard"]) == {"split", "merge"}, (
        "shard subcommands"
    )


def error_exit(capsys, call) -> tuple[int, str]:
    """Exit code and stderr of a CLI call that must fail cleanly."""
    code = exit_code(call)
    return code, capsys.readouterr().err


def test_diff_when_report_is_a_catalog_then_exit_2_untouched(tmp_path, capsys):
    old = write(tmp_path / "old.ts", ts(context("A", "Open", "Ouvrir")))
    new = write(tmp_path / "new.ts", ts(context("A", "Open")))
    before = old.read_bytes()
    code, err = error_exit(capsys, lambda: utilities.diff(str(old), str(new), str(old)))
    assert code == 2 and "would overwrite" in err, err
    assert old.read_bytes() == before, "the catalog is untouched"


def test_shard_split_when_shards_exist_then_exit_2_unless_force(tmp_path, capsys):
    source = write(tmp_path / "app.ts", ts(context("A", "Open"), language="en"))
    out = tmp_path / "s"
    utilities.shard_split(str(source), str(out), 1)
    code, err = error_exit(
        capsys, lambda: utilities.shard_split(str(source), str(out), 1)
    )
    assert code == 2 and "pass --force" in err, err
    result = utilities.shard_split(str(source), str(out), 1, force=True)
    assert len(result["shards"]) == 1, "force replaces the earlier split"


def test_shard_merge_when_shard_language_wrong_then_exit_2(tmp_path, capsys):
    en = write(tmp_path / "en.ts", ts(context("A", "Open"), language="en"))
    de = write(tmp_path / "de.ts", ts(context("A", "Open", "Öffnen"), "de_DE"))
    out = tmp_path / "o.ts"
    code, err = error_exit(
        capsys, lambda: utilities.shard_merge(str(en), str(de), "fr", 2, str(out))
    )
    assert code == 2 and "not fr" in err, err
    assert not out.exists(), "nothing written"


def test_translate_json_when_out_is_source_or_style_then_exit_2(tmp_path, capsys):
    source = write(tmp_path / "help.json", '{"a": "Alpha"}')
    style = write(tmp_path / "style.md", "Be brief.")
    for out in (source, style):
        before = out.read_bytes()
        code, err = error_exit(
            capsys,
            lambda out=out: utilities.translate_json(
                str(source),
                "pl",
                str(out),
                endpoint="http://x",
                model="m",
                style_file=str(style),
            ),
        )
        assert code == 2 and "overwrite an input" in err, err
        assert out.read_bytes() == before, f"{out.name} is untouched"


def test_translate_json_when_interrupted_then_exit_130(tmp_path, monkeypatch, capsys):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(json_file, "translate_json_file", interrupted)
    source = write(tmp_path / "help.json", '{"a": "Alpha"}')
    code, err = error_exit(
        capsys,
        lambda: utilities.translate_json(
            str(source), "pl", str(tmp_path / "o.json"), endpoint="http://x", model="m"
        ),
    )
    assert code == 130 and "partial" in err, err


def test_glossary_json_when_out_is_a_memory_then_exit_2_untouched(tmp_path, capsys):
    tmx = write(tmp_path / "fr-core.tmx", TMX.format(lang="fr", target="calque"))
    before = tmx.read_bytes()
    code, err = error_exit(
        capsys, lambda: utilities.glossary_json(str(tmx), memory=str(tmx))
    )
    assert code == 2 and "input memory" in err, err
    assert tmx.read_bytes() == before, "the memory is not replaced by {}"
    folder = lambda: utilities.glossary_json(str(tmx), folder=str(tmp_path), codes="fr")  # noqa: E731
    assert exit_code(folder) == 2, "the folder form is guarded too"
    assert tmx.read_bytes() == before, "still untouched"


@pytest.mark.parametrize(
    "case",
    [
        "bad_json",
        "bad_tmx_glossary",
        "missing_glossary",
        "missing_style",
        "tuple_out",
        "tuple_batch",
        "word_workers",
        "tuple_temperature",
    ],
)
def test_translate_json_when_inputs_or_flags_bad_then_clean_exit_2(
    case, tmp_path, capsys
):
    source = write(tmp_path / "help.json", '{"a": "Alpha"}')
    bad_tmx = write(tmp_path / "bad.tmx", "<tmx><body>")
    options = {"endpoint": "http://x", "model": "m"}
    out: object = str(tmp_path / "o.json")
    if case == "bad_json":
        source = write(tmp_path / "help.json", '{"a": ')
    options |= {
        "bad_tmx_glossary": {"glossary_memory": str(bad_tmx)},
        "missing_glossary": {"glossary_memory": (str(tmp_path / "none.tmx"),)},
        "missing_style": {"style_file": str(tmp_path / "none.md")},
        "tuple_batch": {"batch_size": (1, 2)},
        "word_workers": {"workers": "many"},
        "tuple_temperature": {"temperature": (0.1,)},
    }.get(case, {})
    if case == "tuple_out":
        out = ("a.json", "b.json")
    code, err = error_exit(
        capsys, lambda: utilities.translate_json(str(source), "pl", out, **options)
    )
    assert code == 2 and err.startswith("error:"), err
    assert "Traceback" not in err, err


@pytest.mark.parametrize(
    "case", ["bad_tmx", "missing_memory", "tuple_out", "tuple_folder"]
)
def test_glossary_json_when_inputs_or_flags_bad_then_clean_exit_2(
    case, tmp_path, capsys
):
    write(tmp_path / "de-core.tmx", "<tmx><body><tu>")
    calls = {
        "bad_tmx": lambda: utilities.glossary_json(
            str(tmp_path / "g.json"), folder=str(tmp_path), codes="de"
        ),
        "missing_memory": lambda: utilities.glossary_json(
            str(tmp_path / "g.json"), memory=(str(tmp_path / "x.tmx"),)
        ),
        "tuple_out": lambda: utilities.glossary_json(
            ("a.json", "b.json"), folder=str(tmp_path), codes=("de",)
        ),
        "tuple_folder": lambda: utilities.glossary_json(
            str(tmp_path / "g.json"), folder=("a", "b"), codes="de"
        ),
    }
    code, err = error_exit(capsys, calls[case])
    assert code == 2 and err.startswith("error:"), err


def test_glossary_json_when_codes_and_memory_are_tuples_then_parsed(tmp_path):
    de = write(tmp_path / "de.tmx", TMX.format(lang="de", target="Ebene"))
    pl = write(tmp_path / "pl.tmx", TMX.format(lang="pl", target="warstwa"))
    summary = utilities.glossary_json(
        str(tmp_path / "g.json"), memory=(str(de), str(pl)), codes=("de", "pl")
    )
    assert summary["codes"] == ["de", "pl"], "Fire tuples work like comma strings"


def test_diff_and_shard_when_malformed_or_tuple_then_clean_exit_2(tmp_path, capsys):
    good = write(tmp_path / "good.ts", ts(context("A", "Open")))
    not_ts = write(tmp_path / "x.ts", "<?xml version='1.0'?><html/>")
    for call in (
        lambda: utilities.diff(str(not_ts), str(good)),
        lambda: utilities.diff(str(good), str(good), report=("a", "b")),
        lambda: utilities.shard_split(str(not_ts), str(tmp_path / "s"), 2),
        lambda: utilities.shard_split(str(good), ("a", "b"), 2),
        lambda: utilities.shard_merge(
            str(good), str(not_ts), "fr", 2, str(tmp_path / "o.ts")
        ),
        lambda: utilities.shard_merge(
            str(good), str(good), "fr", "two", str(tmp_path / "o.ts")
        ),
    ):
        code, err = error_exit(capsys, call)
        assert code == 2 and err.startswith("error:"), err
