# this_file: src/vexy_localizzy/sourcefix/prepare.py
"""Create a Linguist editing catalog and bind it to the original sources."""

import json
from pathlib import Path

from vexy_localizzy.formats import ts_xml
from vexy_localizzy.sourcefix.catalog import Catalog, active
from vexy_localizzy.sourcefix.files import commit, confined, digest


def state_path(mirror: Path) -> Path:
    return Path(str(mirror) + ".json")


def state_bytes(state: dict) -> bytes:
    return (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def prepare(source: str, out: str, root: str, verbose: bool = False) -> dict:
    """Create an English editing TS and OUT.json snapshot; never overwrite either.

    SOURCE is the original English catalog; OUT must be in the same directory.
    Edit translation fields in Qt Linguist and mark corrections finished.
    Plural entries remain unchanged and are not editable through this command.
    """
    root_path = Path(root).resolve(strict=True)
    source_path = confined(Path(source), root_path)
    out_path = confined(Path(out), root_path)
    snapshot = state_path(out_path)
    if out_path.parent != source_path.parent or out_path == source_path:
        raise ValueError(
            "Editing catalog must have a distinct name in the source catalog directory"
        )
    for path in (out_path, snapshot):
        if path.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing editing work: {path}"
            )
    catalog = Catalog(source_path)
    language = (
        catalog.tree.getroot().get("language", "").replace("-", "_").split("_")[0]
    )
    if language != "en":
        raise ValueError("Source corrections require an English catalog")
    source_files = {}
    excluded_files = set()
    missing_files = set()
    originals = {source_path: catalog.raw, out_path: None, snapshot: None}
    for locations in catalog.locations().values():
        for path, _ in locations:
            if not path.is_relative_to(root_path):
                excluded_files.add(str(path))
                continue
            if str(path) not in source_files:
                try:
                    raw = path.read_bytes()
                except FileNotFoundError:
                    missing_files.add(str(path))
                    continue
                source_files[str(path)] = digest(raw)
                originals[path] = raw
    count = plural = 0
    for _, message in catalog.records:
        if not active(message):
            continue
        if message.get("numerus") == "yes":
            plural += 1
            continue
        target = ts_xml.ensure_translation(message, "")
        if target.get("variants") == "yes":
            raise ValueError("English length variants require manual source editing")
        ts_xml.set_text(target, ts_xml.text(message.find("source"), ""), "")
        target.set("type", "unfinished")
        count += 1
    state = {
        "version": 1,
        "source": str(source_path),
        "root": str(root_path),
        "mirror": str(out_path),
        "source_sha256": digest(catalog.raw),
        "files": source_files,
        "excluded_files": sorted(excluded_files),
        "missing_files": sorted(missing_files),
    }
    commit({out_path: catalog.render(), snapshot: state_bytes(state)}, originals)
    return {
        "output": str(out_path),
        "snapshot": str(snapshot),
        "editable": count,
        "plurals_preserved": plural,
        "source_files": len(source_files),
        "external_files_not_editable": len(excluded_files),
        "missing_files_not_editable": len(missing_files),
    }
