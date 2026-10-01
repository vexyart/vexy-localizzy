# this_file: src/vexy_localizzy/editorial/candidates.py
"""Model-assisted review of a translated catalog: propose corrections, never apply them.

Batches of (context, English source, current translation, comment) go to an
OpenAI-compatible endpoint with the rules, the language style sheet and the
glossary terms that occur in the batch. The model answers only where the
current text is wrong, inconsistent with the terminology, longer than it must
be, or breaks a placeholder or mnemonic. Each answered batch is appended to a
JSONL file with before/after text, reason and MQM family, for a human to accept
or reject before ``apply`` writes anything.

Resumable: a batch whose identity is already in the file is skipped, and the
identity covers the items, model, prompt, style sheet and glossary terms.
"""

import json
import sys
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from vexy_localizzy.catalog import Unit
from vexy_localizzy.editorial.commit import refuse_overwrite
from vexy_localizzy.editorial.json_files import json_units
from vexy_localizzy.editorial.review_prompt import (
    DEFAULT_PRODUCT,
    batch_id,
    eligible,
    item,
    language_name,
    system_prompt,
)
from vexy_localizzy.editorial.review_request import Request, review_batch
from vexy_localizzy.formats.document import atomic_write

Terms = Callable[[list[str]], dict[str, str]]
Job = tuple[str, list[dict], dict[str, str]]

GLOSSARY_STATUSES = frozenset({"approved", "do-not-translate"})
SOURCE_LANGUAGE = "en"


def _units(
    catalog: Path, target: str, source_json: Path | None
) -> tuple[list[Unit], str, str]:
    """Units, source language and target language of a TS or JSON catalog."""
    if catalog.suffix.lower() == ".json":
        if source_json is None:
            raise ValueError("a JSON catalog needs the English source JSON file")
        return json_units(source_json, catalog), SOURCE_LANGUAGE, target
    from vexy_localizzy.formats.ts import load

    loaded = load(catalog)
    return (
        loaded.units,
        loaded.source_lang or SOURCE_LANGUAGE,
        loaded.target_lang or target,
    )


def _terms(glossaries: Sequence[Path], source_lang: str, target_lang: str) -> Terms:
    """A ``texts -> {term: hint}`` lookup over approved glossary entries."""
    if not glossaries:
        return lambda texts: {}
    from vexy_localizzy.memory.glossary import Glossary

    glossary = Glossary.load(
        glossaries,
        source_lang=source_lang,
        target_lang=target_lang,
        statuses=GLOSSARY_STATUSES,
    )
    return glossary.relevant


def _batch(line: str, out: Path, number: int) -> str:
    record = json.loads(line)
    if not isinstance(record, dict) or "batch" not in record:
        raise ValueError(f"{out}:{number}: not a review record")
    return record["batch"]


def finished_batches(out: Path) -> set[str]:
    """Batch ids already recorded in the candidates file.

    A last line cut off mid-write (no newline, not JSON) is dropped and the file
    rewritten without it, so the batch is reviewed again; a malformed line
    anywhere else is an error.
    """
    if not out.exists():
        return set()
    text = out.read_text(encoding="utf-8")
    lines = text.splitlines()
    if text and not text.endswith("\n"):
        if _is_partial(lines[-1]):
            lines.pop()
        # End on a newline either way, so the next record starts its own line.
        atomic_write(out, "".join(f"{line}\n" for line in lines).encode("utf-8"))
    return {
        _batch(line, out, number)
        for number, line in enumerate(lines, 1)
        if line.strip()
    }


def _is_partial(line: str) -> bool:
    try:
        json.loads(line)
    except ValueError:
        return True
    return False


def plan(
    units: list[Unit], *, model: str, system: str, terms: Terms, batch_size: int
) -> list[Job]:
    """``(batch id, rows, terms)`` for every batch of ``units``, in catalog order."""
    jobs = []
    for start in range(0, len(units), batch_size):
        rows = [item(u) for u in units[start : start + batch_size]]
        found = terms([r["source"] for r in rows])
        jobs.append(
            (batch_id(rows, model=model, system=system, terms=found), rows, found)
        )
    return jobs


def kept_corrections(corrections: list, rows: list[dict]) -> tuple[list[dict], int]:
    """Corrections for known ids, first per id, with the reviewed text; and the dropped count."""
    known = {r["id"]: r for r in rows}
    kept, seen = [], set()
    for c in corrections:
        key = c.get("id") if isinstance(c, dict) else None
        if key not in known or key in seen or not c.get("revised"):
            continue
        seen.add(key)
        row = known[key]
        kept.append(
            {
                **c,
                "context": row["context"],
                "source": row["source"],
                "before": row["current"],
            }
        )
    return kept, len(corrections) - len(kept)


def review_catalog(
    catalog: Path,
    target: str,
    out: Path,
    *,
    model: str,
    request: Request,
    product: str = DEFAULT_PRODUCT,
    style: str = "",
    glossaries: Sequence[Path] = (),
    source_json: Path | None = None,
    workers: int = 4,
    batch_size: int = 40,
    limit: int = 0,
    sleep: Callable[[float], None] | None = None,
) -> dict:
    """Review CATALOG into the JSONL file OUT; return counts of batches and corrections."""
    refuse_overwrite({"out": out}, {"catalog": catalog, "source JSON": source_json})
    units, source_lang, target_lang = _units(Path(catalog), target, source_json)
    units, left_out = eligible(units)
    language = language_name(target)
    system = system_prompt(language, product, style)
    terms = _terms(glossaries, source_lang, target_lang)
    jobs = plan(units, model=model, system=system, terms=terms, batch_size=batch_size)
    done = finished_batches(Path(out))
    todo = [job for job in jobs if job[0] not in done]
    todo = todo[:limit] if limit else todo
    print(
        f"{len(todo)} batches to review ({len(jobs) - len(todo)} skipped)",
        file=sys.stderr,
    )
    counts = _run(todo, Path(out), request, system, language, workers, sleep)
    return {
        "out": str(out),
        "units": len(units),
        "left_out": left_out,
        "batches": len(jobs),
        "already_reviewed": sum(job[0] in done for job in jobs),
        **counts,
    }


def _run(
    todo: list[Job],
    out: Path,
    request: Request,
    system: str,
    language: str,
    workers: int,
    sleep: Callable[[float], None] | None,
) -> dict:
    """Review ``todo`` in parallel, appending one record per answered batch."""
    counts = {"reviewed": 0, "failed": 0, "corrections": 0, "dropped": 0}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as ledger, ThreadPoolExecutor(workers) as pool:
        futures = {
            pool.submit(
                review_batch, request, system, rows, terms, language, sleep=sleep
            ): (
                bid,
                rows,
            )
            for bid, rows, terms in todo
        }
        for index, future in enumerate(as_completed(futures), 1):
            bid, rows = futures[future]
            try:
                corrections, reported = future.result()
            except RuntimeError as error:
                counts["failed"] += 1
                print(f"[{index}/{len(todo)}] {bid} FAILED: {error}", file=sys.stderr)
                continue
            kept, dropped = kept_corrections(corrections, rows)
            record = {"batch": bid, "model": reported, "items": len(rows)}
            record |= {"corrections": kept, "dropped": dropped}
            ledger.write(json.dumps(record, ensure_ascii=False) + "\n")
            ledger.flush()
            counts["reviewed"] += 1
            counts["corrections"] += len(kept)
            counts["dropped"] += dropped
            print(
                f"[{index}/{len(todo)}] {bid} {len(kept)} corrections", file=sys.stderr
            )
    return counts
