# this_file: src/vexy_localizzy/cli.py
"""Command-line entry points for generic catalog workflows."""

import json
import sys
from pathlib import Path

import fire
from loguru import logger

from vexy_localizzy.cli_tm import TM_COMMANDS
from vexy_localizzy.cli_translate import translate
from vexy_localizzy.cli_upgrade import upgrade
from vexy_localizzy.conversion import convert as convert_catalog
from vexy_localizzy.inventory import write_inventory


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


def qa(catalog: str, fail_on: str = "major", plural_forms: str | None = None) -> dict:
    """Run the deterministic content checks on a catalog; exit 1 on blocking findings."""
    from vexy_localizzy.conversion import load_any
    from vexy_localizzy.qa import TextPolicy
    from vexy_localizzy.qa_catalog import check_catalog

    ranks = {"info": 0, "minor": 1, "major": 2, "critical": 3}
    if fail_on not in ranks:
        raise SystemExit(f"--fail_on must be one of {', '.join(ranks)}")
    loaded = load_any(catalog)
    required = tuple(str(plural_forms).split(",")) if plural_forms else None
    findings = check_catalog(
        loaded, policy=TextPolicy(), required_plural_forms=required
    )
    blocking = [f for f in findings if ranks[f.severity] >= ranks[fail_on]]
    result = {
        "catalog": str(catalog),
        "units": len(loaded.units),
        "findings": [f.model_dump() for f in findings],
        "blocking": len(blocking),
    }
    if blocking:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        raise SystemExit(1)
    return result


COMMANDS = {
    "translate": translate,
    "upgrade": upgrade,
    "convert": convert,
    "qa": qa,
    "review": review,
    "inventory": inventory,
    "tm": TM_COMMANDS,
}


def main() -> None:
    """Expose explicit subcommands through Python Fire.

    Hot-path verbs sit at the top level; the memory builders and converters are
    grouped under ``tm``. ``extract`` is ``localizzy tm extract`` now.
    """
    fire.Fire(COMMANDS)
