# this_file: tests/test_readme_examples.py
"""Every ``localizzy`` command in README.md runs as written on synthetic fixtures."""

import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import fire
import pytest

from vexy_localizzy.cli import COMMANDS

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
README = (ROOT / "README.md").read_text(encoding="utf-8")
BLOCKS = re.findall(r"```sh\n(.*?)```", README, re.S)
EXAMPLES = [
    line.strip()
    for block in BLOCKS
    for line in block.splitlines()
    if line.strip().startswith("localizzy ")
]

PO = """msgid ""
msgstr ""
"Language: de\\n"
"X-Source-Language: en\\n"
"Content-Type: text/plain; charset=UTF-8\\n"

msgid "Open"
msgstr "Öffnen"
"""


def _copy(pairs: dict[str, Path], where: Path) -> None:
    for name, source in pairs.items():
        target = where / name
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy(source, target)


def setup_translate(where: Path) -> None:
    memory = FIXTURES / "memory"
    _copy(
        {
            "app_de.ts": memory / "app_de.ts",
            "de-ui.tmx": memory / "ui-de.tmx",
            "de-core.tmx": memory / "core-de.tmx",
        },
        where,
    )


def setup_upgrade(where: Path) -> None:
    upgrade = FIXTURES / "upgrade"
    _copy(
        {
            "fresh_de.ts": upgrade / "fresh.ts",
            "approved_de.ts": upgrade / "approved.ts",
        },
        where,
    )


def setup_convert(where: Path) -> None:
    (where / "de.po").write_text(PO, encoding="utf-8")


def setup_build_ui(where: Path) -> None:
    memory = FIXTURES / "memory"
    _copy({"de.ts": memory / "app_de.ts", "de-core.tmx": memory / "core-de.tmx"}, where)


def setup_ts2tmx(where: Path) -> None:
    _copy({"translations": FIXTURES / "legacy_golden" / "inputs" / "ts"}, where)


def setup_review(where: Path) -> None:
    example = ROOT / "examples" / "review_sample.py"
    subprocess.run(
        [sys.executable, str(example), str(where / "sample")],
        check=True,
        capture_output=True,
    )
    for path in (where / "sample").iterdir():
        shutil.move(str(path), where / path.name)


def setup_source_fix(where: Path) -> None:
    (where / "app.cpp").write_text('void Window::f() { tr("Old"); }\n')
    (where / "app_en.ts").write_text(
        '<TS version="2.1" language="en_US"><context>'
        '<name>Window</name><message><location filename="app.cpp" line="1"/>'
        '<source>Old</source><translation type="unfinished"/></message></context></TS>'
    )


def setup_nothing(where: Path) -> None:
    """Commands that need no input files."""


def setup_lookup(where: Path) -> None:
    memory = FIXTURES / "memory"
    (where / "memories").mkdir()
    _copy(
        {
            "app_en.ts": memory / "app_de.ts",
            "memories/de-ui.tmx": memory / "ui-de.tmx",
            "memories/de-core.tmx": memory / "core-de.tmx",
        },
        where,
    )


def setup_project(where: Path) -> None:
    upgrade = FIXTURES / "upgrade"
    (where / "i18n" / "fresh").mkdir(parents=True)
    _copy(
        {
            "i18n/app_de.ts": upgrade / "approved.ts",
            "i18n/fresh/app_de.ts": upgrade / "fresh.ts",
        },
        where,
    )
    (where / "localizzy.toml").write_text("[source]\nlocales = ['de']\n")


def setup_scan(where: Path) -> None:
    _copy({"src": FIXTURES / "qt"}, where)


def setup_vocab(where: Path) -> None:
    corpus = ROOT / "examples" / "vocabulary" / "translations.js"
    _copy({"translations.js": corpus}, where)


GROUPS = ("tm", "qt", "project", "editorial", "shard")

# command prefix -> (setup, allowed exit codes, outputs that must exist)
CASES = {
    "translate": (
        setup_translate,
        {0},
        ["app_de.new.ts", "app_de.new.ts.localizzy.json"],
    ),
    "upgrade": (
        setup_upgrade,
        {0, 1},
        ["de.ts", "de-retired.ts", "de.ts.upgrade.json"],
    ),
    "convert": (setup_convert, {0}, ["de.json"]),
    "tm build-ui": (setup_build_ui, {0}, ["de-ui.tmx"]),
    "tm ts2tmx": (setup_ts2tmx, {0}, ["tmx"]),
    "tm tmx2qph": (setup_translate, {0}, ["app_de.qph"]),
    "tm lookup": (
        setup_lookup,
        {0},
        ["app_en.ts.lookup.json", "app_en.ts.lookup.html"],
    ),
    "doctor": (setup_nothing, {0}, []),
    "init": (setup_nothing, {0}, ["localizzy.toml"]),
    "project upgrade": (setup_project, {0, 1}, ["i18n/app_de.new.ts"]),
    "qt scan": (setup_scan, {0, 1}, ["scan.sarif"]),
    "pseudo": (setup_translate, {0}, ["app_xx.ts"]),
    "qa": (setup_translate, {0, 1}, ["qa.sarif"]),
    "vocab": (setup_vocab, {0}, []),
    "tm tmx2html": (setup_translate, {0}, ["de-core.html"]),
    "review": (setup_review, {0}, []),
    "source-fix": (setup_source_fix, {0}, ["app_en_tofix.ts", "app_en_tofix.ts.json"]),
}


def _case(example: str) -> str:
    words = shlex.split(example)[1:]
    key = " ".join(words[:2]) if words[0] in GROUPS else words[0]
    assert key in CASES, f"README example without a test case: {example}"
    return key


def test_readme_when_parsed_then_has_exactly_the_documented_commands() -> None:
    assert sorted(_case(example) for example in EXAMPLES) == sorted(CASES)


@pytest.mark.parametrize("example", EXAMPLES)
def test_readme_example_when_run_then_succeeds_and_writes_outputs(
    example: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup, allowed, outputs = CASES[_case(example)]
    setup(tmp_path)
    monkeypatch.chdir(tmp_path)
    served: list[object] = []

    def fake_serve(config, port=8765, verbose=False, **options):
        from vexy_localizzy.review.server import load_app

        served.append(load_app(config))
        return {"config": str(config)}

    monkeypatch.setattr("vexy_localizzy.review.server.serve", fake_serve)
    code = 0
    try:
        fire.Fire(COMMANDS, command=shlex.split(example)[1:], name="localizzy")
    except SystemExit as exit_:
        code = exit_.code or 0
    assert code in allowed, f"{example} exited {code}"
    for name in outputs:
        assert (tmp_path / name).exists(), f"{example} did not write {name}"
    if _case(example) == "tm ts2tmx":
        assert list((tmp_path / "tmx").rglob("*.tmx")), "ts2tmx wrote no TMX"
    if _case(example) == "review":
        assert served, "review did not load its configuration"
