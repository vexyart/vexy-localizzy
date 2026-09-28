# this_file: tests/test_cli_translate.py
"""Fire parsing, exit codes and flag normalization of `localizzy translate`."""

import json
import sys
from pathlib import Path

import fire
import pytest

from vexy_localizzy.cli import translate as cli_translate
from vexy_localizzy.cli._args import csv_paths, csv_strings
from vexy_localizzy.cli.translate import translate
from vexy_localizzy.translate.types import TranslationResult

try:
    import vexy_localizzy.translate.abersetz_transport  # noqa: F401

    HAS_ABERSETZ = True
except ImportError:
    HAS_ABERSETZ = False
needs_abersetz = pytest.mark.skipif(not HAS_ABERSETZ, reason="needs abersetz")

FIXTURES = Path(__file__).parent / "fixtures" / "memory"
APP_DE = FIXTURES / "app_de.ts"
UI_DE = FIXTURES / "ui-de.tmx"
CORE_DE = FIXTURES / "core-de.tmx"

PLAIN_TS = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" sourcelanguage="en">
<context>
    <name>Menu</name>
    <message>
        <source>Save</source>
        <translation type="unfinished"></translation>
    </message>
</context>
</TS>
"""


def run(*argv: str):
    """Invoke through Fire; return (exit code, parsed stdout summary or None)."""
    try:
        result = fire.Fire(translate, command=list(argv))
    except SystemExit as exit:
        return exit.code, None
    return 0, result


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, []),
        ("a.tmx", ["a.tmx"]),
        ("a.tmx,b.tmx", ["a.tmx", "b.tmx"]),
        (("a.tmx", "b.tmx"), ["a.tmx", "b.tmx"]),
        (["a.tmx,b.tmx", "c.tmx"], ["a.tmx", "b.tmx", "c.tmx"]),
        (" a , ,b ", ["a", "b"]),
    ],
)
def test_csv_strings_when_string_tuple_or_none_then_flat_list(value, expected):
    assert csv_strings(value) == expected
    assert csv_paths(value) == [Path(v) for v in expected]


def test_translate_when_direct_memory_is_string_then_both_files_load(tmp_path):
    out = tmp_path / "x.ts"
    code, summary = run(
        str(APP_DE), "--target", "de", "--out", str(out),
        "--direct-memory", f"{UI_DE},{UI_DE}", "--memory-only",
    )  # fmt: skip
    assert code == 0 and summary["counts"]["memory_context"] == 2
    report = json.loads(Path(f"{out}.localizzy.json").read_text())
    assert report["memories"][0]["files"] == [str(UI_DE), str(UI_DE)]


def test_translate_when_direct_memory_is_tuple_then_both_files_load(tmp_path):
    out = tmp_path / "x.ts"
    code, _ = run(
        str(APP_DE), "--target=de", f"--out={out}",
        f"--direct-memory={UI_DE},{UI_DE}", "--memory-only",
    )  # fmt: skip
    assert code == 0
    report = json.loads(Path(f"{out}.localizzy.json").read_text())
    assert report["memories"][0]["files"] == [str(UI_DE), str(UI_DE)]


def test_translate_when_memory_only_and_units_remain_then_exit_one(tmp_path, capsys):
    code, _ = run(str(APP_DE), "--target", "de", "--out", str(tmp_path / "x.ts"),
                  "--memory-only")  # fmt: skip
    assert code == 1
    printed = json.loads(capsys.readouterr().out)
    assert printed["counts"]["pending"] == 3


def test_translate_when_no_endpoint_and_not_memory_only_then_exit_two(tmp_path):
    code, _ = run(str(APP_DE), "--target", "de", "--out", str(tmp_path / "x.ts"))
    assert code == 2
    assert not (tmp_path / "x.ts").exists()


@pytest.mark.parametrize(
    "extra",
    [
        ["--finish-on", "id,exact"],
        ["--provenance", "inline"],
        ["--plural-count", "two"],
        ["--memory-lang", "pl"],
    ],
)
def test_translate_when_flag_invalid_then_exit_two(tmp_path, extra):
    code, _ = run(str(APP_DE), "--target", "de", "--out", str(tmp_path / "x.ts"),
                  "--direct-memory", str(UI_DE), "--memory-only", *extra)  # fmt: skip
    assert code == 2


def test_translate_when_out_omitted_for_new_language_then_exit_two(tmp_path):
    source = tmp_path / "app.ts"
    source.write_text(PLAIN_TS, encoding="utf-8")
    assert run(str(source), "--target", "de", "--memory-only")[0] == 2
    assert source.read_text(encoding="utf-8") == PLAIN_TS


def test_translate_when_out_omitted_for_same_language_then_overwrite(tmp_path):
    source = tmp_path / "app_de.ts"
    source.write_bytes(APP_DE.read_bytes())
    code, summary = run(str(source), "--target", "de", "--direct-memory",
                        str(UI_DE), "--memory-only")  # fmt: skip
    assert code == 0 and summary["out"] == str(source)
    assert b"<translation>Sichern</translation>" in source.read_bytes()


def test_translate_when_nokeep_existing_then_existing_text_replaced(tmp_path):
    source = tmp_path / "app_de.ts"
    source.write_bytes(
        APP_DE.read_bytes().replace(
            b'<translation type="unfinished"></translation>',
            b"<translation>Alt</translation>",
            1,
        )
    )
    out = tmp_path / "x.ts"
    base = [str(source), "--target", "de", "--out", str(out), "--memory-only",
            "--direct-memory", str(UI_DE)]  # fmt: skip
    assert run(*base)[1]["counts"]["kept"] == 1
    assert b"Alt" in out.read_bytes()
    for flag in ("--nokeep-existing", "--keep-existing=False"):
        code, summary = run(*base, flag)
        assert code == 0 and summary["counts"]["kept"] == 0, flag
        assert b"<translation>Sichern</translation>" in out.read_bytes()


def test_translate_when_target_is_no_then_stays_a_string(tmp_path):
    source = tmp_path / "app.ts"
    source.write_text(PLAIN_TS, encoding="utf-8")
    out = tmp_path / "no.ts"
    code, _ = run(str(source), "--target", "no", "--out", str(out), "--memory-only")
    assert code == 1
    assert b'language="no"' in out.read_bytes()


def test_translate_when_glossary_status_includes_proposed_then_term_used(tmp_path):
    source = tmp_path / "app.ts"
    source.write_text(PLAIN_TS.replace("Save", "Font"), encoding="utf-8")
    out = tmp_path / "de.ts"
    base = [str(source), "--target", "de", "--out", str(out), "--memory-only",
            "--glossary-memory", str(CORE_DE)]  # fmt: skip
    assert run(*base)[0] == 1, "proposed terms are excluded by default"
    code, summary = run(*base, "--glossary-status", "approved,proposed")
    assert code == 0 and summary["counts"]["memory_term"] == 1


@needs_abersetz
def test_translate_when_endpoint_given_then_models_in_fallback_order(
    tmp_path, monkeypatch
):
    seen = []

    def fake_request(spec):
        seen.append(spec)

        def request(model, batch):
            return TranslationResult(
                targets={i.id: "DE " + i.source for i in batch.items},
                requested_model=model,
                reported_model=model,
            )

        return request

    monkeypatch.setattr(
        "vexy_localizzy.translate.engine.abersetz_request", fake_request
    )
    code, summary = run(
        str(APP_DE), "--target", "de", "--out", str(tmp_path / "x.ts"),
        "--endpoint", "http://fake.invalid/v1", "--model", "big",
        "--fallback-models", "small,tiny", "--temperature=1",
        "--cache", str(tmp_path / "c.sqlite"),
    )  # fmt: skip
    assert code == 0 and summary["counts"]["engine"] == 3
    assert seen[0].models == ("big", "small", "tiny")
    assert seen[0].temperature == 1.0
    assert (tmp_path / "c.sqlite").exists()


def test_translate_when_translation_extra_missing_then_exit_three(
    tmp_path, monkeypatch
):
    monkeypatch.setitem(
        sys.modules, "vexy_localizzy.translate.abersetz_transport", None
    )
    code, _ = run(str(APP_DE), "--target", "de", "--out", str(tmp_path / "x.ts"),
                  "--endpoint", "http://fake.invalid/v1", "--model", "m")  # fmt: skip
    assert code == cli_translate.EXIT_EXTRA == 3


@pytest.mark.parametrize(
    "extra",
    [["--glossary-status", "aproved"], ["--plural-count", "0"], ["--plural-count=7"]],
)
def test_translate_when_status_or_count_out_of_range_then_exit_two(tmp_path, extra):
    code, _ = run(str(APP_DE), "--target", "de", "--out", str(tmp_path / "x.ts"),
                  "--memory-only", *extra)  # fmt: skip
    assert code == 2
