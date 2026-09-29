# this_file: src/vexy_localizzy/sourcefix/refresh.py
"""Rebuild catalogs against a staged source tree before committing any edits."""

import copy
import os
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

from vexy_localizzy.formats import ts_xml
from vexy_localizzy.sourcefix.catalog import Catalog, active, key
from vexy_localizzy.sourcefix.refresh_merge import (
    protect_line_spaces,
    retain_baseline,
    verify_translations,
)


def _overlay(root: Path, target: Path, changes: dict[Path, bytes]) -> None:
    """Only edited branches are real directories; other entries are read-only inputs."""
    target.mkdir()
    branches = defaultdict(dict)
    for relative, raw in changes.items():
        branches[relative.parts[0]][Path(*relative.parts[1:])] = raw
    for child in root.iterdir():
        out = target / child.name
        if child.name not in branches:
            out.symlink_to(child, target_is_directory=child.is_dir())
        elif child.is_dir():
            _overlay(child, out, branches[child.name])
        else:
            out.write_bytes(branches[child.name][Path(".")])


def _locations(
    catalog: Catalog,
    original: Path,
    overlay: Path | None = None,
    root: Path | None = None,
) -> bytes:
    """Seed absolute references; map extraction's staged references back to the project."""
    refs = catalog.locations()
    for context, message in catalog.records:
        for node, (path, line) in zip(
            message.findall("location"), refs[key(context, message)], strict=True
        ):
            if overlay is not None and path.is_relative_to(overlay):
                path = root / path.relative_to(overlay)
            node.set(
                "filename",
                os.path.relpath(path, original.parent) if overlay else str(path),
            )
            if line is not None:
                node.set("line", str(line))
    return catalog.render()


def _mirror(source: Catalog, previous: Catalog) -> bytes:
    for identity, message in previous.index.items():
        target = message.find("translation")
        text = ts_xml.text(target, "")
        if (
            identity[4] != "yes"
            and text not in {"", identity[1]}
            and identity not in source.index
        ):
            raise ValueError(
                f"Rebuild would retire an edited message; resolve its draft first: {identity}"
            )
    for context, message in source.records:
        if not active(message) or message.get("numerus") == "yes":
            continue
        target = ts_xml.ensure_translation(message, "")
        identity = key(context, message)
        old = previous.index.get(identity)
        if old is None:
            ts_xml.set_text(target, identity[1], "")
            target.set("type", "unfinished")
            continue
        old_target = old.find("translation")
        if old_target is not None:
            copied = copy.deepcopy(old_target)
            copied.tail = target.tail
            message.replace(target, copied)
        note = old.find("translatorcomment")
        if note is not None:
            existing = message.find("translatorcomment")
            if existing is not None:
                message.remove(existing)
            message.insert(
                message.index(message.find("translation")), copy.deepcopy(note)
            )
    return source.render()


def rebuild(
    outputs: dict[Path, bytes],
    catalogs: list[Catalog],
    state: dict,
    lupdate: str,
    originals: dict[Path, bytes | None],
) -> None:
    """Refresh every runtime TS and reconstruct the editor from the fresh English TS.

    The extraction roster is every available source referenced by the English
    catalog, including read-only external libraries. Missing inputs are retained
    as active baseline entries; a partial checkout is not deletion authority.
    Existing translations and approvals survive exactly. No original changes here.
    """
    root = Path(state["root"])
    english, editing = catalogs[:2]
    files = {p for refs in english.locations().values() for p, _ in refs if p.is_file()}
    for path in files:
        originals.setdefault(path, path.read_bytes())
    changed_sources = {
        p.relative_to(root): raw for p, raw in outputs.items() if p in files
    }
    with tempfile.TemporaryDirectory(prefix="localizzy-rebuild-") as directory:
        temp = Path(directory).resolve()
        overlay = temp / "sources"
        _overlay(root, overlay, changed_sources)
        staged = []
        for catalog in catalogs:
            if catalog is editing:
                continue
            prepared = Catalog(catalog.path, outputs.get(catalog.path, catalog.raw))
            target = temp / catalog.path.name
            target.write_bytes(_locations(prepared, catalog.path))
            staged.append((catalog, target, Catalog(target)))
        listing = temp / "sources.lst"
        listing.write_text(
            "\n".join(
                str(overlay / p.relative_to(root)) if p.is_relative_to(root) else str(p)
                for p in sorted(files)
            )
            + "\n"
        )
        command = [
            shutil.which(lupdate) or lupdate,
            "@" + str(listing),
            "-I",
            str(overlay),
            "-I",
            str(root),
            "-locations",
            "absolute",
            "-disable-heuristic",
            "similartext",
            "-disable-heuristic",
            "sametext",
            "-ts",
            *(str(path) for _, path, _ in staged),
        ]
        result = subprocess.run(
            command, cwd=root, capture_output=True, text=True, timeout=120
        )
        if result.returncode:
            raise ValueError(f"Catalog rebuild failed before writes: {result.stderr}")
        for catalog, path, previous in staged:
            merged = Catalog(path, retain_baseline(Catalog(path), previous))
            verify_translations(previous, merged)
            outputs[catalog.path] = _locations(merged, catalog.path, overlay, root)
    rebuilt = Catalog(english.path, outputs[english.path])
    prior_mirror = Catalog(editing.path, outputs.get(editing.path, editing.raw))
    outputs[editing.path] = _mirror(rebuilt, prior_mirror)
    for catalog in catalogs:
        outputs[catalog.path] = protect_line_spaces(
            Catalog(catalog.path, outputs[catalog.path])
        )
    # Every new source key becomes the next round's baseline and file snapshot.
    state["files"], external, missing = {}, set(), set()
    from vexy_localizzy.sourcefix.files import digest

    for refs in Catalog(english.path, outputs[english.path]).locations().values():
        for path, _ in refs:
            if not path.is_relative_to(root):
                external.add(str(path))
            elif path.is_file():
                raw = outputs.get(path, originals.get(path))
                if raw is None:
                    raw = path.read_bytes()
                    originals[path] = raw
                state["files"][str(path)] = digest(raw)
            else:
                missing.add(str(path))
    state["excluded_files"], state["missing_files"] = sorted(external), sorted(missing)
