# this_file: src/vexy_localizzy/cli.py
"""Command-line entry points for generic catalog workflows."""

import sys
from pathlib import Path

import fire
from loguru import logger

from vexy_localizzy.conversion import convert as convert_catalog
from vexy_localizzy.inventory import write_inventory
from vexy_localizzy.source_extraction import extract


def inventory(root: str, output: str, verbose: bool = False) -> dict:
    """Inventory all .tmx and .ts XML catalogs recursively under ROOT."""
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "WARNING")
    directory = Path(root).resolve()
    if not directory.is_dir():
        raise ValueError(f"Input directory does not exist: {directory}")
    paths = sorted(
        path
        for path in directory.rglob("*")
        if path.suffix.lower() in {".tmx", ".ts"} and path.is_file()
    )
    return write_inventory(paths, Path(output), root=directory)


def convert(
    src: str,
    target: str,
    out: str,
    allow_loss: bool = False,
    plural_forms: str | None = None,
    plural_order: list[str] | None = None,
    source_format: str | None = None,
    source_lang: str | None = None,
    target_lang: str | None = None,
) -> dict:
    """Convert catalogs; use source_format=i18next for application JSON."""
    result = convert_catalog(
        src,
        target,
        out,
        allow_loss=allow_loss,
        plural_forms=plural_forms,
        plural_order=plural_order,
        source_format=source_format,
        source_lang=source_lang,
        target_lang=target_lang,
    )
    return {
        "output": str(result.out_path),
        "entries": len(result.catalog.units),
        "findings": [finding.model_dump() for finding in result.findings],
    }


def review(config: str, port: int = 8765, verbose: bool = False):
    """Serve configured catalogs with the optional review UI and API."""
    from vexy_localizzy.review_server import serve

    return serve(config, port=port, verbose=verbose)


def main() -> None:
    """Expose explicit subcommands through Python Fire."""
    fire.Fire(
        {
            "inventory": inventory,
            "convert": convert,
            "review": review,
            "extract": extract,
        }
    )
