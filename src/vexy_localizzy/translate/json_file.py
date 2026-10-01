# this_file: src/vexy_localizzy/translate/json_file.py
"""Translate a flat JSON file of Markdown texts through an OpenAI-compatible endpoint.

Help panels and tip files (``{key: markdown text}``) are not catalogs, so they
do not go through ``localizzy translate``. Items go in small batches with an
optional style sheet and the glossary terms they mention. In titles mode the
keys are English titles and are translated too. Every returned item passes the
text QA in ``json_checks``; a batch with a blocking finding is rejected. Output
is a draft for review, like any engine output.

Each distinct text is requested once and written under every key that has it
(a title is part of the item, so titled items never repeat). The models of the
engine are tried in order: the next one when a request fails or its answer is
rejected. After the batches, every item of a failed batch gets a second chance
on its own (``json_rescue``): alone, then by paragraph, then with masked markup.

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
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from vexy_localizzy.memory.glossary import Glossary
from vexy_localizzy.translate import json_sidecar as state
from vexy_localizzy.translate.engine import EngineSpec
from vexy_localizzy.translate.json_checks import blocking, check_item
from vexy_localizzy.translate.json_request import (
    DEFAULT_PRODUCT,
    Ask,
    Rejected,
    Request,
    openai_request,
    system_prompt,
)
from vexy_localizzy.translate.json_rescue import WHOLE, rescue_item


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


def distinct_rows(rows: list[dict]) -> tuple[list[dict], dict[str, list[str]]]:
    """The rows to request, and for each requested id the other keys of its text.

    Rows with the same text are one item, requested under the first key. A row
    with a title is always its own item: the title is translated with it.
    """
    leaders: dict[str, str] = {}
    kept, twins = [], {}
    for row in rows:
        leader = (
            row["id"] if "title" in row else leaders.setdefault(row["text"], row["id"])
        )
        if leader == row["id"]:
            kept.append(row)
        else:
            twins.setdefault(leader, []).append(row["id"])
    return kept, twins


def _twin(entry: dict, key: str) -> dict:
    """``entry`` for another key with the same text; its findings name that key."""
    return entry | {"findings": [f | {"unit_key": key} for f in entry["findings"]]}


def reuse_done(source: dict, done: dict, titles: bool) -> int:
    """Fill each key whose text already has a current translation under another
    key; return how many were filled. Titled items are never shared."""
    if titles:
        return 0
    current = {}
    for key, text in source.items():
        if state.is_current(done, key, text, titles):
            current.setdefault(text, key)
    stale = [
        key
        for key, text in source.items()
        if text in current and not state.is_current(done, key, text, titles)
    ]
    for key in stale:
        done[key] = _twin(done[current[source[key]]], key)
    return len(stale)


def _log(message: str) -> None:
    print(message, file=sys.stderr)


@dataclass
class _Results:
    """Where accepted items go: ``done``, under their key and every twin key."""

    done: dict
    titles: bool
    twins: dict[str, list[str]]
    reused: int = 0

    def store(self, row: dict, item: dict, reported: str | None, path: str) -> None:
        entry = {
            "text": item["text"],
            **({"title": item["title"]} if self.titles else {}),
            "sha256": state.source_hash(row["id"], row["text"], self.titles),
            "model": reported,
            "state": "machine",
            "path": path,
            "findings": check_item(row, item),
        }
        self.done[row["id"]] = entry
        for key in self.twins.get(row["id"], ()):
            self.done[key] = _twin(entry, key)
            self.reused += 1


def _in_pool(jobs: list, work: Callable, accept: Callable, workers: int, save) -> list:
    """Run ``work(job)`` for every job; return ``(job, error)`` for the failed ones.

    ``accept(job, result)`` runs in this thread as each job finishes, and the
    partial file is saved after it. On KeyboardInterrupt the queued jobs are
    cancelled, the partial file is saved and the interrupt propagates; requests
    already in flight finish.
    """
    failed = []
    with ThreadPoolExecutor(max(1, workers)) as pool:
        futures = {pool.submit(work, job): job for job in jobs}
        try:
            for index, future in enumerate(as_completed(futures), 1):
                label = f"[{index}/{len(jobs)}]"
                try:
                    result = future.result()
                except Exception as error:  # noqa: BLE001 - keep the other jobs' work
                    failed.append((futures[future], error))
                    _log(f"{label} failed: {error}")
                    continue
                accept(futures[future], result)
                save()
                _log(f"{label} ok")
        except KeyboardInterrupt:
            pool.shutdown(wait=False, cancel_futures=True)
            save()
            _log("interrupted: queued batches cancelled, finished ones kept")
            raise
    return failed


def _batch_check(batch: list[dict]) -> Callable[[dict], list[str]]:
    """The QA gate of a batch: blocking labels over all its items."""
    return lambda got: blocking(
        [f for row in batch for f in check_item(row, got[row["id"]])]
    )


def _run_batches(ask: Ask, jobs, results: _Results, workers: int, save) -> list:
    """Translate the batches; return ``(batch, error)`` for the failed ones."""

    def accept(batch, answer):
        got, reported = answer
        for row in batch:
            results.store(row, got[row["id"]], reported, WHOLE)

    return _in_pool(
        jobs, lambda batch: ask(batch, _batch_check(batch)), accept, workers, save
    )


def _rescue(ask: Ask, failed: list, results: _Results, workers: int, save) -> int:
    """Give every item of a failed batch its own requests; return how many passed.

    An item goes alone first, unless it already was a batch of one whose answer
    was rejected: then only the paragraph paths are left.
    """
    jobs = [
        (row, not (len(batch) == 1 and isinstance(error, Rejected)))
        for batch, error in failed
        for row in batch
    ]
    _log(f"{len(jobs)} items to retry on their own")
    lost = _in_pool(
        jobs,
        lambda job: rescue_item(job[0], ask, alone=job[1]),
        lambda job, answer: results.store(job[0], *answer),
        workers,
        save,
    )
    return len(jobs) - len(lost)


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


def _finish(source: Path, out: Path, english, done, models, titles) -> dict:
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
    sidecar = state.sidecar(source.name, models[0], english, done, models[1:])
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


def _routes(spec: EngineSpec, request: Request | None) -> list[Request]:
    """One transport per model, preferred first; ``request`` replaces them all."""
    if request is not None:
        return [request]
    return [
        openai_request(spec.model_copy(update={"models": (model,)}))
        for model in spec.models
    ]


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
    rescue: bool = True,
) -> dict:
    """Translate ``source`` into ``out``; the summary's ``complete`` says whether
    ``out`` was written. ``request`` replaces the OpenAI transport of every model.

    ``protected`` names further inputs (a style file) that the output, sidecar
    and partial file must not replace; the source and glossary files always
    count. ``rescue=False`` leaves the items of a failed batch for the next run
    instead of retrying each on its own. Raises ValueError for such a clash, a
    malformed source or state file, or an unpairable titles file.
    """
    source, out = Path(source), Path(out)
    memories = [Path(f.path) for f in glossary.files] if glossary else []
    check_outputs(out, [source, *protected, *memories])
    english = read_source(source)
    done = state.load_done(english, out, titles)
    reused = reuse_done(english, done, titles)
    rows, twins = distinct_rows(pending_rows(english, done, titles))
    results = _Results(done, titles, twins, reused)
    failed, rescued = [], 0
    if rows:
        system = system_prompt(
            source_lang=source_lang,
            target_lang=target_lang,
            product=product,
            style=style,
        )
        ask = Ask(_routes(spec, request), system, glossary)
        size = max(1, batch_size)
        jobs = [rows[i : i + size] for i in range(0, len(rows), size)]
        kept = len(english) - len(rows) - sum(len(keys) for keys in twins.values())
        _log(f"{len(jobs)} batches, {len(rows)} items to translate, {kept} kept")

        def save():
            _save_partial(out, english, done, titles)

        failed = _run_batches(ask, jobs, results, workers, save)
        if failed and rescue:
            rescued = _rescue(ask, failed, results, workers, save)
    summary = {
        "out": str(out),
        "items": len(english),
        "requested": len(rows),
        "reused": results.reused,
        "failed_batches": len(failed),
        "rescued": rescued,
    }
    return summary | _finish(source, out, english, done, spec.models, titles)
