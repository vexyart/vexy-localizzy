# this_file: tests/extract/test_legacy_parity.py
"""Ported converters reproduce the outputs of the old fl10n scripts on synthetic inputs.

Goldens in ``tests/fixtures/legacy_golden`` were written by the fl10n tools
(see ``capture.py`` and ``commands.txt`` there). Files are compared as parsed
records (header srclang, tuid, props, segments, languages) and as filename
sets, not as bytes.
"""

import inspect
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import fire
import pytest
from legacy_builders import build_adobe, build_lproj

from vexy_localizzy.cli import tm as cli_tm
from vexy_localizzy.extract import adobe, lproj, names, oss, po2tmx, ts2tmx

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "legacy_golden"
INPUTS = GOLDEN / "inputs"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def parse(path: Path) -> dict:
    root = ET.parse(path).getroot()
    units = [
        {
            "tuid": tu.get("tuid"),
            "props": [(p.get("type"), p.text) for p in tu.findall("prop")],
            "segs": [
                (tuv.get(XML_LANG), tuv.findtext("seg")) for tuv in tu.findall("tuv")
            ],
        }
        for tu in root.iter("tu")
    ]
    return {
        "srclang": root.find("header").get("srclang"),
        "languages": sorted({lang for unit in units for lang, _ in unit["segs"]}),
        "units": units,
    }


def tree(root: Path) -> dict[str, dict]:
    return {
        p.relative_to(root).as_posix(): parse(p) for p in sorted(root.rglob("*.tmx"))
    }


def assert_parity(actual: Path, expected: Path) -> None:
    got, want = tree(actual), tree(expected)
    assert sorted(got) == sorted(want), (
        "Output filename set differs from the legacy tool"
    )
    assert want, f"Golden folder {expected} is empty"
    for name in want:
        assert got[name] == want[name], (
            f"{name}: parsed records differ from the legacy tool"
        )


def test_ts2tmx_when_folder_then_matches_legacy(tmp_path):
    result = ts2tmx.run(str(INPUTS / "ts"), str(tmp_path / "dir"))
    assert_parity(tmp_path / "dir", GOLDEN / "ts2tmx/dir")
    assert {row["input"]: row["lang"] for row in result["files"]} == {
        "French.ts": "fr-CA",
        "app_de.ts": "de",
        "scribus.fr.ts": "fr",
        "sub/app_pt_BR.ts": "pt-BR",
        "sub/zh_Hans.ts": "zh-CN",
    }, "Per-file target language must follow the legacy attribute/stem policy"


def test_ts2tmx_when_single_file_and_src_lang_then_matches_legacy(tmp_path):
    out = tmp_path / "single/app_de.tmx"
    ts2tmx.run(str(INPUTS / "ts/app_de.ts"), str(out), src_lang="en_GB")
    assert_parity(tmp_path / "single", GOLDEN / "ts2tmx/single")


@pytest.mark.parametrize("variant,fuzzy", [("dir", False), ("fuzzy", True)])
def test_po2tmx_when_folder_then_matches_legacy(tmp_path, variant, fuzzy):
    po2tmx.run(str(INPUTS / "po"), str(tmp_path / variant), fuzzy=fuzzy)
    assert_parity(tmp_path / variant, GOLDEN / "po2tmx" / variant)


@pytest.mark.parametrize(
    "variant,options",
    [
        ("default", {}),
        (
            "options",
            {"dedupe": False, "skip_identical": True, "include_infoplist": True},
        ),
    ],
)
def test_lproj2tmx_when_bundle_then_matches_legacy(tmp_path, variant, options):
    app = build_lproj(tmp_path / "Example.app")
    lproj.run(str(app), str(tmp_path / variant), **options)
    assert_parity(tmp_path / variant, GOLDEN / "lproj2tmx" / variant)


@pytest.mark.parametrize(
    "variant,options",
    [
        ("de", {"ui_lang": "de_DE"}),
        ("auto", {"dedupe": False, "skip_identical": True, "include_infoplist": True}),
    ],
)
def test_adobe2tmx_when_folder_then_matches_legacy(tmp_path, variant, options):
    root = build_adobe(tmp_path / "Adobe Synthetic")
    result = adobe.run(str(root), str(tmp_path / variant), **options)
    assert_parity(tmp_path / variant, GOLDEN / "adobe2tmx" / variant)
    assert result["zstring_language"] == ("de" if variant == "de" else "fr")


def local_fetch(repo: oss.Repo, cache: Path, refresh: bool) -> Path:
    return INPUTS / "oss" / repo.url.rsplit("/", 1)[-1].removesuffix(".git")


def test_oss2tmx_when_registry_override_then_matches_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(oss, "fetch", local_fetch)
    result = oss.run(
        str(tmp_path / "oss"),
        registry=str(GOLDEN / "oss_registry.toml"),
        cache=str(tmp_path / "cache"),
    )
    shutil.rmtree(tmp_path / "cache")
    assert_parity(tmp_path / "oss", GOLDEN / "oss2tmx")
    assert [app["app"] for app in result["apps"]] == [
        "synth-po",
        "synth-ts",
        "synth-moz",
    ]
    assert not (tmp_path / "oss/synth-po/ua.tmx").exists(), (
        "Zero-unit languages are removed"
    )


def test_oss2tmx_when_unknown_app_then_exit(tmp_path):
    with pytest.raises(SystemExit, match="Unknown apps"):
        oss.run(str(tmp_path), apps="nope", registry=str(GOLDEN / "oss_registry.toml"))


def test_oss_registry_when_packaged_then_equals_legacy_apps():
    snapshot = json.loads((GOLDEN / "legacy_apps.json").read_text())

    def repo(r: oss.Repo | None) -> list | None:
        return [r.url, list(r.paths), r.branch] if r else None

    assert {
        name: {
            "repo": repo(app.repo),
            "glob": app.glob,
            "kind": app.kind,
            "source_repo": repo(app.source_repo),
            "ignore": app.ignore,
        }
        for name, app in oss.load_registry().items()
    } == snapshot
    assert list(oss.APPS) == list(snapshot), (
        "Registry order sets the default processing order"
    )


def test_oss_registry_when_malformed_then_refuse(tmp_path):
    empty, bad = tmp_path / "empty.toml", tmp_path / "bad.toml"
    empty.write_text("# nothing\n")
    bad.write_text(
        '[apps.x]\nglob = "{lang}.po"\nkind = "svn"\n[apps.x.repo]\nurl = "u"\n'
    )
    with pytest.raises(ValueError, match="no \\[apps"):
        oss.load_registry(empty)
    with pytest.raises(ValueError):
        oss.load_registry(bad)


@pytest.mark.parametrize("mode,dry_run", [("dry_run", True), ("apply", False)])
def test_norm_when_folder_then_matches_legacy(tmp_path, mode, dry_run):
    golden = json.loads((GOLDEN / "tmxnorm/result.json").read_text())
    for name in golden["inputs"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
    result = names.norm(str(tmp_path), dry_run=dry_run)
    listing = sorted(
        p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*.tmx")
    )
    assert {"renamed": result["renamed"], "files": listing} == golden[mode]


def test_normalize_folder_when_no_aliases_then_sp_is_not_serbia(tmp_path):
    (tmp_path / "sr-Cyrl-SP.tmx").write_text("x")
    with_alias = names.normalize_folder(
        tmp_path, dry_run=True, territory_aliases=names.TERRITORY_ALIASES
    )
    without = names.normalize_folder(tmp_path, dry_run=True)
    assert with_alias["rows"][0]["new"] == "sr.tmx"
    assert without["rows"][0]["new"] != "sr.tmx", (
        "The SP alias is caller policy, not a default"
    )


def test_norm_when_not_directory_then_exit(tmp_path):
    with pytest.raises(SystemExit, match="Not a directory"):
        names.norm(str(tmp_path / "missing"))


@pytest.mark.parametrize(
    "command,module,function",
    [
        ("ts2tmx", "ts2tmx", "run"),
        ("po2tmx", "po2tmx", "run"),
        ("lproj2tmx", "lproj", "run"),
        ("adobe2tmx", "adobe", "run"),
        ("oss2tmx", "oss", "run"),
        ("norm", "names", "norm"),
    ],
)
def test_tm_commands_when_wrapped_then_signature_matches_run(command, module, function):
    import importlib

    target = getattr(
        importlib.import_module(f"vexy_localizzy.extract.{module}"), function
    )
    wrapper = cli_tm.TM_COMMANDS[command]
    assert inspect.signature(wrapper) == inspect.signature(target), (
        f"{command} drifted from {module}.{function}"
    )


def test_tm_commands_when_listed_then_expected_names():
    from vexy_localizzy.extract.single import extract

    assert list(cli_tm.TM_COMMANDS) == [
        "tmx2qph",
        "build_ui",
        "ts2tmx",
        "po2tmx",
        "lproj2tmx",
        "adobe2tmx",
        "oss2tmx",
        "norm",
        "extract",
    ]
    assert cli_tm.TM_COMMANDS["extract"] is extract


def test_tm_commands_when_called_through_fire_then_writes_tmx(tmp_path):
    out = tmp_path / "a.tmx"
    result = fire.Fire(
        cli_tm.TM_COMMANDS,
        command=["ts2tmx", str(INPUTS / "ts/app_de.ts"), "--output", str(out)],
    )
    assert result["units"] == 7 and out.is_file()
    assert parse(out) == parse(GOLDEN / "ts2tmx/dir/app_de.tmx")


def test_ts2tmx_when_one_file_fails_then_others_written_and_exit_1(tmp_path):
    source = tmp_path / "in"
    source.mkdir()
    shutil.copy(INPUTS / "ts/app_de.ts", source / "good_de.ts")
    (source / "bad_de.ts").write_text("<TS><context>")
    with pytest.raises(SystemExit) as info:
        ts2tmx.run(str(source), str(tmp_path / "out"))
    assert info.value.code == 1
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["good_de.tmx"]


@pytest.mark.parametrize("module,suffix", [(ts2tmx, ".ts"), (po2tmx, ".po")])
def test_walkers_when_input_missing_or_empty_then_exit(tmp_path, module, suffix):
    with pytest.raises(SystemExit, match="input not found"):
        module.run(str(tmp_path / "missing"))
    with pytest.raises(SystemExit, match=f"no \\{suffix} files"):
        module.run(str(tmp_path))
