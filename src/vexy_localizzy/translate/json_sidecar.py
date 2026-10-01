# this_file: src/vexy_localizzy/translate/json_sidecar.py
"""Provenance and resume state for a translated flat JSON file.

The sidecar ``<out stem>.localizzy.json`` records, for each English key in the
order of the output file, the sha256 of its English text (title included in
titles mode), the model, the state (``machine``, or ``adopted`` for a
translation that predates the sidecar) and the QA findings. A key whose English
text changed is translated again; resume goes by English key, never by
position. Items done in an incomplete run wait in ``<out stem>.partial.json``,
which is rewritten after every accepted batch.

In titles mode the output keys are translated titles, so an output without a
sidecar can only be paired with the English file by position; that is refused
when their lengths differ.
"""

import hashlib
import json
from pathlib import Path

from vexy_localizzy.formats.document import atomic_write

META_FIELDS = ("sha256", "model", "state", "findings")


def sidecar_path(out: Path) -> Path:
    return Path(out).with_suffix(".localizzy.json")


def partial_path(out: Path) -> Path:
    return Path(out).with_suffix(".partial.json")


def source_hash(key: str, text: str, titles: bool) -> str:
    """The identity of an English item: its text, plus the key when it is a title."""
    payload = f"{key}\n\n{text}" if titles else text
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict:
    """A JSON object from ``path``, or ``{}`` when the file does not exist."""
    path = Path(path)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must hold a JSON object")
    return data


def write_json(path: Path, data: object) -> None:
    """Replace ``path`` with indented UTF-8 JSON as one unit."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    atomic_write(path, text.encode("utf-8"))


def _pairs(source: dict, existing: dict, meta: dict, titles: bool, out: Path):
    if not titles:
        return [(k, {"text": existing[k]}) for k in source if k in existing]
    order = list(meta) if meta else list(source)
    if existing and len(order) != len(existing):
        raise ValueError(
            f"refusing: {out} has {len(existing)} entries and cannot be paired "
            f"with {len(order)} English keys; move it aside or restore its sidecar"
        )
    return [
        (key, {"title": title, "text": text})
        for key, (title, text) in zip(order, existing.items())
    ]


def _entries(path: Path, data: object) -> dict[str, dict]:
    """``data`` as {key: object}; ValueError names ``path`` otherwise."""
    if not isinstance(data, dict) or not all(
        isinstance(v, dict) for v in data.values()
    ):
        raise ValueError(f"{path} must map each key to an object")
    return data


def load_done(source: dict, out: Path, titles: bool) -> dict:
    """Translated items by English key from ``out``, its sidecar and a partial file.

    Raises ValueError when a titles file cannot be paired with the English keys,
    or when the output, sidecar or partial file has the wrong shape.
    """
    existing = read_json(out)
    if not all(isinstance(v, str) for v in existing.values()):
        raise ValueError(f"{out} must be a flat JSON object of strings")
    meta_file = sidecar_path(out)
    meta = _entries(meta_file, read_json(meta_file).get("items", {}))
    done = {}
    for key, entry in _pairs(source, existing, meta, titles, out):
        if key in meta:
            entry.update(meta[key])
        elif key in source:
            entry.update(
                sha256=source_hash(key, source[key], titles),
                model=None,
                state="adopted",
                findings=[],
            )
        else:
            continue
        done[key] = entry
    partial = partial_path(out)
    done.update(_entries(partial, read_json(partial)))
    return done


def is_current(done: dict, key: str, text: str, titles: bool) -> bool:
    """True when ``done`` holds a translation of the present English item."""
    return done.get(key, {}).get("sha256") == source_hash(key, text, titles)


def assemble(source: dict, done: dict, titles: bool) -> dict | None:
    """The complete output in English key order, or None when an item is missing,
    stale, or (titles mode) its translated title repeats another."""
    output = {}
    for key, text in source.items():
        if not is_current(done, key, text, titles):
            return None
        entry = done[key]
        output[(entry.get("title") or key) if titles else key] = entry["text"]
    return output if len(output) == len(source) else None


def clashing_keys(done: dict) -> list[str]:
    """English keys whose translated title is also another item's title."""
    titles = [entry.get("title") for entry in done.values()]
    return sorted(
        key
        for key, entry in done.items()
        if entry.get("title") and titles.count(entry["title"]) > 1
    )


def sidecar(source_name: str, model: str, source: dict, done: dict) -> dict:
    """The sidecar document for a complete output."""
    return {
        "source": source_name,
        "model": model,
        "items": {k: {f: done[k][f] for f in META_FIELDS} for k in source},
    }
