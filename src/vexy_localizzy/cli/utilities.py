# this_file: src/vexy_localizzy/cli/utilities.py
"""Fire-ready utility commands: catalog diff, shards, JSON-file translation, glossary JSON.

Each command parses Fire values at the boundary and imports its module on
call, so the CLI loads without optional extras. Exit codes follow
``localizzy translate``: 0 success; 1 not complete (unfilled merge messages,
untranslated JSON items); 2 usage or input error; 3 the ``translation`` extra
is missing.
"""

import json
import sys
from pathlib import Path
from typing import get_args

from vexy_localizzy.cli._args import csv_paths, csv_strings
from vexy_localizzy.cli.translate import (
    EXIT_EXTRA,
    EXIT_PENDING,
    EXIT_USAGE,
    TermStatus,
    UsageError,
    _language,
)

EXIT_INTERRUPTED = 130  # 128 + SIGINT, as shells report Ctrl+C
# XMLSyntaxError is a SyntaxError, not a ValueError.
INPUT_ERRORS = (ValueError, OSError, SyntaxError)


def _fail(error: Exception, code: int = EXIT_USAGE) -> SystemExit:
    print(f"error: {error}", file=sys.stderr)
    return SystemExit(code)


def _pending(summary: dict) -> SystemExit:
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return SystemExit(EXIT_PENDING)


def _path(value: object, what: str) -> Path:
    """One path; Fire turns ``a,b`` into a tuple, which is a usage error here."""
    if isinstance(value, list | tuple | dict) or value is None or value == "":
        raise UsageError(f"{what} takes one path, got {value!r}")
    return Path(str(value))


def _number(value: object, what: str, kind: type, minimum: float) -> int | float:
    """``value`` as ``kind`` (int or float) and at least ``minimum``."""
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise UsageError(f"{what} must be a number, got {value!r}")
    try:
        number = kind(value)
    except ValueError as error:
        raise UsageError(f"{what} must be a number, got {value!r}") from error
    if number < minimum:
        raise UsageError(f"{what} must be at least {minimum}")
    return number


def _file(value: object, what: str) -> Path:
    path = _path(value, what)
    if not path.is_file():
        raise UsageError(f"{what} does not exist: {path}")
    return path


def _statuses(value: object) -> frozenset[str]:
    statuses = frozenset(csv_strings(value))
    if unknown := statuses - set(get_args(TermStatus)):
        raise UsageError(f"--glossary-status: unknown status {sorted(unknown)}")
    return statuses


def diff(old: str, new: str, report: str | None = None) -> dict:
    """Compare approved catalog OLD with fresh catalog NEW; print a Markdown report.

    Messages pair as ``localizzy upgrade`` pairs them (message id, else context,
    source and comment). --report also writes the full report as JSON. Returns
    the counts. A --report that is OLD or NEW is refused.
    """
    from vexy_localizzy.formats.document import atomic_write
    from vexy_localizzy.upgrade.diff import compare, render

    try:
        old_path, new_path = _file(old, "Old catalog"), _file(new, "New catalog")
        path = _path(report, "--report") if report else None
        if path and path.resolve() in {old_path.resolve(), new_path.resolve()}:
            raise UsageError(f"--report {path} would overwrite a catalog")
        result = compare(old_path, new_path)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(result, ensure_ascii=False, indent=1) + "\n"
            atomic_write(path, text.encode("utf-8"))
    except INPUT_ERRORS as error:
        raise _fail(error) from error
    print(render(result))
    return result["counts"]


def shard_split(source: str, out_dir: str, parts: int = 4, force: bool = False) -> dict:
    """Split catalog SOURCE into --parts shards in OUT_DIR, keeping contexts whole.

    OUT_DIR holding shards of SOURCE (<stem>-shard*.ts) is refused unless
    --force, which first removes the earlier <stem>-shard<N>.ts files.
    """
    from vexy_localizzy.formats.ts_shards import split

    if isinstance(parts, bool) or not isinstance(parts, int) or parts < 1:
        raise _fail(UsageError("--parts must be a positive integer"))
    try:
        shards = split(
            _file(source, "Catalog"),
            _path(out_dir, "OUT_DIR"),
            parts,
            force=bool(force),
        )
    except INPUT_ERRORS as error:
        raise _fail(error) from error
    return {"source": str(source), "shards": shards}


def shard_merge(
    source: str,
    shards: str,
    target: str,
    plural_count: int,
    out: str,
    force: bool = False,
) -> dict:
    """Fill the --target template of SOURCE from translated SHARDS into --out.

    SHARDS is comma-separated. An existing --out is refused unless --force; an
    --out that is an input, or a shard in another language, is refused. Exits 1 when a message stays unfilled; the catalog is still written.
    """
    from vexy_localizzy.formats.ts_shards import merge

    try:
        paths = [_file(path, "Shard") for path in csv_paths(shards)]
        if not paths:
            raise UsageError("Pass at least one shard")
        summary = merge(
            _file(source, "Catalog"),
            paths,
            target=_language(target, "target"),
            plural_count=plural_count,
            out=_path(out, "--out"),
            force=bool(force),
        )
    except INPUT_ERRORS as error:
        raise _fail(error) from error
    if summary["unfilled"]:
        raise _pending(summary)
    return summary


def _engine(endpoint, model, api_key_env, temperature, timeout):
    from vexy_localizzy.translate.engine import EngineSpec

    if not endpoint or not model:
        raise UsageError("Pass --endpoint and --model")
    return EngineSpec(
        endpoint=str(endpoint),
        models=(str(model),),
        api_key_env=str(api_key_env),
        temperature=_number(temperature, "--temperature", float, 0),
        timeout=_number(timeout, "--timeout", float, 0),
    )


def _glossary(paths, statuses, source_lang, target):
    from vexy_localizzy.memory.glossary import Glossary

    if not paths:
        return None
    return Glossary.load(
        paths, source_lang=source_lang, target_lang=target, statuses=statuses
    )


def translate_json(
    source: str,
    target: str,
    out: str,
    endpoint: str | None = None,
    model: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    temperature: float = 0.2,
    timeout: float = 120,
    style_file: str | None = None,
    glossary_memory: str | None = None,
    glossary_status: str = "approved,do-not-translate",
    source_lang: str = "en",
    product: str | None = None,
    titles: bool = False,
    batch_size: int = 5,
    workers: int = 3,
) -> dict:
    """Translate flat JSON file SOURCE ({key: Markdown text}) into --target at --out.

    --titles: the keys are English titles and are translated too. --product
    describes what the texts document (default: a software application).
    --glossary-memory a.tmx,b.tmx adds the terms each batch mentions. Resume is
    by English key; provenance goes to OUT's ``.localizzy.json`` sidecar. Exits
    1, leaving --out untouched, until every item is translated; finished batches
    are kept in OUT's ``.partial.json`` after each batch. Ctrl+C exits 130. An
    --out (or its sidecar or partial file) that is an input is refused.
    """
    try:
        from vexy_localizzy.translate.json_file import (
            DEFAULT_PRODUCT,
            translate_json_file,
        )

        target = _language(target, "target")
        source_lang = _language(source_lang, "source-lang")
        style_path = _file(style_file, "Style file") if style_file else None
        style = style_path.read_text(encoding="utf-8") if style_path else ""
        summary = translate_json_file(
            _file(source, "Source file"),
            _path(out, "OUT"),
            spec=_engine(endpoint, model, api_key_env, temperature, timeout),
            target_lang=target,
            source_lang=source_lang,
            style=style,
            glossary=_glossary(
                csv_paths(glossary_memory),
                _statuses(glossary_status),
                source_lang,
                target,
            ),
            product=str(product) if product else DEFAULT_PRODUCT,
            titles=bool(titles),
            batch_size=_number(batch_size, "--batch-size", int, 1),
            workers=_number(workers, "--workers", int, 1),
            protected=[style_path] if style_path else [],
        )
    except KeyboardInterrupt:
        print("interrupted; finished batches are in the partial file", file=sys.stderr)
        raise SystemExit(EXIT_INTERRUPTED) from None
    except ImportError as error:
        print(f"error: {error}; install vexy-localizzy[translation]", file=sys.stderr)
        raise SystemExit(EXIT_EXTRA) from error
    except INPUT_ERRORS as error:
        raise _fail(error) from error
    if not summary["complete"]:
        raise _pending(summary)
    return summary


def glossary_json(
    out: str,
    memory: str | None = None,
    folder: str | None = None,
    pattern: str = "{code}-core.tmx",
    codes: str | None = None,
    source_lang: str = "en",
    glossary_status: str = "approved,do-not-translate",
) -> dict:
    """Write a {source term: {code: translation}} JSON view of glossary memories to OUT.

    Either --memory a.tmx,b.tmx (codes read from each memory, or given by --codes
    in the same order), or --folder DIR with --codes de,pl and --pattern
    (default {code}-core.tmx). An OUT that is one of the memories is refused.
    """
    from vexy_localizzy.memory.glossary_json import memory_paths, write_glossary_json

    try:
        names = csv_strings(codes)
        if bool(memory) == bool(folder):
            raise UsageError("Pass exactly one of --memory and --folder")
        if folder:
            memories = memory_paths(_path(folder, "--folder"), str(pattern), names)
        else:
            paths = csv_paths(memory)
            if names and len(names) != len(paths):
                raise UsageError("--codes must name one code per --memory file")
            memories = list(zip(names or [None] * len(paths), paths))
        return write_glossary_json(
            _path(out, "OUT"),
            memories,
            source_lang=_language(source_lang, "source-lang"),
            statuses=_statuses(glossary_status),
        )
    except INPUT_ERRORS as error:
        raise _fail(error) from error


UTILITY_COMMANDS = {
    "diff": diff,
    "shard": {"split": shard_split, "merge": shard_merge},
    "translate_json": translate_json,
    "glossary_json": glossary_json,
}
