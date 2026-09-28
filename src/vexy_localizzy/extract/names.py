# this_file: src/vexy_localizzy/extract/names.py
"""Rename ``.tmx`` files under a folder to their shortest BCP 47 tag (legacy tmxnorm).

Planning rules live in ``vexy_localizzy.tmx_names`` (CLDR via ``langcodes`` and
``language_data``, needs the ``sources`` extra): canonicalize, drop a redundant
script, drop the most-populous territory, lowercase. Invalid stems are left
alone, collisions are reported and nothing is ever overwritten. Ported from
fl10n ``tools/tmxnorm.py``.
"""

import sys
from collections import defaultdict
from pathlib import Path

from loguru import logger

from vexy_localizzy import tmx_names

# Historical alias of the tmxnorm command: early .NET/Windows spelled Serbia
# ``SP`` (``sr-Cyrl-SP``); the ISO 3166-1 code is ``RS``.
TERRITORY_ALIASES = {"sp": "rs"}


def normalize_folder(
    root: str | Path,
    dry_run: bool = False,
    territory_aliases: dict[str, str] | None = None,
) -> dict:
    """Rename every ``.tmx`` under ``root``; return the renamed count and every planned row."""
    base = Path(root).expanduser().resolve()
    if not base.is_dir():
        raise SystemExit(f"Not a directory: {base}")
    by_folder: dict[Path, list[Path]] = defaultdict(list)
    for path in sorted(base.rglob("*.tmx")):
        by_folder[path.parent].append(path)
    rows: list[dict[str, str]] = []
    renamed = 0
    for folder, paths in by_folder.items():
        rel = folder.relative_to(base).as_posix() or "."
        plan = tmx_names.plan_folder(paths, territory_aliases=territory_aliases)
        for path, new_name, note in plan:
            if new_name is None:
                rows.append({"folder": rel, "old": path.name, "new": "", "note": note})
                continue
            if new_name == path.name:
                logger.debug(f"{rel}/{path.name}: already normalized")
                continue
            target = path.with_name(new_name)
            if target.exists() and not target.samefile(path):
                rows.append(
                    {
                        "folder": rel,
                        "old": path.name,
                        "new": new_name,
                        "note": "target exists, skipped",
                    }
                )
                continue
            rows.append({"folder": rel, "old": path.name, "new": new_name, "note": ""})
            if not dry_run:
                path.rename(target)
            renamed += 1
    logger.info(f"{'would rename' if dry_run else 'renamed'} {renamed} file(s)")
    return {"root": str(base), "dry_run": dry_run, "renamed": renamed, "rows": rows}


def norm(input: str, dry_run: bool = False, verbose: bool = False) -> dict:
    """Rename every ``.tmx`` under ``input`` to its shortest BCP 47 form (legacy tmxnorm).

    Args:
        input: Folder searched recursively (no default).
        dry_run: Report only, rename nothing.
        verbose: Debug logging.
    """
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "INFO")
    return normalize_folder(input, dry_run, TERRITORY_ALIASES)
