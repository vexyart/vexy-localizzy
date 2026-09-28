# this_file: tests/fixtures/legacy_golden/capture.py
"""Regenerate golden outputs by running the OLD fl10n converter scripts.

Run with the fl10n virtual environment, never through the scripts' ``uv run -s``
shebang (that would resolve vexy-localizzy from PyPI):

    FL10N=/path/to/fl10n
    $FL10N/.venv/bin/python tests/fixtures/legacy_golden/capture.py $FL10N/tools [WORKDIR]

Every input is synthetic: text fixtures live in ``inputs/``; binary Adobe and
Apple resources are built by ``tests/extract/legacy_builders.py``. Each command
line is printed and recorded in ``commands.txt``.
"""

import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUTS = HERE / "inputs"
sys.path.insert(0, str(HERE.parents[1] / "extract"))
from legacy_builders import build_adobe, build_lproj  # noqa: E402

TMXNORM_NAMES = [
    "en-US.tmx",
    "de-DE.tmx",
    "de-AT.tmx",
    "sr-Cyrl-SP.tmx",
    "zh-TW.tmx",
    "zh-HK.tmx",
    "bs-Latn-BA.tmx",
    "es-MX.tmx",
    "junk_name.tmx",
    "pt.tmx",
    "pt-PT.tmx",
    "fr.tmx",
    "sub/en-GB.tmx",
    "sub/pa-PK.tmx",
    "sub/iw.tmx",
    "sub/nb-NO.tmx",
]


def build_tmxnorm(root: Path) -> Path:
    for name in TMXNORM_NAMES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
    return root


def listing(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*.tmx"))


WORK: list[Path] = [Path("/nonexistent")]


def run(log: list[str], tools: Path, script: str, *args: str) -> None:
    command = [sys.executable, str(tools / script), *args]
    shown = " ".join(
        a.replace(str(HERE), "$GOLDEN")
        .replace(str(tools), "$TOOLS")
        .replace(str(WORK[0]), "$WORK")
        for a in command[1:]
    )
    log.append(f"python {shown}")
    print(log[-1])
    subprocess.run(command, check=True)


def main(tools: Path, work: Path) -> None:
    log: list[str] = []
    for name in ("ts2tmx", "po2tmx", "lproj2tmx", "adobe2tmx", "oss2tmx", "tmxnorm"):
        shutil.rmtree(HERE / name, ignore_errors=True)
    WORK[0] = work
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    run(
        log,
        tools,
        "ts2tmx.py",
        "--input",
        str(INPUTS / "ts"),
        "--output",
        str(HERE / "ts2tmx/dir"),
    )
    run(
        log,
        tools,
        "ts2tmx.py",
        "--input",
        str(INPUTS / "ts/app_de.ts"),
        "--output",
        str(HERE / "ts2tmx/single/app_de.tmx"),
        "--src_lang",
        "en_GB",
    )
    run(
        log,
        tools,
        "po2tmx.py",
        "--input",
        str(INPUTS / "po"),
        "--output",
        str(HERE / "po2tmx/dir"),
    )
    run(
        log,
        tools,
        "po2tmx.py",
        "--input",
        str(INPUTS / "po"),
        "--output",
        str(HERE / "po2tmx/fuzzy"),
        "--fuzzy",
    )

    app = build_lproj(work / "Example.app")
    run(
        log,
        tools,
        "lproj2tmx.py",
        "--app",
        str(app),
        "--output",
        str(HERE / "lproj2tmx/default"),
    )
    run(
        log,
        tools,
        "lproj2tmx.py",
        "--app",
        str(app),
        "--output",
        str(HERE / "lproj2tmx/options"),
        "--dedupe=False",
        "--skip_identical",
        "--include_infoplist",
    )

    adobe = build_adobe(work / "Adobe Synthetic")
    run(
        log,
        tools,
        "adobe2tmx.py",
        "--input",
        str(adobe),
        "--output",
        str(HERE / "adobe2tmx/de"),
        "--ui_lang",
        "de_DE",
    )
    run(
        log,
        tools,
        "adobe2tmx.py",
        "--input",
        str(adobe),
        "--output",
        str(HERE / "adobe2tmx/auto"),
        "--dedupe=False",
        "--skip_identical",
        "--include_infoplist",
    )

    # oss2tmx clones with git; the driver swaps the registry and fetch() for local trees.
    sys.path.insert(0, str(tools))
    oss = importlib.import_module("oss2tmx")
    registry = tomllib.loads((HERE / "oss_registry.toml").read_text())["apps"]
    oss.APPS.clear()
    for name, spec in registry.items():
        source = spec.get("source_repo")
        oss.APPS[name] = oss.App(
            name,
            oss.Repo(
                spec["repo"]["url"],
                tuple(spec["repo"].get("paths", ())),
                spec["repo"].get("branch"),
            ),
            spec["glob"],
            spec.get("kind", "po"),
            oss.Repo(
                source["url"], tuple(source.get("paths", ())), source.get("branch")
            )
            if source
            else None,
            spec.get("ignore"),
        )
    oss.fetch = lambda repo, cache, refresh: (
        INPUTS / "oss" / repo.url.rsplit("/", 1)[-1].removesuffix(".git")
    )
    log.append(
        "oss2tmx.main(output=$GOLDEN/oss2tmx, cache=<tmp>) with APPS from oss_registry.toml and fetch -> inputs/oss/<repo>"
    )
    oss.main(output=str(HERE / "oss2tmx"), cache=str(work / "cache"))

    tmxnorm = importlib.import_module("tmxnorm")
    result = {}
    for mode, dry in (("dry_run", True), ("apply", False)):
        root = build_tmxnorm(work / f"tmxnorm-{mode}")
        log.append(f"tmxnorm.normalize(<tmp>/tmxnorm-{mode}, dry_run={dry})")
        renamed = tmxnorm.normalize(root, dry_run=dry)
        result[mode] = {"renamed": renamed, "files": listing(root)}
    (HERE / "tmxnorm").mkdir()
    (HERE / "tmxnorm/result.json").write_text(
        json.dumps({"inputs": TMXNORM_NAMES, **result}, indent=2) + "\n"
    )

    snapshot = {
        name: {
            "repo": [app.repo.url, list(app.repo.paths), app.repo.branch],
            "glob": app.glob,
            "kind": app.kind,
            "source_repo": [
                app.source_repo.url,
                list(app.source_repo.paths),
                app.source_repo.branch,
            ]
            if app.source_repo
            else None,
            "ignore": app.ignore,
        }
        for name, app in importlib.reload(oss).APPS.items()
    }
    (HERE / "legacy_apps.json").write_text(json.dumps(snapshot, indent=2) + "\n")
    (HERE / "commands.txt").write_text("\n".join(log) + "\n")


if __name__ == "__main__":
    work = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else Path(tempfile.mkdtemp(prefix="legacy-golden-"))
    )
    main(Path(sys.argv[1]).resolve(), work)
