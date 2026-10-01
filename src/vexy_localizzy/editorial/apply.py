# this_file: src/vexy_localizzy/editorial/apply.py
"""Apply accepted review candidates to a catalog and record an exact change ledger.

Reads the JSONL the reviewer wrote, keeps the corrections that pass the user's
filters (severity, family, rejected ids) and the shape guards, and writes them
into a Qt TS catalog through the byte-preserving writer, or into a translated
JSON file. A correction lands only while the catalog still holds what the
reviewer saw; stale candidates are listed, never applied. Applied Qt messages
keep their state unless ``finish`` says a human accepted the candidates. Every
refusal is counted by reason and listed by id in the ledger.
"""

from collections import Counter
from pathlib import Path

from vexy_localizzy.catalog import Unit
from vexy_localizzy.editorial.candidate_file import (
    FAMILIES,
    SEVERITIES,
    load_candidates,
)
from vexy_localizzy.editorial.commit import commit_files, refuse_overwrite
from vexy_localizzy.editorial.guards import EMPTY, MNEMONIC, PLURAL_FORMS, SHAPE
from vexy_localizzy.editorial.json_files import FORMAT, apply_json
from vexy_localizzy.editorial.ledger import (
    ALREADY_APPLIED,
    LEDGER_INDENT,
    UNCHANGED,
    Applied,
    Outcome,
    change_record,
    check_live,
    settled,
    stale_entry,
    write_json,
)

VANISHED, VARIANTS = "vanished", "variants"
# Every count the ledger reports, zero when nothing was skipped for that reason.
SKIP_REASONS = (
    "rejected",
    "severity",
    "family",
    PLURAL_FORMS,
    EMPTY,
    SHAPE,
    MNEMONIC,
    VANISHED,
    VARIANTS,
    FORMAT,
    ALREADY_APPLIED,
    UNCHANGED,
    "stale",
)


def current(unit: Unit) -> object:
    """The live translation of a unit in the shape the reviewer records."""
    if unit.plural is not None:
        return [unit.plural.forms[k] for k in sorted(unit.plural.forms, key=int)]
    return unit.target


def has_variants(unit: Unit) -> bool:
    """Length variants (``<lengthvariant>``) a form rewrite would leave behind."""
    return unit.variants is not None or bool(unit.plural and unit.plural.variants)


def _update(unit: Unit, revised: object) -> dict | None:
    """Model fields for ``revised``, or None when it does not fit the unit's forms."""
    if isinstance(revised, list):
        if unit.plural is None or len(revised) != len(unit.plural.forms):
            return None
        forms = {str(i): form for i, form in enumerate(revised)}
        return {"plural": unit.plural.model_copy(update={"forms": forms})}
    if unit.plural is not None:
        return None
    return {"target": revised}


def _refusal(unit: Unit, c: dict, outcome: Outcome) -> bool:
    """Record why ``c`` cannot land on ``unit``; False when it can."""
    if unit.state == VANISHED:
        outcome.skip(c, VANISHED)
    elif has_variants(unit):
        outcome.skip(c, VARIANTS)
    elif reason := settled(c, unit.source, current(unit)):
        outcome.counts[reason] += 1
    elif reason := check_live(c, unit.source, current(unit)):
        outcome.stale.append(stale_entry(c, reason, unit.source, current(unit)))
    else:
        return False
    return True


def _apply_unit(
    unit: Unit, c: dict, language: str, finish: bool, outcome: Outcome
) -> Unit:
    """The unit to keep after trying candidate ``c`` on it."""
    if _refusal(unit, c, outcome):
        return unit
    update = _update(unit, c["revised"])
    if update is None:
        outcome.skip(c, PLURAL_FORMS)
        return unit
    state = "translated" if finish else unit.state
    record = change_record(
        language, f"key:{unit.key}", unit.context, unit.source, c["before"], c
    )
    record |= {
        "comment": unit.disambiguation or "",
        "state_before": unit.state,
        "state_after": state,
    }
    outcome.applied.append(record)
    return unit.model_copy(update={**update, "state": state})


def apply_ts(
    catalog_path: Path, changes: list[dict], language: str, *, finish: bool = False
) -> Applied:
    """Live-verified corrections for a TS catalog; ``render`` writes only edited messages."""
    from vexy_localizzy.formats.ts import dump, load

    catalog = load(catalog_path)
    by_key = {c["id"]: c for c in changes}
    outcome, units = Outcome(), []
    for unit in catalog.units:
        c = by_key.pop(unit.key, None)
        units.append(
            unit if c is None else _apply_unit(unit, c, language, finish, outcome)
        )
    for c in by_key.values():
        outcome.stale.append(stale_entry(c, "message missing"))
    if not outcome.applied:
        return Applied(outcome)
    edited = catalog.model_copy(update={"units": units})
    return Applied(outcome, lambda path: dump(edited, path))


def _ledger(catalog: Path, scope: str | None, outcome: Outcome, skipped, items) -> dict:
    return {
        "scope": scope or f"Model-assisted review of {Path(catalog).name}.",
        "skipped": skipped,
        "skipped_items": items,
        "changes": outcome.applied,
        "stale": outcome.stale,
    }


def apply_review(
    catalog: Path,
    language: str,
    candidates: Path,
    ledger: Path,
    *,
    source_json: Path | None = None,
    severities: set[str] = frozenset(SEVERITIES),
    families: set[str] = frozenset(FAMILIES),
    rejected: set[str] = frozenset(),
    scope: str | None = None,
    dry_run: bool = False,
    allow_markup: bool = False,
    finish: bool = False,
    force: bool = False,
) -> dict:
    """Apply CANDIDATES to CATALOG and write LEDGER with it, all or nothing.

    An existing LEDGER is refused unless ``force``: it is the only record of an
    earlier run. ``dry_run`` writes nothing.
    """
    inputs = {"catalog": catalog, "source JSON": source_json}
    refuse_overwrite({"candidates": candidates, "ledger": ledger}, inputs)
    refuse_overwrite({"ledger": ledger}, {"candidates": candidates})
    if not dry_run and Path(ledger).exists() and not force:
        raise ValueError(f"ledger {ledger} exists; pass --force to replace it")
    changes, filtered, refused = load_candidates(
        candidates, severities, families, rejected, allow_markup=allow_markup
    )
    if Path(catalog).suffix.lower() == ".json":
        if source_json is None:
            raise ValueError("a JSON catalog needs the English source JSON file")
        result = apply_json(catalog, source_json, changes, language)
    else:
        result = apply_ts(catalog, changes, language, finish=finish)
    outcome = result.outcome
    items = refused.skipped + outcome.skipped
    counts = filtered + Counter(item["reason"] for item in items) + outcome.counts
    counts["stale"] = len(outcome.stale)
    skipped = {reason: counts[reason] for reason in SKIP_REASONS}
    if not dry_run:
        record = _ledger(catalog, scope, outcome, skipped, items)
        outputs = [(Path(catalog), result.render)] if result.render else []
        outputs.append(
            (Path(ledger), lambda path: write_json(path, record, indent=LEDGER_INDENT))
        )
        commit_files(outputs)
    return {
        "candidates": len(changes),
        "applied": len(outcome.applied),
        "skipped": skipped,
        "skipped_ids": _ids_by_reason(items),
        "dry_run": dry_run,
    }


def _ids_by_reason(items: list[dict]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for item in items:
        grouped.setdefault(item["reason"], []).append(item["id"])
    return grouped
