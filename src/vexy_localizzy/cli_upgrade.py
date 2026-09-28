# this_file: src/vexy_localizzy/cli_upgrade.py
"""Fire command: ``localizzy upgrade FRESH.ts APPROVED.ts --out NEW.ts --retired RETIRED.ts``.

Exit codes: 0 when every active message has text in NEW, 1 when any stays
empty (pending or untranslated), 2 for usage errors, 3 when the translation
extra is missing but an engine was requested.
"""

import json
import os
import sys
from pathlib import Path

from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.upgrade.ts_upgrade import UpgradeOptions, UpgradeUsageError
from vexy_localizzy.upgrade.ts_upgrade import upgrade as run_upgrade

MATCH_CLASSES = {"id", "context", "source", "term"}
GLOSSARY_STATUSES = {"approved", "proposed", "do-not-translate"}


def csv_list(value) -> list[str]:
    """Fire hands comma lists over as a str or a tuple; accept both."""
    if value is None or value == "":
        return []
    items = value if isinstance(value, list | tuple) else str(value).split(",")
    return [str(item).strip() for item in items if str(item).strip()]


def _usage(message: str) -> SystemExit:
    print(f"localizzy upgrade: {message}", file=sys.stderr)
    return SystemExit(2)


def _languages(path: Path) -> tuple[str, str | None]:
    tree, _ = xml.parse(path.read_bytes())
    root = tree.getroot()
    return root.get("sourcelanguage") or "en", root.get("language")


def _open_cache(endpoint, models, api_key_env, cache_path, temperature):
    """Build the engine-backed cache inline; abersetz is an optional extra."""
    try:
        from vexy_localizzy.abersetz_transport import TRANSPORT_ID, translate_batch
        from vexy_localizzy.qa.text import validate_batch
        from vexy_localizzy.translation_cache import TranslationCache
    except ImportError as error:
        print(
            f"localizzy upgrade: install the 'translation' extra ({error})",
            file=sys.stderr,
        )
        raise SystemExit(3) from error
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise _usage(f"environment variable {api_key_env} is not set")

    def request(model, batch):
        return translate_batch(
            batch, model, base_url=endpoint, api_key=api_key, temperature=temperature
        )

    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    return TranslationCache(
        cache_path,
        models=tuple(models),
        request=request,
        endpoint_identity=endpoint,
        engine_identity=f"{TRANSPORT_ID};temperature={temperature!r}",
        validation_identity="localizzy-upgrade:qa:1",
        validate=validate_batch,
    )


def upgrade(
    fresh,
    approved,
    out,
    retired,
    report=None,
    target=None,
    direct_memory=None,
    glossary_memory=None,
    memory_lang=None,
    glossary_status="approved,do-not-translate",
    finish_on="id,context,term",
    fuzzy_threshold=0.92,
    relocated_finished=False,
    no_engine=False,
    endpoint=None,
    model=None,
    fallback_models=None,
    api_key_env="OPENAI_API_KEY",
    cache=None,
    temperature=0.2,
    style_file=None,
) -> dict:
    """Port APPROVED translations onto FRESH lupdate output; write NEW and RETIRED.

    Tiers: exact, memory id/context, relocated, fuzzy, memory source/term,
    machine, pending. The report defaults to OUT + '.upgrade.json'.
    """
    fresh, approved, out, retired = (
        Path(str(p)) for p in (fresh, approved, out, retired)
    )
    report_path = Path(str(report)) if report else Path(str(out) + ".upgrade.json")
    for path in (fresh, approved):
        if not path.is_file():
            raise _usage(f"no such file: {path}")
    finish = set(csv_list(finish_on))
    statuses = set(csv_list(glossary_status))
    if finish - MATCH_CLASSES:
        raise _usage(f"unknown finish-on classes: {sorted(finish - MATCH_CLASSES)}")
    if statuses - GLOSSARY_STATUSES:
        raise _usage(
            f"unknown glossary statuses: {sorted(statuses - GLOSSARY_STATUSES)}"
        )
    try:
        threshold = float(fuzzy_threshold)
    except (TypeError, ValueError):
        raise _usage("fuzzy-threshold must be a number") from None
    if not 0 < threshold <= 1:
        raise _usage("fuzzy-threshold must be in (0, 1]")
    if not no_engine and not endpoint:
        raise _usage("pass --endpoint and --model, or --no-engine")
    if endpoint and not model:
        raise _usage("--endpoint needs --model")
    target = str(target) if target not in (None, "") else None
    memory_lang = str(memory_lang) if memory_lang not in (None, "") else None
    try:
        _languages(fresh)
        source_lang, approved_lang = _languages(approved)
    except ValueError as error:
        raise _usage(f"cannot read TS input: {error}") from None
    target_lang = target or approved_lang
    if not target_lang:
        raise _usage("APPROVED has no language attribute; pass --target")

    direct = glossary = None
    try:
        from vexy_localizzy.memory import DirectMemory, Glossary

        if paths := csv_list(direct_memory):
            direct = DirectMemory.load(
                [Path(p) for p in paths],
                source_lang=source_lang,
                target_lang=target_lang,
                memory_lang=memory_lang,
            )
        if paths := csv_list(glossary_memory):
            glossary = Glossary.load(
                [Path(p) for p in paths],
                source_lang=source_lang,
                target_lang=target_lang,
                memory_lang=memory_lang,
                statuses=frozenset(statuses),
            )
    except (OSError, ValueError) as error:
        raise _usage(f"cannot load memory: {error}") from None

    engine_cache = None
    if not no_engine:
        models = [str(model), *csv_list(fallback_models)]
        cache_path = (
            Path(str(cache))
            if cache
            else out.parent / ".localizzy" / "translation-cache.sqlite"
        )
        engine_cache = _open_cache(
            str(endpoint), models, str(api_key_env), cache_path, float(temperature)
        )
    options = UpgradeOptions(
        style=Path(str(style_file)).read_text(encoding="utf-8") if style_file else "",
        finish_on=frozenset(finish),
        fuzzy_threshold=threshold,
        relocated_finished=bool(relocated_finished),
        no_engine=bool(no_engine),
    )
    try:
        result = run_upgrade(
            fresh,
            approved,
            out=out,
            retired=retired,
            report=report_path,
            target=target,
            direct=direct,
            glossary=glossary,
            cache=engine_cache,
            options=options,
        )
    except UpgradeUsageError as error:
        raise _usage(str(error)) from None
    finally:
        if engine_cache is not None:
            engine_cache.db.close()
    summary = {
        "out": str(out),
        "retired": str(retired),
        "report": str(report_path),
        "target_lang": result.target_lang,
        "counts": {k: v for k, v in result.counts.items() if v},
    }
    if result.unfilled:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    return summary


if __name__ == "__main__":
    import fire

    fire.Fire(upgrade)
