# this_file: src/vexy_localizzy/editorial/json_files.py
"""Review and apply corrections to a translated flat JSON file (key → text).

Two layouts are supported. Keyed files share their keys with the English file,
and each value is reviewed on its own. Titled files translate their keys too
(a title → text list such as a set of tips), so English and translated entries
pair by position and the reviewer sees ``"title\\n\\ntext"`` as one message; a
revision then rewrites title and text together.
"""

import json
from pathlib import Path

from vexy_localizzy.catalog import Unit
from vexy_localizzy.editorial.ledger import (
    Applied,
    Outcome,
    change_record,
    check_live,
    settled,
    stale_entry,
    write_json,
)

JSON_CONTEXT = "json"
TITLE_SEPARATOR = "\n\n"
FORMAT = "format"


def read_object(path: Path) -> dict:
    """A JSON file whose top level is an object, or ValueError."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object at the top level")
    return data


def is_keyed(source: dict, target: dict) -> bool:
    """Keyed files share keys; titled files translate them."""
    return bool(set(source) & set(target))


def _unit(key: str, source: str, target: str) -> Unit:
    return Unit(
        key=key, context=JSON_CONTEXT, source=source, target=target, state="translated"
    )


def _titled(key: str, text: object) -> str:
    return f"{key}{TITLE_SEPARATOR}{text}"


def json_units(source_path: Path, target_path: Path) -> list[Unit]:
    """Catalog-shaped units for the reviewer, one per translated text value."""
    source, target = read_object(source_path), read_object(target_path)
    if is_keyed(source, target):
        return [
            _unit(key, text, target[key])
            for key, text in source.items()
            if isinstance(text, str) and isinstance(target.get(key), str)
        ]
    if len(source) != len(target):
        raise ValueError(
            "JSON files share no keys and differ in length; cannot pair them"
        )
    return [
        _unit(skey, _titled(skey, stext), _titled(tkey, ttext))
        for (skey, stext), (tkey, ttext) in zip(source.items(), target.items())
    ]


def _apply_keyed(source: dict, target: dict, by_key: dict, language: str) -> Outcome:
    outcome = Outcome()
    for key, c in by_key.items():
        if key not in target or key not in source:
            outcome.stale.append(stale_entry(c, "message missing"))
            continue
        if done := settled(c, source[key], target[key]):
            outcome.counts[done] += 1
        elif reason := check_live(c, source[key], target[key]):
            outcome.stale.append(stale_entry(c, reason, source[key], target[key]))
        else:
            outcome.applied.append(
                change_record(language, key, JSON_CONTEXT, source[key], target[key], c)
            )
            target[key] = c["revised"]
    return outcome


def _apply_titled(
    source: dict, target: dict, by_key: dict, language: str
) -> tuple[dict, Outcome]:
    """Rebuild a titled file in order; refuse files that cannot pair or titles that clash."""
    if len(source) != len(target):
        raise ValueError(
            f"refusing: {len(source)} English entries against {len(target)} "
            "translated ones; the files cannot be paired by position"
        )
    outcome, rebuilt, pending = Outcome(), [], dict(by_key)
    for (skey, stext), (tkey, ttext) in zip(source.items(), target.items()):
        c = pending.pop(skey, None)
        rebuilt.append(_titled_entry(c, skey, stext, tkey, ttext, language, outcome))
    for c in pending.values():
        outcome.stale.append(stale_entry(c, "message missing"))
    titles = [title for title, _ in rebuilt]
    if clashes := sorted({t for t in titles if titles.count(t) > 1}):
        raise ValueError(f"refusing: revised titles collide: {clashes}")
    return dict(rebuilt), outcome


def _titled_entry(
    c: dict | None,
    skey: str,
    stext: object,
    tkey: str,
    ttext: object,
    language: str,
    outcome: Outcome,
) -> tuple:
    """The (title, text) to keep for one entry, recording what happened to ``c``."""
    if c is None:
        return tkey, ttext
    live_source, live = _titled(skey, stext), _titled(tkey, ttext)
    revised = c["revised"]
    if done := settled(c, live_source, live):
        outcome.counts[done] += 1
    elif reason := check_live(c, live_source, live):
        outcome.stale.append(stale_entry(c, reason, live_source, live))
    elif not isinstance(revised, str) or TITLE_SEPARATOR not in revised:
        outcome.skip(c, FORMAT)
    else:
        outcome.applied.append(
            change_record(language, skey, JSON_CONTEXT, live_source, live, c)
        )
        return tuple(revised.split(TITLE_SEPARATOR, 1))
    return tkey, ttext


def apply_json(
    target_path: Path,
    source_path: Path,
    changes: list[dict],
    language: str,
) -> Applied:
    """Live-verified corrections for a JSON file; ``render`` writes the new file."""
    source, target = read_object(source_path), read_object(target_path)
    by_key = {c["id"]: c for c in changes}
    if is_keyed(source, target):
        outcome = _apply_keyed(source, target, by_key, language)
    else:
        target, outcome = _apply_titled(source, target, by_key, language)
    if not outcome.applied:
        return Applied(outcome)
    return Applied(outcome, lambda path: write_json(path, target))
