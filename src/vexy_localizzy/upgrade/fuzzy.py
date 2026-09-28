# this_file: src/vexy_localizzy/upgrade/fuzzy.py
"""Loose source comparison for the upgrade fuzzy tiers.

Only upgrade uses this. The direct memory matches verbatim on purpose.
"""

import re
import unicodedata
from difflib import SequenceMatcher

_SPACE = re.compile(r"\s+")
_ACCEL = re.compile(r"&&|&(?=\S)")
_QT_ARG = re.compile(r"%L?(?:\d+|n)")
_BRACE = re.compile(r"\{[A-Za-z_][\w]*\}")
_TRAIL = re.compile(r"[\s:.…]+$")


def loose(text: str) -> str:
    """NFC; collapse whitespace; '...'→'…'; drop trailing ':' '…' '.' and spaces;
    drop single '&' accelerators; %L?\\d+ and %L?n → '%#'; {name} → '{#}'; casefold."""
    text = unicodedata.normalize("NFC", text)
    text = _SPACE.sub(" ", text).strip()
    text = text.replace("...", "…")
    text = _TRAIL.sub("", text)
    text = _ACCEL.sub(lambda m: "&" if m.group() == "&&" else "", text)
    text = _QT_ARG.sub("%#", text)
    text = _BRACE.sub("{#}", text)
    return text.casefold()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, loose(a), loose(b)).ratio()
