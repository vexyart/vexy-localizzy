# this_file: src/vexy_localizzy/cli/translate.py
"""Fire command `localizzy translate`: memories first, then an optional engine.

Exit codes: 0 success; 1 pending units remain; 2 usage or configuration error;
3 the ``translation`` extra is missing. The printed summary is the same for 0 and 1.
"""

import json
import sys
from pathlib import Path
from typing import Literal, get_args

from vexy_localizzy.cli._args import csv_paths, csv_strings
from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.memory.direct import MatchClass

TermStatus = Literal["approved", "proposed", "do-not-translate"]

EXIT_OK, EXIT_PENDING, EXIT_USAGE, EXIT_EXTRA = 0, 1, 2, 3


class UsageError(ValueError):
    """Invalid flags or configuration; exit code 2."""


def _classes(value: object, flag: str) -> frozenset[str]:
    classes = frozenset(csv_strings(value))
    if unknown := classes - set(get_args(MatchClass)):
        raise UsageError(f"--{flag}: unknown match class {sorted(unknown)}")
    return classes


def _language(value: object, flag: str) -> str:
    text = str(value).strip()
    try:
        canonical_locale(text)
    except Exception as error:  # noqa: BLE001 - langcodes raises several types
        raise UsageError(f"--{flag}: invalid language tag {text!r}") from error
    return text


def _options(
    catalog,
    target,
    out,
    direct_memory,
    glossary_memory,
    memory_lang,
    glossary_status,
    finish_on,
    memory_only,
    plural_count,
    keep_existing,
    provenance,
    endpoint,
    model,
    fallback_models,
    api_key_env,
    cache,
    temperature,
    timeout=120,
):
    """Parse Fire values into ``translate_file`` keyword arguments."""
    from vexy_localizzy.formats.ts_read import load
    from vexy_localizzy.translate.engine import EngineSpec
    from vexy_localizzy.translate.run import MemoryPolicy, same_language

    source = Path(str(catalog))
    if not source.is_file():
        raise UsageError(f"Catalog does not exist: {source}")
    target = _language(target, "target")
    if out is None:
        if source.suffix.lower() != ".ts" or not same_language(
            load(source).target_lang, canonical_locale(target)
        ):
            raise UsageError("--out is required unless a TS catalog keeps its language")
        out = source
    if str(provenance) not in ("sidecar", "extra"):
        raise UsageError("--provenance must be sidecar or extra")
    engine = None
    if not memory_only:
        models = [
            str(m) for m in ([model] if model else []) + csv_strings(fallback_models)
        ]
        if not endpoint or not models:
            raise UsageError("Pass --endpoint and --model, or --memory-only")
        engine = EngineSpec(
            endpoint=str(endpoint),
            models=tuple(dict.fromkeys(models)),
            api_key_env=str(api_key_env),
            temperature=float(temperature),
            timeout=float(timeout),
        )
    if plural_count is not None and (
        isinstance(plural_count, bool)
        or not isinstance(plural_count, int)
        or not 1 <= plural_count <= 6
    ):
        raise UsageError("--plural-count must be an integer from 1 through 6")
    statuses = frozenset(csv_strings(glossary_status))
    if unknown := statuses - set(get_args(TermStatus)):
        raise UsageError(f"--glossary-status: unknown status {sorted(unknown)}")
    return {
        "catalog": source,
        "target": target,
        "out": Path(str(out)),
        "direct_memories": csv_paths(direct_memory),
        "glossary_memories": csv_paths(glossary_memory),
        "memory_lang": _language(memory_lang, "memory-lang") if memory_lang else None,
        "glossary_statuses": statuses,
        "engine": engine,
        "cache_path": Path(str(cache)) if cache else None,
        "plural_count": plural_count,
        "keep_existing": bool(keep_existing),
        "policy": MemoryPolicy(
            finish_on=_classes(finish_on, "finish-on"),
            use=frozenset(get_args(MatchClass)),
        ),
        "provenance": str(provenance),
    }


def translate(
    catalog: str,
    target: str,
    out: str | None = None,
    report: str | None = None,
    direct_memory: str | None = None,
    glossary_memory: str | None = None,
    memory_lang: str | None = None,
    glossary_status: str = "approved,do-not-translate",
    finish_on: str = "id,context,term",
    memory_only: bool = False,
    plural_count: int | None = None,
    keep_existing: bool = True,
    provenance: str = "sidecar",
    endpoint: str | None = None,
    model: str | None = None,
    fallback_models: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    cache: str | None = None,
    temperature: float = 0.2,
    style_file: str | None = None,
    batch_size: int = 50,
    timeout: float = 120,
) -> dict:
    """Translate CATALOG into --target using memories, then an optional engine.

    Lists are comma-separated: --direct-memory a.tmx,b.tmx. Direct memory hits
    (id > context > source) and whole-string glossary terms fill messages before
    the engine; --finish-on picks which classes are written finished. A catalog
    already in the target language keeps its complete translations; turn that
    off with --nokeep-existing (or --keep-existing=False). --out may be omitted
    only for a TS catalog that keeps its language. The report JSON goes to
    --report (default OUT.localizzy.json); --provenance=extra also writes
    <extra-localizzy-origin> into TS messages.
    """
    from vexy_localizzy.formats.qt_numerus import UnknownQtNumerus

    try:
        options = _options(
            catalog,
            target,
            out,
            direct_memory,
            glossary_memory,
            memory_lang,
            glossary_status,
            finish_on,
            memory_only,
            plural_count,
            keep_existing,
            provenance,
            endpoint,
            model,
            fallback_models,
            api_key_env,
            cache,
            temperature,
            timeout,
        )
        from vexy_localizzy.translate.run import translate_file

        style = Path(str(style_file)).read_text(encoding="utf-8") if style_file else ""
        result = translate_file(
            report=Path(str(report)) if report else None,
            style=style,
            batch_size=int(batch_size),
            **options,
        )
    except ImportError as error:
        print(f"error: {error}; install vexy-localizzy[translation]", file=sys.stderr)
        raise SystemExit(EXIT_EXTRA) from error
    except (UsageError, UnknownQtNumerus, ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(EXIT_USAGE) from error
    summary = {
        "out": result.out,
        "report": str(report or f"{result.out}.localizzy.json"),
        "target_lang": result.target_lang,
        "counts": result.counts,
        "findings": len(result.findings),
        "ready": result.ready,
    }
    if result.counts["pending"]:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        raise SystemExit(EXIT_PENDING)
    return summary


if __name__ == "__main__":
    import fire

    fire.Fire(translate)
