# this_file: src/vexy_localizzy/upgrade/diff.py
"""Compare an approved Qt .ts catalog with a fresh one, message by message.

Messages pair the way ``localizzy upgrade`` pairs them: by ``message/@id`` when
the old catalog knows that id, otherwise by (context, source, comment), first
come first served for repeats. The report has four sections, so a reviewer sees
what lupdate brought in before running an upgrade:

  new_untranslated   only in the fresh catalog, without a complete translation
  new_translated     only in the fresh catalog, already translated
  changed            in both, with a different translation (old and new shown)
  removed            only in the approved catalog

Vanished and obsolete messages take no part.
"""

from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from vexy_localizzy.catalog import Unit
from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.formats.ts_read import load_bytes
from vexy_localizzy.upgrade.identity import (
    MessageRef,
    is_filled,
    key_identity,
    refs_from_tree,
)

SECTIONS = ("new_untranslated", "new_translated", "changed", "removed")
TITLES = {
    "new_untranslated": "Not translated in the fresh catalog",
    "changed": "Translation differs",
    "new_translated": "New in the fresh catalog, already translated",
    "removed": "Removed from the fresh catalog",
}
RETIRED = ("vanished", "obsolete")


@dataclass(frozen=True)
class Message:
    """One TS message: its XML identity, its catalog unit, and whether every
    translation slot (plural form, length variant) carries text."""

    ref: MessageRef
    unit: Unit
    filled: bool

    @property
    def retired(self) -> bool:
        return self.ref.kind in RETIRED


def read_messages(raw: bytes) -> list[Message]:
    """Every message of TS bytes in document order."""
    tree, ns = xml.parse(raw)
    refs = refs_from_tree(tree.getroot(), ns)
    units = load_bytes(raw).units
    return [
        Message(ref, unit, is_filled(xml.translation(ref.element, ns), ns))
        for ref, unit in zip(refs, units, strict=True)
    ]


def pair_messages(old: Sequence[Message], new: Sequence[Message]) -> dict[int, int]:
    """Map indices in ``new`` to indices in ``old``, as upgrade pairs identities.

    An old message with an id is reachable only through that id; a new message
    whose id the old side lacks falls back to its (context, source, comment).
    An id known only from a retired old message pairs with nothing.
    """
    known = {m.ref.msg_id for m in old if m.ref.msg_id}
    by_id: dict[str, deque[int]] = defaultdict(deque)
    by_key: dict[tuple, deque[int]] = defaultdict(deque)
    for index, message in enumerate(old):
        if message.retired:
            continue
        if message.ref.msg_id:
            by_id[message.ref.msg_id].append(index)
        else:
            by_key[key_identity(message.ref)].append(index)
    pairs = {}
    for index, message in enumerate(new):
        if message.retired:
            continue
        msg_id = message.ref.msg_id
        if msg_id in known:
            queue = by_id.get(msg_id)
        else:
            queue = by_key.get(key_identity(message.ref))
        if queue:
            pairs[index] = queue.popleft()
    return pairs


def text_of(unit: Unit) -> str | list[str]:
    """The translation as one string, or a list for plurals and length variants."""
    if unit.plural is not None:
        return [unit.plural.forms[k] for k in sorted(unit.plural.forms, key=int)]
    if unit.variants is not None:
        return list(unit.variants)
    return unit.target or ""


def _row(message: Message) -> dict:
    unit = message.unit
    return {
        "context": unit.context,
        "source": unit.source,
        "comment": unit.disambiguation or "",
    }


def compare(old_path: Path, new_path: Path) -> dict:
    """The four-section report plus counts, as plain JSON-ready data."""
    old = read_messages(Path(old_path).read_bytes())
    new = read_messages(Path(new_path).read_bytes())
    pairs = pair_messages(old, new)
    report: dict = {"old": str(old_path), "new": str(new_path)}
    report |= {section: [] for section in SECTIONS}
    for index, message in enumerate(new):
        if message.retired:
            continue
        row, after = _row(message), text_of(message.unit)
        if index not in pairs:
            section = "new_translated" if message.filled else "new_untranslated"
            report[section].append(row | {"new": after})
            continue
        before = old[pairs[index]]
        if text_of(before.unit) != after:
            report["changed"].append(
                row
                | {
                    "old": text_of(before.unit),
                    "new": after,
                    "old_state": before.unit.state,
                    "new_state": message.unit.state,
                }
            )
    paired = set(pairs.values())
    for index, message in enumerate(old):
        if not message.retired and index not in paired:
            report["removed"].append(_row(message) | {"old": text_of(message.unit)})
    report["counts"] = {section: len(report[section]) for section in SECTIONS}
    report["counts"]["old_messages"] = sum(not m.retired for m in old)
    report["counts"]["new_messages"] = sum(not m.retired for m in new)
    return report


def _filled(value: str | list[str]) -> bool:
    values = value if isinstance(value, list) else [value]
    return bool(values) and all(v.strip() for v in values)


def _describe(row: dict) -> list[str]:
    head = f"- **{row['context']}** | {row['source']!r}"
    lines = [head + (f" | {row['comment']!r}" if row["comment"] else "")]
    if "old" in row and "new" in row:
        lines.append(f"    old: {row['old']!r}  ({row['old_state']})")
        lines.append(f"    new: {row['new']!r}  ({row['new_state']})")
    elif "new" in row and _filled(row["new"]):
        lines.append(f"    new: {row['new']!r}")
    elif "old" in row:
        lines.append(f"    old: {row['old']!r}")
    return lines


def render(report: dict) -> str:
    """The report as Markdown: a count line, then one section per non-empty list."""
    c = report["counts"]
    lines = [
        f"# {Path(report['old']).name} (approved) vs {Path(report['new']).name} (fresh)",
        "",
        f"old {c['old_messages']} messages, new {c['new_messages']}; "
        f"new untranslated {c['new_untranslated']}, new already translated "
        f"{c['new_translated']}, changed {c['changed']}, removed {c['removed']}",
        "",
    ]
    for section in ("new_untranslated", "changed", "new_translated", "removed"):
        rows = report[section]
        if not rows:
            continue
        lines += [f"## {TITLES[section]} ({len(rows)})", ""]
        for row in rows:
            lines += _describe(row)
        lines.append("")
    return "\n".join(lines)
