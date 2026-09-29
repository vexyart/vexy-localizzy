# this_file: src/vexy_localizzy/sourcefix/apply.py
"""Validate and apply finished English copy edits as a single planned batch."""

import difflib
import json
from collections import Counter
from pathlib import Path

from vexy_localizzy.catalog import PLACEHOLDER_PATTERNS
from vexy_localizzy.formats import ts_xml
from vexy_localizzy.sourcefix import refresh
from vexy_localizzy.sourcefix.catalog import (
    Catalog,
    Key,
    rebase_locations,
    replace_source,
)
from vexy_localizzy.sourcefix.files import commit, confined, digest
from vexy_localizzy.sourcefix.prepare import state_bytes, state_path
from vexy_localizzy.sourcefix.progress import report
from vexy_localizzy.sourcefix.source import plan_sources


def _plural_text(message) -> list[str]:
    target = message.find("translation")
    if target is None:
        return []
    return [ts_xml.text(node, "") for node in target.findall("numerusform")]


def corrections(source: Catalog, mirror: Catalog) -> dict[Key, str]:
    if source.index.keys() != mirror.index.keys():
        raise ValueError(
            "Editing catalog identities differ: change translation fields only; do not edit sources or contexts"
        )
    edits = {}
    for identity, message in mirror.index.items():
        if identity[4] == "yes":
            if _plural_text(message) != _plural_text(source.index[identity]):
                raise ValueError(
                    f"Edited plural requires manual source/form review: {identity}"
                )
            continue
        target = message.find("translation")
        if target is None or target.get("type") == "unfinished":
            continue
        if target.get("variants") == "yes":
            raise ValueError(
                f"Length variants cannot be source corrections: {identity}"
            )
        new = ts_xml.text(target, "")
        if not new or new == identity[1]:
            continue
        for style in ("qt", "printf", "python_brace"):
            pattern = PLACEHOLDER_PATTERNS.get(style)
            if pattern and Counter(pattern.findall(identity[1])) != Counter(
                pattern.findall(new)
            ):
                raise ValueError(f"Correction changes {style} placeholders: {identity}")
        edits[identity] = new
    return edits


def _update_catalog(
    catalog: Catalog, edits: dict[Key, str], *, mirror: bool, english: bool
) -> None:
    # Check all destinations before mutating, including swaps and chains.
    for identity, new in edits.items():
        if identity not in catalog.index:
            continue
        destination = (identity[0], new, *identity[2:])
        if destination in catalog.index and destination != identity:
            raise ValueError(f"Message key collision in {catalog.path}: {destination}")
    destinations = [
        (k[0], new, *k[2:]) for k, new in edits.items() if k in catalog.index
    ]
    if len(set(destinations)) != len(destinations):
        raise ValueError(f"Correction key collision in {catalog.path}")
    for identity, new in edits.items():
        if identity in catalog.index:
            replace_source(catalog.index[identity], new, mirror=mirror, english=english)


def apply(
    mirror: str,
    source: str,
    root: str,
    dry_run: bool = False,
    verbose: bool = False,
    lupdate: str = "lupdate",
) -> dict:
    """Upstream finished English edits into sources and sibling TS catalogs.

    Use --dry-run to return a unified diff without writing. Empty, identical and
    unfinished translations are skipped. C++/headers and Qt UI XML are supported;
    unsupported or ambiguous sources, changed placeholders, plurals and stale
    snapshots fail before any writes. Other languages retain translations marked
    unfinished with oldsource. Keep the MIRROR.json preparation snapshot.
    """
    root_path = Path(root).resolve(strict=True)
    source_path = confined(Path(source), root_path)
    mirror_path = confined(Path(mirror), root_path)
    snapshot = confined(state_path(mirror_path), root_path)
    state_raw = snapshot.read_bytes()
    state = json.loads(state_raw)
    expected = {
        "version": 1,
        "source": str(source_path),
        "root": str(root_path),
        "mirror": str(mirror_path),
    }
    if any(state.get(k) != v for k, v in expected.items()):
        raise ValueError(
            "Preparation snapshot does not belong to this source, root and mirror"
        )
    report(f"Reading {source_path.name}")
    original = Catalog(source_path)
    if digest(original.raw) != state["source_sha256"]:
        raise ValueError(f"English catalog changed since preparation: {source_path}")
    report(f"Reading {mirror_path.name}")
    editing = Catalog(mirror_path)
    edits = corrections(original, editing)
    unfinished = sum(
        1
        for identity, message in editing.index.items()
        if identity[4] != "yes"
        and message.find("translation") is not None
        and message.find("translation").get("type") == "unfinished"
        and ts_xml.text(message.find("translation"), "") not in {"", identity[1]}
    )
    report(
        f"Found {len(edits)} finished correction(s); skipping {unfinished} unfinished edit(s)"
    )
    if verbose:
        for identity, new in edits.items():
            report(f"{identity[0]}: {identity[1]!r} -> {new!r}")
    if not edits:
        return {
            "edits": 0,
            "unfinished_edits": unfinished,
            "files": [],
            "dry_run": dry_run,
            "diff": "",
        }
    report("Resolving corrections against current sources with Qt lupdate")
    outputs, originals, shifts = plan_sources(original, edits, state, lupdate)
    originals.update(
        {source_path: original.raw, mirror_path: editing.raw, snapshot: state_raw}
    )
    catalogs = [original, editing]
    for path in sorted(source_path.parent.glob("*.ts")):
        path = confined(path, root_path)
        if path in {source_path, mirror_path} or state_path(path).exists():
            continue  # Other editing mirrors must keep their own snapshot.
        report(f"Reading {path.name}")
        catalogs.append(Catalog(path))
    for catalog in catalogs:
        report(f"Staging corrections in {catalog.path.name}")
        originals[catalog.path] = catalog.raw
        # Resolve/rebase while old identities still correspond to locations.
        rebase_locations(catalog, shifts)
        _update_catalog(
            catalog, edits, mirror=catalog is editing, english=catalog is original
        )
        raw = catalog.render()
        Catalog(catalog.path, raw)  # Parse outputs and reject duplicate keys.
        if raw != catalog.raw:
            outputs[catalog.path] = raw
    refresh.rebuild(outputs, catalogs, state, lupdate, originals)
    rebuilt_counts = {}
    for catalog in catalogs:
        report(f"Validating rebuilt {catalog.path.name}")
        fresh = Catalog(catalog.path, outputs.get(catalog.path, catalog.raw))
        rebuilt_counts[catalog.path.name] = {
            "active": len(fresh.index),
            "added": len(fresh.index.keys() - catalog.index.keys()),
            "retired": len(catalog.index.keys() - fresh.index.keys()),
        }
    state["source_sha256"] = digest(outputs[source_path])
    for path in list(state["files"]):
        if Path(path) in outputs:
            state["files"][path] = digest(outputs[Path(path)])
    outputs[snapshot] = state_bytes(state)
    diff = ""
    if dry_run:
        report("Generating preview diff; no files will be written")
        diff = "".join(
            "".join(
                difflib.unified_diff(
                    originals[path].decode("utf-8").splitlines(keepends=True),
                    raw.decode("utf-8").splitlines(keepends=True),
                    fromfile=str(path.relative_to(root_path)),
                    tofile=str(path.relative_to(root_path)),
                )
            )
            for path, raw in outputs.items()
            if path != snapshot
        )
    if not dry_run:
        commit(outputs, originals)
    return {
        "edits": len(edits),
        "unfinished_edits": unfinished,
        "rebuilt_catalogs": rebuilt_counts,
        "files": [str(p) for p in outputs],
        "dry_run": dry_run,
        "diff": diff if dry_run else "",
    }
