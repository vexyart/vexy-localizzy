# this_file: src/vexy_localizzy/cli/project.py
"""``localizzy project`` commands: the general commands with paths from ``localizzy.toml``.

``upgrade``, ``translate`` and ``build_ui`` own the mechanics. These wrappers
only resolve a language code to catalog paths, memories, tags and engine
settings, so a weekly run names a code and nothing else.
"""

import hashlib
import sys
from pathlib import Path

from vexy_localizzy.cli._args import csv_strings
from vexy_localizzy.project import Config, load_config

DIGEST_LENGTH = 8  # hex digits of each input's sha256 in a retired file name
EXIT_PENDING, EXIT_USAGE = 1, 2


def _fail(message: str) -> SystemExit:
    print(f"localizzy project: {message}", file=sys.stderr)
    return SystemExit(EXIT_USAGE)


def _style_file(config: Config) -> str | None:
    """``[translate].style_file`` resolved against the project file, like every path."""
    style = config.translate.style_file
    return str(config.resolve(style)) if style else None


def _check_retired(retired: Path, earlier: bytes | None) -> None:
    """A rerun must reproduce the retired messages; otherwise restore and refuse."""
    if earlier is None or not retired.exists() or retired.read_bytes() == earlier:
        return
    retired.write_bytes(earlier)
    raise _fail(
        f"{retired} held different retired messages from an earlier run and was "
        "restored; move it aside to run again"
    )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:DIGEST_LENGTH]


def _engine(config: Config, model: str | None) -> dict:
    """Engine flags from ``[translate]``; the given model leads the fallback list."""
    settings = config.translate
    models = list(dict.fromkeys(([model] if model else []) + settings.fallback_models))
    if not models:
        raise _fail("No model: pass --model or list fallback_models under [translate]")
    return {
        "endpoint": settings.endpoint,
        "model": models[0],
        "fallback_models": ",".join(models[1:]) or None,
        "api_key_env": settings.api_key_env,
        "cache": str(config.resolve(settings.cache_path)),
        "temperature": settings.temperature,
        "timeout": settings.timeout,
    }


def _memories(config: Config, code: str, extra_glossaries: list[str]) -> dict:
    """Memory flags for ``code``; a configured memory that is missing is reported."""
    found: dict[str, list[Path]] = {}
    for kind, paths in config.memory_candidates(code).items():
        found[kind] = [path for path in paths if path.is_file()]
        for path in paths:
            if not path.is_file():
                print(f"warning: {kind} memory not found: {path}", file=sys.stderr)
    glossary = found["glossary"] + [Path(path) for path in extra_glossaries]
    return {
        "direct_memory": ",".join(str(p) for p in found["direct"]) or None,
        "glossary_memory": ",".join(str(p) for p in glossary) or None,
        "memory_lang": config.language(code).memory,
        "glossary_status": ",".join(config.memories.glossary_statuses),
    }


def upgrade(
    code: str,
    fresh: str | None = None,
    out: str | None = None,
    model: str | None = None,
    no_engine: bool = False,
    in_place: bool = False,
    glossary: str | None = None,
    fuzzy_threshold: float = 0.92,
    config: str | None = None,
) -> dict:
    """Port the approved catalog of CODE onto the fresh lupdate output.

    Writes NEW beside the approved catalog (``<name>.new.ts``), RETIRED under
    ``[catalogs].retired_dir`` and the report under ``report_dir``. RETIRED is
    named from the sha256 of both inputs and never overwritten: a rerun on the
    same inputs must produce the same retired messages, or it is refused.
    --in-place replaces the approved catalog only when nothing stays pending
    (pending messages exit 1 and leave NEW for review). --glossary adds memories to the
    configured ones; --no-engine leaves new strings pending.
    """
    from vexy_localizzy.cli.upgrade import upgrade as run

    settings = load_config(config)
    approved = settings.catalog_path(code)
    fresh_path = Path(fresh) if fresh else settings.catalog_path(code, fresh=True)
    for path in (approved, fresh_path):
        if not path.is_file():
            raise _fail(f"no such catalog: {path}")
    stem = approved.stem
    new_path = Path(out) if out else approved.with_suffix(".new.ts")
    retired = (
        settings.resolve(settings.catalogs.retired_dir)
        / f"{stem}-{_digest(fresh_path)}-{_digest(approved)}.ts"
    )
    earlier = retired.read_bytes() if retired.exists() else None
    report = settings.resolve(settings.catalogs.report_dir) / f"{stem}.json"
    retired.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    engine = {"no_engine": True} if no_engine else _engine(settings, model)
    pending = False
    try:
        result = dict(
            run(
                str(fresh_path),
                str(approved),
                str(new_path),
                str(retired),
                report=str(report),
                target=settings.language(code).catalog,
                fuzzy_threshold=fuzzy_threshold,
                style_file=_style_file(settings),
                **_memories(settings, code, csv_strings(glossary)),
                **engine,
            )
        )
    except SystemExit as exit_:
        if exit_.code != EXIT_PENDING:
            raise
        pending, result = True, {}  # outputs are written; some messages are unfilled
    _check_retired(retired, earlier)
    if pending:
        raise SystemExit(EXIT_PENDING)
    result["in_place"] = bool(in_place)
    if in_place:
        new_path.replace(approved)
        result["out"] = str(approved)
    return result


def translate(
    code: str,
    catalog: str | None = None,
    out: str | None = None,
    model: str | None = None,
    memory_only: bool = False,
    glossary: str | None = None,
    source_catalog: str | None = None,
    batch_size: int = 50,
    config: str | None = None,
) -> dict:
    """Fill the catalog of CODE from its memories, then the engine.

    --source-catalog starts a new language from the source-language catalog.
    That keeps no existing translation, so it is refused when the catalog of
    CODE exists and --out was not given. --memory-only needs no endpoint.
    """
    from vexy_localizzy.cli.translate import translate as run

    settings = load_config(config)
    if source_catalog:
        source = Path(source_catalog)
        destination = Path(out) if out else settings.catalog_path(code)
        if out is None and destination.exists():
            raise _fail(
                f"{destination} exists and would lose its translations; complete it "
                "without --source-catalog, or pass --out to write elsewhere"
            )
    else:
        source = Path(catalog) if catalog else settings.catalog_path(code)
        destination = Path(out) if out else source
    flags = _memories(settings, code, csv_strings(glossary))
    if not memory_only:
        flags.update(_engine(settings, model))
    return dict(
        run(
            str(source),
            settings.language(code).catalog,
            out=str(destination),
            memory_only=memory_only,
            style_file=_style_file(settings),
            batch_size=batch_size,
            **flags,
        )
    )


def build_ui(code: str, out: str | None = None, config: str | None = None) -> dict:
    """Rebuild the project memory of CODE from its approved catalog.

    The output is the first ``[memories].direct`` name. Exact pairs already
    served by the glossary memories are left out, so a missing glossary memory
    is an error: its terms would otherwise enter the project memory.
    """
    from vexy_localizzy.memory.build_ui import build_ui as run

    settings = load_config(config)
    candidates = settings.memory_candidates(code)
    missing = [path for path in candidates["glossary"] if not path.is_file()]
    if missing:
        raise _fail(
            "glossary memories missing, so their terms would enter the project memory: "
            + ", ".join(str(path) for path in missing)
        )
    if not candidates["direct"] and not out:
        raise _fail("No [memories].direct name configured; pass --out")
    return run(
        settings.catalog_path(code),
        Path(out) if out else candidates["direct"][0],
        lang=settings.language(code).memory,
        exclude_memories=candidates["glossary"],
    )


PROJECT_COMMANDS = {"upgrade": upgrade, "translate": translate, "build_ui": build_ui}
