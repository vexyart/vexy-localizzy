# this_file: src/vexy_localizzy/sourcefix/source.py
"""Plan exact source occurrences before any writes."""

from collections import defaultdict
from pathlib import Path

from vexy_localizzy.sourcefix.catalog import Catalog, Key
from vexy_localizzy.sourcefix.extract import current_locations
from vexy_localizzy.sourcefix.files import confined, digest
from vexy_localizzy.sourcefix.literals import literals, replacement


def plan_sources(
    catalog: Catalog, edits: dict[Key, str], state: dict, lupdate: str
) -> tuple[dict, dict, dict]:
    """Resolve every location, check shared literals and return bytes plus line shifts."""
    locations = catalog.locations()
    pending = defaultdict(list)
    for identity, new in edits.items():
        if not locations[identity]:
            raise ValueError(f"No source locations for {identity}")
        for path, line in locations[identity]:
            pending[path].append((identity, new, line))
    outputs, originals, shifts = {}, {}, {}
    for path in pending:
        confined(path, Path(state["root"]))
        if str(path) in state.get("missing_files", []):
            raise ValueError(
                f"Source missing at preparation; refresh extraction before editing: {path}"
            )
        originals[path] = path.read_bytes()
        if digest(originals[path]) != state["files"].get(str(path)):
            raise ValueError(f"Source changed since preparation: {path}")
    locations = current_locations(set(pending), Path(state["root"]), lupdate)
    for identity in edits:
        if not locations.get(identity):
            raise ValueError(
                f"Current Qt extraction cannot find source identity: {identity}"
            )
    for path, requests in pending.items():
        raw = originals[path]
        requested = {identity: new for identity, new, _ in requests}
        requests = [
            (identity, new, n)
            for identity, new in requested.items()
            for p, n in locations[identity]
            if p == path
        ]
        if set(requested) != {identity for identity, _, _ in requests}:
            raise ValueError(
                f"Current Qt extraction cannot find every requested identity in {path}"
            )
        candidates = literals(path, raw)
        changes = {}
        for identity, new, line in requests:
            matches = [item for item in candidates if item.matches(identity, line)]
            if len(matches) != 1:
                raise ValueError(
                    f"Expected one exact literal, found {len(matches)}: {path}:{line} {identity}"
                )
            literal = matches[0]
            span = (literal.start, literal.end)
            output = replacement(path, literal, new, raw)
            if span in changes and changes[span][0] != output:
                raise ValueError(
                    f"Conflicting corrections to shared literal: {path}:{line}"
                )
            # Inline headers/macros can supply one literal to several contexts.
            for other, refs in locations.items():
                if other[1] != identity[1]:
                    continue
                shared = any(p == path and literal.matches(other, n) for p, n in refs)
                if shared and edits.get(other) != new:
                    raise ValueError(
                        f"Shared source literal also belongs to {other}; correct all owners together"
                    )
            changes[span] = (output, literal)
        cursor, pieces, movements = 0, [], []
        for (start, end), (output, literal) in sorted(changes.items()):
            if start < cursor:
                raise ValueError(f"Overlapping source edits: {path}")
            pieces.extend((raw[cursor:start], output))
            cursor = end
            delta = output.count(b"\n") - raw[start:end].count(b"\n")
            if delta:
                movements.append((literal.first_line, literal.last_line, delta))
        pieces.append(raw[cursor:])
        outputs[path] = b"".join(pieces)
        literals(path, outputs[path])  # XML well-formedness and parser smoke gate.
        shifts[path] = movements
    return outputs, originals, shifts
