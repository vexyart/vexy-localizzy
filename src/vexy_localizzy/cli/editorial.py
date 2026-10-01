# this_file: src/vexy_localizzy/cli/editorial.py
"""Fire-ready ``review`` and ``apply`` commands for editorial review of a translation.

``review`` asks a model for corrections to an already translated catalog and
appends them to a JSONL file; ``apply`` writes the accepted ones back with
staleness and shape guards and records an exact ledger. Exit codes: 0 success;
1 some review batches failed (re-run to resume); 2 usage or input error; 3 the
``llm`` (or ``translation``) extra is missing.
"""

import json
import sys
from pathlib import Path

from lxml.etree import LxmlError

from vexy_localizzy.cli._args import csv_paths, csv_strings
from vexy_localizzy.editorial.candidate_file import FAMILIES, SEVERITIES
from vexy_localizzy.editorial.review_prompt import DEFAULT_PRODUCT

EXIT_OK, EXIT_FAILED, EXIT_USAGE, EXIT_EXTRA = 0, 1, 2, 3
# Errors that mean bad input or flags: a clean message and exit 2, no traceback.
INPUT_ERRORS = (ValueError, OSError, LxmlError)


class UsageError(ValueError):
    """Invalid flags or configuration; exit code 2."""


def _text(value: object) -> str:
    """Free text; Fire splits ``--scope "A, B"`` into a tuple, so join it back."""
    if isinstance(value, list | tuple):
        return ", ".join(str(part) for part in value)
    return str(value)


def _path(value: object, flag: str) -> Path:
    """One path; Fire splits a name containing a comma, so join it back."""
    if isinstance(value, list | tuple):
        value = ",".join(str(part) for part in value)
    if value is None or not str(value).strip():
        raise UsageError(f"--{flag}: expected a path")
    return Path(str(value))


def _existing(value: object, flag: str) -> Path:
    path = _path(value, flag)
    if not path.is_file():
        raise UsageError(f"--{flag}: file does not exist: {path}")
    return path


def _positive(value: object, flag: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise UsageError(f"--{flag} must be a positive integer")
    return value


def _choices(value: object, allowed: tuple[str, ...], flag: str) -> set[str]:
    chosen = set(csv_strings(value))
    if unknown := chosen - set(allowed):
        raise UsageError(f"--{flag}: unknown value {sorted(unknown)}")
    if not chosen:
        raise UsageError(f"--{flag}: name at least one of {', '.join(allowed)}")
    return chosen


def _fail(error: Exception, code: int, hint: str = "") -> None:
    print(f"error: {error}{hint}", file=sys.stderr)
    raise SystemExit(code) from error


def review(
    catalog: str,
    target: str,
    out: str,
    model: str | None = None,
    endpoint: str | None = None,
    style_file: str | None = None,
    glossary_memory: str | None = None,
    product: str = DEFAULT_PRODUCT,
    source_json: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    temperature: float = 0.2,
    timeout: float = 300,
    workers: int = 4,
    batch_size: int = 40,
    limit: int = 0,
) -> dict:
    """Ask a model to review the --target translation in CATALOG; append proposals to OUT.

    The catalog is never edited. CATALOG is a Qt .ts file, or a translated JSON
    file with --source-json naming the English one. --product describes the
    application in a phrase ("a professional font editor"); --style-file is the
    language style sheet; --glossary-memory lists TMX memories, comma-separated,
    whose approved and do-not-translate terms are sent with each batch.
    --endpoint and --model are required; the key comes from --api-key-env.
    --timeout defaults to 300 seconds because a batch of 40 messages returns
    long corrected texts. Re-running skips batches already in OUT unless the
    items, model, prompt, style sheet or glossary terms changed. Messages with
    length variants are not reviewed (``apply`` cannot write them); they are
    counted under left_out. --limit reviews only the first N pending batches.
    """
    from vexy_localizzy.editorial.candidates import review_catalog
    from vexy_localizzy.editorial.review_request import endpoint_request

    try:
        if not endpoint or not model:
            raise UsageError("Pass --endpoint and --model")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise UsageError("--limit must be zero (no limit) or a positive integer")
        style = _existing(style_file, "style-file") if style_file else None
        options = {
            "glossaries": [
                _existing(p, "glossary-memory") for p in csv_paths(glossary_memory)
            ],
            "source_json": _existing(source_json, "source-json")
            if source_json
            else None,
            "workers": _positive(workers, "workers"),
            "batch_size": _positive(batch_size, "batch-size"),
        }
        request = endpoint_request(
            _text(endpoint),
            _text(model),
            api_key_env=_text(api_key_env),
            temperature=float(temperature),
            timeout=float(timeout),
        )
        summary = review_catalog(
            _existing(catalog, "catalog"),
            _text(target),
            _path(out, "out"),
            model=_text(model),
            request=request,
            product=_text(product),
            style=style.read_text(encoding="utf-8") if style else "",
            limit=limit,
            **options,
        )
    except ImportError as error:
        _fail(error, EXIT_EXTRA, "; install vexy-localizzy[llm]")
    except INPUT_ERRORS as error:
        _fail(error, EXIT_USAGE)
    if summary["failed"]:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        raise SystemExit(EXIT_FAILED)
    return summary


def apply(
    catalog: str,
    target: str,
    candidates: str,
    ledger: str,
    source_json: str | None = None,
    severity: str = ",".join(SEVERITIES),
    family: str = ",".join(FAMILIES),
    reject_ids: str | None = None,
    scope: str | None = None,
    dry_run: bool = False,
    allow_markup_changes: bool = False,
    finish: bool = False,
    force: bool = False,
) -> dict:
    """Apply accepted CANDIDATES (from ``review``) to CATALOG and write LEDGER.

    A correction lands only while CATALOG still holds the English source and
    translation the reviewer saw, and only if it keeps the source's
    placeholders, tags, trailing ellipsis or colon, surrounding whitespace,
    newlines and the translation's accelerator count. Stale and refused
    candidates are listed in the ledger; corrections already in the catalog
    count as already_applied. --severity and --family filter
    (comma-separated); --reject-ids names a file with one id per line to leave
    unchanged; --allow-markup-changes lets markup-family corrections change
    tags (nothing else). Qt messages keep their state unless --finish says a
    human accepted the candidates. --target is recorded as each change's
    language. The catalog and LEDGER are written together or not at all; an
    existing LEDGER is refused unless --force. --dry-run writes nothing.
    """
    from vexy_localizzy.editorial.apply import apply_review

    try:
        rejected = (
            set(_existing(reject_ids, "reject-ids").read_text(encoding="utf-8").split())
            if reject_ids
            else set()
        )
        return apply_review(
            _existing(catalog, "catalog"),
            _text(target),
            _existing(candidates, "candidates"),
            _path(ledger, "ledger"),
            source_json=_existing(source_json, "source-json") if source_json else None,
            severities=_choices(severity, SEVERITIES, "severity"),
            families=_choices(family, FAMILIES, "family"),
            rejected=rejected,
            scope=_text(scope) if scope else None,
            dry_run=bool(dry_run),
            allow_markup=bool(allow_markup_changes),
            finish=bool(finish),
            force=bool(force),
        )
    except INPUT_ERRORS as error:
        _fail(error, EXIT_USAGE)


EDITORIAL_COMMANDS = {"review": review, "apply": apply}


if __name__ == "__main__":
    import fire

    fire.Fire(EDITORIAL_COMMANDS)
