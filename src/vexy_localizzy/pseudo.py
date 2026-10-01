# this_file: src/vexy_localizzy/pseudo.py
"""Pseudo-localization: accent, expand and wrap text; keep every token intact.

A pseudo catalog shows hard-coded strings (they stay plain), clipped layouts
(the padding overflows) and concatenation (the brackets split) before any
translator is paid. Placeholders, tags, entities and accelerators survive
verbatim; only the plain runs of text change. Referenced by ``localizzy pseudo``.
"""

import re

from vexy_localizzy.catalog import Catalog, Unit
from vexy_localizzy.plurals import closing_brace, parse_icu_plural

MODES = ("accent", "bracket", "rtl")
DEFAULT_EXPANSION = 0.4  # share of the plain text length added as padding
PSEUDO_LOCALE = "xx-pseudo"
PAD = "ē"
RLE, PDF = "‫", "‬"  # right-to-left embedding and its terminator

_ACCENT_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "αβčδēƒğħīĵķłмņōρqřšţůvŵχŷžÀßČĐÉFĞĦÌĴĶŁМÑÓÞQŔŠŢÛVŴXŶŻ",
)
# Tokens that survive verbatim. Order matters: named and positional printf
# before Qt's %1, so "%1$s" is one token. The printf grammar has no space flag,
# so "100% done" is not read as a conversion.
_TOKEN = re.compile(
    r"%\(\w+\)[sdifeg]"
    r"|%(?:\d+\$)?[-+0#]*\d*(?:\.\d+)?(?:hh|h|ll|l|q|j|z|t)?[diouxXeEfFgGaAcsp]"
    r"|%L?n|%L?\d+"
    r"|<[^>]+>"
    r"|&#?\w+;|&&|&\w"
)
_ICU_HEAD = re.compile(r"\s*\w+\s*,\s*(?:plural|select|selectordinal)\s*,")


def _icu_block(block: str) -> tuple[str, int]:
    """A ``{…}`` block: placeholders stay; plural and select arms are transformed."""
    head = _ICU_HEAD.match(block, 1)
    if head is None:
        return block, 0  # {name}, {{name}}, {0}: a placeholder
    out, plain, index = [block[: head.end()]], 0, head.end()
    while index < len(block) - 1:
        if block[index] != "{" or (end := closing_brace(block, index)) is None:
            out.append(block[index])  # keywords, =0, offset:1 and spacing
            index += 1
            continue
        arm, count = _transform(block[index + 1 : end])
        out.append("{" + arm + "}")
        plain += count
        index = end + 1
    return "".join(out) + "}", plain


def _transform(text: str) -> tuple[str, int]:
    """Accent the plain runs of ``text``; return it with the plain character count."""
    out, plain, index = [], 0, 0
    while index < len(text):
        if text[index] == "{" and (end := closing_brace(text, index)) is not None:
            block, count = _icu_block(text[index : end + 1])
            out.append(block)
            plain += count
            index = end + 1
        elif token := _TOKEN.match(text, index):
            out.append(token.group())
            index = token.end()
        else:
            out.append(text[index].translate(_ACCENT_MAP))
            plain += 1
            index += 1
    return "".join(out), plain


def pseudo_string(
    text: str, *, expansion: float = DEFAULT_EXPANSION, mode: str = "accent"
) -> str:
    """Pseudo-localize one string, protecting placeholders, tags and accelerators."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}")
    if not text:
        return text
    if mode == "rtl":
        return f"{RLE}{text}{PDF}"
    body, plain_length = _transform(text)
    pad = PAD * max(1, int(plain_length * expansion))
    return f"[{body} {pad}]" if mode == "bracket" else f"⟦{body}{pad}⟧"


def _pseudo_unit(unit: Unit, pseudo) -> Unit:
    """Fill every native target shape of a unit from its source."""
    updates: dict[str, object] = {"state": "translated"}
    if unit.plural is not None and unit.plural.icu is not None:
        target = pseudo(unit.source)
        updates.update(target=target, plural=parse_icu_plural(target))
    elif unit.plural is not None:
        forms = {key: pseudo(unit.source) for key in unit.plural.forms}
        variants = {
            key: [forms[key]] * len(values)
            for key, values in unit.plural.variants.items()
        }
        plural = unit.plural.model_copy(update={"forms": forms, "variants": variants})
        updates.update(target=None, plural=plural)
    elif unit.variants is not None:
        updates.update(target=None, variants=[pseudo(unit.source)] * len(unit.variants))
    else:
        updates["target"] = pseudo(unit.source)
    return unit.model_copy(update=updates)


def pseudo_catalog(
    catalog: Catalog, *, expansion: float = DEFAULT_EXPANSION, mode: str = "accent"
) -> Catalog:
    """A pseudo-locale copy of a catalog; vanished messages stay untouched."""

    def pseudo(text: str) -> str:
        return pseudo_string(text, expansion=expansion, mode=mode)

    units = [
        unit if unit.state == "vanished" else _pseudo_unit(unit, pseudo)
        for unit in catalog.units
    ]
    return catalog.model_copy(update={"target_lang": PSEUDO_LOCALE, "units": units})


def pseudo_mapping(
    mapping: dict[str, str],
    *,
    expansion: float = DEFAULT_EXPANSION,
    mode: str = "accent",
) -> dict[str, str]:
    """Pseudo-localize a flat key to string mapping."""
    return {
        key: pseudo_string(value, expansion=expansion, mode=mode)
        for key, value in mapping.items()
    }
