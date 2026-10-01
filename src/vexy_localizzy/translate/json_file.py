# this_file: src/vexy_localizzy/translate/json_file.py
"""Translate a flat JSON file of Markdown texts through an OpenAI-compatible endpoint.

Help panels and tip files (``{key: markdown text}``) are not catalogs, so they
do not go through ``localizzy translate``. Items go in small batches with an
optional style sheet and the glossary terms they mention. In titles mode the
keys are English titles and are translated too. Every returned item passes the
text QA in ``json_checks``; a batch with a blocking finding is rejected and
retried on the next run. Output is a draft for review, like any engine output.

The output is written only when every key is translated; otherwise the done
items wait in the partial file (see ``json_sidecar``) and the output is left
untouched. The partial file is rewritten after every accepted batch, so an
interrupt or a crash keeps paid work; Ctrl+C also cancels queued batches.
Items whose translated titles collide are dropped from it and requested again.
The ``openai`` SDK comes with the ``translation`` extra and is
imported only when a request is actually needed.
"""

import json
import sys
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from vexy_localizzy.memory.glossary import Glossary
from vexy_localizzy.translate import json_sidecar as state
from vexy_localizzy.translate.engine import EngineSpec
from vexy_localizzy.translate.json_checks import blocking, check_item
from vexy_localizzy.translate.json_request import (
    DEFAULT_PRODUCT,
    Request,
    openai_request,
    system_prompt,
    translate_rows,
)

GLOSSARY_LIMIT = 80


def read_source(path: Path) -> dict[str, str]:
    """The English file: a flat JSON object of strings."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
        raise ValueError(f"{path} must be a flat JSON object of strings")
    return data


def pending_rows(source: dict, done: dict, titles: bool) -> list[dict]:
    """Rows for every English item without a current translation."""
    rows = []
    for key, text in source.items():
        if state.is_current(done, key, text, titles):
            continue
        rows.append({"id": key, "text": text} | ({"title": key} if titles else {}))
    return rows


def _log(message: str) -> None:
    print(message, file=sys.stderr)


def _accept(batch, got, reported, done, titles) -> list[str]:
    """Store a batch in ``done`` unless QA blocks it; return the blocking labels."""
    checked = {row["id"]: check_item(row, got[row["id"]]) for row in batch}
    rejected = blocking([f for findings in checked.values() for f in findings])
    if rejected:
        return rejected
    for row in batch:
        item = got[row["id"]]
        done[row["id"]] = {
            "text": item["text"],
            **({"title": item["title"]} if titles else {}),
            "sha256": state.source_hash(row["id"], row["text"], titles),
            "model": reported,
            "state": "machine",
            "findings": checked[row["id"]],
        }
    return []


def _collect(futures, total, done, titles, save) -> int:
    """Take batches as they finish; save after each accepted one."""
    failures = 0
    for index, future in enumerate(as_completed(futures), 1):
        label = f"[{index}/{total}]"
        try:
            got, reported = future.result()
        except Exception as error:  # noqa: BLE001 - keep the other batches' work
            failures += 1
            _log(f"{label} failed: {error}")
            continue
        if rejected := _accept(futures[future], got, reported, done, titles):
            failures += 1
            _log(f"{label} rejected by QA: {rejected}")
            continue
        save()
        _log(f"{label} ok")
    return failures


def _run_batches(request, system, jobs, glossary, done, titles, workers, save) -> int:
    """Translate ``jobs`` into ``done``; return the number of failed batches.

    On KeyboardInterrupt the queued batches are cancelled, the partial file is
    saved and the interrupt propagates; requests already in flight finish.
    """
    with ThreadPoolExecutor(max(1, workers)) as pool:
        futures = {}
        for batch in jobs:
            texts = [row["text"] + " " + row.get("title", "") for row in batch]
            terms = glossary.relevant(texts, limit=GLOSSARY_LIMIT) if glossary else {}
            futures[pool.submit(translate_rows, request, system, batch, terms)] = batch
        try:
            return _collect(futures, len(jobs), done, titles, save)
        except KeyboardInterrupt:
            pool.shutdown(wait=False, cancel_futures=True)
            save()
            _log("interrupted: queued batches cancelled, finished ones kept")
            raise


def _save_partial(out: Path, english: dict, done: dict, titles: bool) -> list[str]:
    """Write the done items, minus colliding titles; return the dropped keys.

    Dropped keys are requested again on the next run.
    """
    kept = {k: done[k] for k in english if k in done}
    clashes = state.clashing_keys(kept) if titles else []
    for key in clashes:
        del kept[key]
    state.write_json(state.partial_path(out), kept)
    return clashes


def _finish(source: Path, out: Path, english, done, model: str, titles) -> dict:
    """Write the output and sidecar when complete, else the partial file."""
    output = state.assemble(english, done, titles)
    partial = state.partial_path(out)
    if output is None:
        clashes = _save_partial(out, english, done, titles)
        if clashes:
            _log(
                f"translated titles collide for {clashes}; they will be requested again"
            )
        ready = sum(k in done for k in english) - len(clashes)
        return {
            "complete": False,
            "ready": ready,
            "partial": str(partial),
            "title_clashes": clashes,
        }
    state.write_json(out, output)
    sidecar = state.sidecar(source.name, model, english, done)
    state.write_json(state.sidecar_path(out), sidecar)
    partial.unlink(missing_ok=True)
    return {
        "complete": True,
        "ready": len(output),
        "partial": None,
        "title_clashes": [],
    }


def check_outputs(out: Path, inputs: Sequence[Path]) -> None:
    """ValueError when ``out``, its sidecar or its partial file is an input."""
    written = {
        p.resolve() for p in (out, state.sidecar_path(out), state.partial_path(out))
    }
    if clash := sorted(str(p) for p in written & {Path(i).resolve() for i in inputs}):
        raise ValueError(f"output would overwrite an input: {', '.join(clash)}")


def translate_json_file(
    source: Path,
    out: Path,
    *,
    spec: EngineSpec,
    target_lang: str,
    source_lang: str = "en",
    style: str = "",
    glossary: Glossary | None = None,
    product: str = DEFAULT_PRODUCT,
    titles: bool = False,
    batch_size: int = 5,
    workers: int = 3,
    request: Request | None = None,
    protected: Sequence[Path] = (),
) -> dict:
    """Translate ``source`` into ``out``; the summary's ``complete`` says whether
    ``out`` was written. ``request`` replaces the OpenAI transport.

    ``protected`` names further inputs (a style file) that the output, sidecar
    and partial file must not replace; the source and glossary files always
    count. Raises ValueError for such a clash, a malformed source or state
    file, or an unpairable titles file.
    """
    source, out = Path(source), Path(out)
    memories = [Path(f.path) for f in glossary.files] if glossary else []
    check_outputs(out, [source, *protected, *memories])
    english = read_source(source)
    done = state.load_done(english, out, titles)
    rows = pending_rows(english, done, titles)
    failures = 0
    if rows:
        request = request or openai_request(spec)
        system = system_prompt(
            source_lang=source_lang,
            target_lang=target_lang,
            product=product,
            style=style,
        )
        size = max(1, batch_size)
        jobs = [rows[i : i + size] for i in range(0, len(rows), size)]
        kept = len(english) - len(rows)
        _log(f"{len(jobs)} batches, {len(rows)} items to translate, {kept} kept")

        def save():
            _save_partial(out, english, done, titles)

        failures = _run_batches(
            request, system, jobs, glossary, done, titles, workers, save
        )
    summary = {
        "out": str(out),
        "items": len(english),
        "requested": len(rows),
        "failed_batches": failures,
    }
    return summary | _finish(source, out, english, done, spec.models[0], titles)
