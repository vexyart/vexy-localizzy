# this_file: src/vexy_localizzy/formats/ts_shards.py
"""Split a Qt .ts catalog into shards that keep every context whole, and merge back.

An engine translates one batch after another, so a large catalog through a slow
model takes hours. Shards let several ``localizzy translate`` processes run at
once. Split balances message counts across shards (largest context first, into
the lightest shard). Merge prepares the full target template from the source
catalog, fills it from the translated shards by message identity (the pairing
``localizzy upgrade`` uses) and writes one catalog.

Neither step silently replaces work: split refuses an ``out_dir`` that already
holds shards of the same catalog (``force`` removes the earlier
``<stem>-shard<N>.ts`` files first, so no stale shard survives), and merge
refuses an existing output, an output that is one of its inputs, and a shard
whose language is not the target. Messages left unfilled are counted, and the
catalog is still written so they can be inspected.
"""

import copy
import re
from collections.abc import Sequence
from pathlib import Path

from lxml import etree

from vexy_localizzy.catalog import Unit
from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.formats.ts_read import load_bytes
from vexy_localizzy.formats.ts_template import prepare_translation
from vexy_localizzy.formats.ts_write import dump
from vexy_localizzy.upgrade.diff import pair_messages, read_messages

DOCTYPE = "<!DOCTYPE TS>"


def balance(sizes: Sequence[int], parts: int) -> list[list[int]]:
    """Indices of ``sizes`` in ``parts`` buckets, greedy largest-first by load."""
    if isinstance(parts, bool) or not isinstance(parts, int) or parts < 1:
        raise ValueError("parts must be a positive integer")
    buckets: list[list[int]] = [[] for _ in range(parts)]
    loads = [0] * parts
    for size, index in sorted(((s, i) for i, s in enumerate(sizes)), reverse=True):
        lightest = loads.index(min(loads))
        buckets[lightest].append(index)
        loads[lightest] += size
    return [sorted(bucket) for bucket in buckets]


def _shard_bytes(root, ns: str, keep: set[int], loose: bool, doctype: str) -> bytes:
    """A copy of the TS root with only the kept contexts (and top-level messages)."""
    shard = copy.deepcopy(root)
    for index, context in enumerate(shard.findall(ns + "context")):
        if index not in keep:
            shard.remove(context)
    if not loose:
        for message in shard.findall(ns + "message"):
            shard.remove(message)
    return etree.tostring(
        shard, xml_declaration=True, encoding="utf-8", doctype=doctype
    )


def shard_name(source: Path, part: int) -> str:
    return f"{Path(source).stem}-shard{part}.ts"


def clear_shards(source: Path, out_dir: Path, *, force: bool) -> list[Path]:
    """Make room for a new split of ``source`` in ``out_dir``; return removed paths.

    Any ``<stem>-shard*.ts`` (a split shard or a translation named after one)
    refuses the split without ``force``. With ``force`` only the split's own
    ``<stem>-shard<N>.ts`` files are removed; other files are never deleted.
    """
    stem = Path(source).stem
    present = sorted(Path(out_dir).glob(f"{glob_escape(stem)}-shard*.ts"))
    if present and not force:
        names = ", ".join(path.name for path in present)
        raise FileExistsError(f"{out_dir} already holds shards ({names}); pass --force")
    own = re.compile(re.escape(stem) + r"-shard\d+\.ts")
    removed = [path for path in present if own.fullmatch(path.name)]
    for path in removed:
        path.unlink()
    return removed


def glob_escape(text: str) -> str:
    """``text`` with glob metacharacters matched literally."""
    return re.sub(r"([*?\[])", r"[\1]", text)


def split(
    source: Path, out_dir: Path, parts: int, *, force: bool = False
) -> list[dict]:
    """Write ``<stem>-shard<N>.ts`` files to ``out_dir``; return one row per shard.

    Shards that would hold nothing are not written. Messages outside any
    context go to the first shard. Raises FileExistsError when ``out_dir``
    already holds shards of this catalog and ``force`` is not set.
    """
    source, out_dir = Path(source), Path(out_dir)
    tree, ns = xml.parse(source.read_bytes())
    balance([], parts)  # validate before touching the folder
    root = tree.getroot()
    contexts = root.findall(ns + "context")
    loose = len(root.findall(ns + "message"))
    sizes = [len(context.findall(ns + "message")) for context in contexts]
    out_dir.mkdir(parents=True, exist_ok=True)
    clear_shards(source, out_dir, force=force)
    doctype = tree.docinfo.doctype or DOCTYPE
    written = []
    for part, indices in enumerate(balance(sizes, parts), 1):
        extra = loose if part == 1 else 0
        if not indices and not extra:
            continue
        path = out_dir / shard_name(source, part)
        atomic_write(path, _shard_bytes(root, ns, set(indices), part == 1, doctype))
        messages = sum(sizes[i] for i in indices) + extra
        written.append(
            {"path": str(path), "contexts": len(indices), "messages": messages}
        )
    return written


def needs_text(unit: Unit) -> bool:
    """Active messages with a non-empty source must be translated."""
    return unit.state != "vanished" and bool(unit.source.strip())


def fill(unit: Unit, hit: Unit) -> Unit | None:
    """``unit`` carrying the translation of ``hit``, or None when shapes differ."""
    if unit.plural is not None:
        if hit.plural is None or len(hit.plural.forms) != len(unit.plural.forms):
            return None
        forms = unit.plural.model_copy(update={"forms": dict(hit.plural.forms)})
        return unit.model_copy(update={"state": hit.state, "plural": forms})
    if unit.variants is not None:
        if hit.variants is None or len(hit.variants) != len(unit.variants):
            return None
        return unit.model_copy(
            update={"state": hit.state, "variants": list(hit.variants)}
        )
    if hit.target is None:
        return None
    return unit.model_copy(update={"state": hit.state, "target": hit.target})


def check_language(shard: Path, have: str | None, target: str) -> None:
    """ValueError unless the shard's language names the target (``fr`` and
    ``fr_FR`` match each other; ``fr_CA`` and ``fr_FR`` do not)."""
    from vexy_localizzy.locales import canonical_locale
    from vexy_localizzy.translate.run import same_language

    if have:
        have_tag, want_tag = canonical_locale(have), canonical_locale(target)
        if same_language(have, want_tag) or same_language(target, have_tag):
            return
    raise ValueError(f"{shard} is in {have or 'no language'}, not {target}")


def merge(
    source: Path,
    shards: Sequence[Path],
    *,
    target: str,
    plural_count: int,
    out: Path,
    force: bool = False,
) -> dict:
    """Fill the ``target`` template of ``source`` from ``shards`` and write ``out``.

    Only shard messages whose every translation slot has text count as fills.
    Raises FileExistsError when ``out`` exists and ``force`` is not set, and
    ValueError when ``out`` is an input or a shard is in another language.
    """
    out = Path(out)
    inputs = {Path(p).resolve() for p in (source, *shards)}
    if out.resolve() in inputs:
        raise ValueError(f"{out} is an input; choose another output")
    if out.exists() and not force:
        raise FileExistsError(f"{out} exists; pass --force to replace it")
    template = prepare_translation(
        Path(source).read_bytes(), target_lang=target, plural_count=plural_count
    )
    fresh = read_messages(template.document.content)
    found = []
    for shard in shards:
        raw = Path(shard).read_bytes()
        check_language(shard, load_bytes(raw).target_lang, template.target_lang)
        found += [m for m in read_messages(raw) if m.filled and not m.retired]
    pairs = pair_messages(found, fresh)
    units, wanted, unfilled = [], 0, 0
    for index, unit in enumerate(template.units):
        if not needs_text(unit):
            units.append(unit)
            continue
        filled = fill(unit, found[pairs[index]].unit) if index in pairs else None
        units.append(filled or unit)
        wanted += 1
        unfilled += filled is None
    out.parent.mkdir(parents=True, exist_ok=True)
    dump(template.model_copy(update={"units": units}), out)
    return {
        "out": str(out),
        "shards": len(shards),
        "messages": wanted,
        "filled": wanted - unfilled,
        "unfilled": unfilled,
    }
