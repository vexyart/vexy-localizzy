# this_file: src/vexy_localizzy/review/workspace.py
"""Import a catalog into a resumable review workspace; never edit the source file.

``localizzy review catalog.ts`` needs no hand-written review TOML. The first
call snapshots the catalog (and any ``.ui`` previews) into ``<catalog>.review/``,
adds the editable plural slots the target language requires and writes the
TOML. A later call reopens the same workspace, and refuses when the inputs
changed, so reviewed work is never reset. The import is staged in a temporary
directory and renamed into place, so an interrupted run leaves nothing behind.
"""

import hashlib
import json
import tempfile
from collections.abc import Sequence
from pathlib import Path

from vexy_localizzy.catalog import Catalog
from vexy_localizzy.formats import json_io, ts
from vexy_localizzy.formats.ts_template import prepare_review
from vexy_localizzy.qa.catalog import shape_findings
from vexy_localizzy.qa.layers import native_plural_forms
from vexy_localizzy.review.journal import sync_directory
from vexy_localizzy.review.store import ReviewStore

SUFFIXES = (".ts", ".json")
ORIGIN_VERSION = 1
LOCK_TIMEOUT = 10  # seconds to wait for a concurrent import of the same workspace


def load_catalog(path: Path) -> Catalog:
    return ts.load(path) if path.suffix.lower() == ".ts" else json_io.load(path)


def _prepare(catalog: Catalog, forms: list[str]) -> Catalog:
    """Add missing editable plural slots; keep existing translations and variants."""
    if forms and catalog.document is not None and catalog.document.format == "ts":
        with tempfile.TemporaryDirectory(prefix="localizzy-review-") as temporary:
            current = Path(temporary) / "current.ts"
            ts.dump(catalog, current)
            prepared = prepare_review(current.read_bytes(), plural_count=len(forms))
        catalog = catalog.model_copy(update={"document": prepared.document})
    units = []
    for unit in catalog.units:
        active = unit.state != "vanished" and unit.source.strip()
        if active and unit.plural is not None and unit.plural.icu is None:
            missing = set(forms) - set(unit.plural.forms)
            filled = dict.fromkeys(forms, "") | unit.plural.forms
            plural = unit.plural.model_copy(update={"forms": filled})
            state = "needs_review" if missing else unit.state
            unit = unit.model_copy(update={"plural": plural, "state": state})
        if active and (issues := shape_findings(unit, tuple(forms) or None)):
            raise ValueError(
                "Prepare native target shape before review: "
                + "; ".join(finding.message for finding in issues)
            )
        units.append(unit)
    return catalog.model_copy(update={"units": units})


def _inputs(source: Path, ui_files: Sequence[str | Path]) -> tuple[dict, dict]:
    """The origin manifest and the bytes to snapshot, keyed by workspace file name."""
    previews = [Path(path).resolve(strict=True) for path in ui_files]
    if any(path.suffix.lower() != ".ui" for path in previews):
        raise ValueError("Review previews must be .ui files")
    contents = {"source" + source.suffix.lower(): source.read_bytes()}
    ui = []
    for index, path in enumerate(previews, start=1):
        name = f"ui/{index}-{path.name}"
        contents[name] = path.read_bytes()
        ui.append({"source": str(path), "file": name})
    origin = {
        "version": ORIGIN_VERSION,
        "source": str(source),
        "ui": ui,
        "hashes": {
            name: hashlib.sha256(raw).hexdigest() for name, raw in contents.items()
        },
    }
    return origin, contents


def _reopen(root: Path, origin: dict, *, check_ui: bool) -> Path:
    """Return the existing workspace TOML when its inputs are the ones given."""
    manifest = root / "origin.json"
    if not manifest.is_file():
        raise ValueError("Unrecognized review workspace; choose a new workspace")
    saved = json.loads(manifest.read_text(encoding="utf-8"))
    source_name = "source" + Path(origin["source"]).suffix.lower()
    hashes = saved.get("hashes") if isinstance(saved, dict) else None
    if (
        not isinstance(hashes, dict)
        or saved.get("version") != ORIGIN_VERSION
        or saved.get("source") != origin["source"]
        or hashes.get(source_name) != origin["hashes"][source_name]
        or (check_ui and saved != origin)
    ):
        raise ValueError("Review inputs changed; choose a new workspace")
    for name, digest in hashes.items():
        if not isinstance(name, str) or not isinstance(digest, str):
            raise ValueError("Invalid review workspace input hashes")
        path = (root / name).resolve(strict=True)
        if (
            not path.is_relative_to(root)
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise ValueError("Review input snapshot changed; choose a new workspace")
    return root / "review.toml"


def _stage(root: Path, origin: dict, contents: dict[str, bytes]) -> None:
    """Write the complete workspace into ``root`` (a staging directory)."""
    for name, raw in contents.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    catalog = load_catalog(root / ("source" + Path(origin["source"]).suffix.lower()))
    forms = list(native_plural_forms(catalog) or [])
    json_io.dump(_prepare(catalog, forms), root / "catalog.json")
    plural_forms = {"main": forms} if forms else {}
    ReviewStore(root, {"main": "catalog.json"}, plural_forms=plural_forms).open("main")
    settings = ['root = "."', "[catalogs]", 'main = "catalog.json"']
    if forms:
        settings += ["[plural_forms]", "main = " + json.dumps(forms)]
    settings.append("[ui_files]")
    settings += [
        f'"ui-{index}" = {json.dumps(item["file"])}'
        for index, item in enumerate(origin["ui"], start=1)
    ]
    (root / "review.toml").write_text("\n".join(settings) + "\n", encoding="utf-8")
    (root / "origin.json").write_text(
        json.dumps(origin, indent=2) + "\n", encoding="utf-8"
    )


def prepare_workspace(
    source: str | Path,
    *,
    workspace: str | Path | None = None,
    ui_files: Sequence[str | Path] = (),
) -> Path:
    """Import ``source`` into a workspace, or reopen it; return its review TOML."""
    from filelock import FileLock

    source = Path(source).resolve(strict=True)
    if source.suffix.lower() not in SUFFIXES:
        raise ValueError("Review accepts TS, canonical JSON or a review TOML")
    root = Path(workspace) if workspace is not None else Path(str(source) + ".review")
    if root.is_symlink():
        raise ValueError("Review workspace must not be a symbolic link")
    root = root.resolve()
    origin, contents = _inputs(source, ui_files)
    root.parent.mkdir(parents=True, exist_ok=True)
    lock = Path(str(root) + ".setup.lock")
    if lock.is_symlink() or (lock.exists() and lock.stat().st_nlink != 1):
        raise ValueError("Review setup lock must not alias another file")
    with FileLock(lock, timeout=LOCK_TIMEOUT):
        if root.exists():
            return _reopen(root, origin, check_ui=bool(ui_files))
        with tempfile.TemporaryDirectory(
            prefix=".localizzy-review-", dir=root.parent
        ) as work:
            stage = Path(work) / "workspace"
            stage.mkdir()
            _stage(stage, origin, contents)
            stage.rename(root)
            sync_directory(root.parent)
    return root / "review.toml"
