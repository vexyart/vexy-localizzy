# this_file: src/vexy_localizzy/extract/walk.py
"""File-or-directory job planning shared by the ts2tmx and po2tmx converters."""

from collections.abc import Callable
from pathlib import Path

from loguru import logger


def plan_jobs(input: Path, output: Path | None, suffix: str) -> list[tuple[Path, Path]]:
    """Return (source, destination.tmx) pairs for one file or a recursive folder.

    A file input writes to ``output`` or next to itself. A folder input mirrors
    its tree under ``output``, or writes next to each source when it is None.
    """
    if input.is_file():
        return [(input, output if output else input.with_suffix(".tmx"))]
    files = sorted(p for p in input.rglob(f"*{suffix}") if p.is_file())
    return [
        (
            p,
            (output / p.relative_to(input)).with_suffix(".tmx")
            if output
            else p.with_suffix(".tmx"),
        )
        for p in files
    ]


def convert_all(
    tool: str,
    root: Path,
    jobs: list[tuple[Path, Path]],
    convert: Callable[[Path, Path], tuple[str, int]],
) -> dict:
    """Run ``convert`` per job, keep going past failures, then exit 1 if any failed."""
    rows, total, failed = [], 0, 0
    for source, destination in jobs:
        try:
            lang, count = convert(source, destination)
        except Exception as exc:  # noqa: BLE001 - legacy tools report and continue
            failed += 1
            logger.error(f"{source}: {exc}")
            continue
        total += count
        name = source.relative_to(root) if root.is_dir() else source.name
        rows.append(
            {
                "input": str(name),
                "output": str(destination),
                "lang": lang,
                "units": count,
            }
        )
        logger.debug(f"{source} -> {destination} ({lang}, {count} units)")
    logger.info(
        f"{len(jobs) - failed}/{len(jobs)} files, {total} units, {failed} failed"
    )
    if failed:
        raise SystemExit(1)
    return {"tool": tool, "files": rows, "units": total, "failed": failed}
