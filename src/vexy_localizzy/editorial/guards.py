# this_file: src/vexy_localizzy/editorial/guards.py
"""Shape, token and mnemonic checks a review correction must pass before it is applied.

A model may reword a translation, but not what the English source fixes:
placeholders and tags, a trailing ellipsis or colon, surrounding whitespace,
newlines and literal ``\\n`` escapes. Nor may it add or drop an accelerator
(``&``) relative to the current translation. ``problem`` names the first
broken rule so the applier can count and list refusals by reason.
"""

import re
from collections import Counter

from vexy_localizzy.qa.text import COUNT_TOKENS

PRINTF = r"%[-+ 0#]*\d*(?:\.\d+)?[hlLqjzt]*[diouxXeEfFgGaAcspn%]"
PLACEHOLDER = re.compile(r"%L?\d+|%n|" + PRINTF + r"|\{\{[^{}]*\}\}|\{\w+\}|<[^>]+>")
TAG = re.compile(r"<[A-Za-z/!?][^<>]*>")
ENTITY = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]*|#[0-9]+|#[xX][0-9A-Fa-f]+);")
ELLIPSES = ("…", "...")
COLONS = (":", "：")
LITERAL_NEWLINE = "\\n"

PLURAL_FORMS, EMPTY, SHAPE, MNEMONIC = "plural_forms", "empty", "shape", "mnemonic"


def tokens(text: str, *, tags: bool = True) -> list[str]:
    """Placeholders (printf, Qt, brace) and, unless ``tags`` is false, markup tags."""
    found = (m.group(0) for m in PLACEHOLDER.finditer(text or ""))
    return sorted(t for t in found if tags or not t.startswith("<"))


def _edges(text: str) -> tuple[str, str]:
    """Leading and trailing whitespace of ``text``."""
    return text[: len(text) - len(text.lstrip())], text[len(text.rstrip()) :]


def shape(text: str, *, tags: bool = True) -> tuple:
    """What a correction must keep from the English source, whatever it rewords."""
    stripped = text.rstrip()
    return (
        tokens(text, tags=tags),
        stripped.endswith(ELLIPSES),
        stripped.endswith(COLONS),
        _edges(text),
        text.count("\n"),
        text.count(LITERAL_NEWLINE),
    )


def mnemonics(text: str) -> int:
    """Accelerator markers: ``&`` not doubled; entities of rich text are literal.

    In plain Qt text ``&amp;`` underlines the ``a``, so it counts there; once the
    text carries a tag, Qt renders it as rich text and ``&amp;``, ``&nbsp;`` or
    ``&#160;`` are characters, not accelerators.
    """
    if TAG.search(text):
        text = ENTITY.sub("", text)
    return text.count("&") - text.count("&&") * 2


def _pairs(before: object, after: object) -> list[tuple[object, object]] | None:
    """Matching (before, after) forms, or None for a mismatched or empty plural list."""
    if isinstance(before, list) != isinstance(after, list):
        return None
    if not isinstance(after, list):
        return [(before, after)]
    if not after or len(after) != len(before):
        return None
    return list(zip(before, after))


def _same_shape(reference: str, text: str, tags: bool, count_optional: bool) -> bool:
    """True when ``text`` keeps the shape of ``reference``; with ``count_optional``
    it may lack the count placeholder, and nothing else."""
    wanted, got = shape(reference, tags=tags), shape(text, tags=tags)
    if not count_optional:
        return wanted == got
    missing = Counter(wanted[0]) - Counter(got[0])
    extra = Counter(got[0]) - Counter(wanted[0])
    return wanted[1:] == got[1:] and not extra and set(missing) <= set(COUNT_TOKENS)


def problem(
    before: object,
    after: object,
    source: object = None,
    *,
    markup: bool = False,
    count_optional: frozenset[int] = frozenset(),
) -> str | None:
    """The first rule ``after`` breaks, or None when the correction is safe.

    Shape is compared with ``source`` (``before`` when an old candidate lacks
    it), so a fix that restores a lost placeholder passes and a revision that
    keeps a defect does not. The mnemonic count is compared with ``before``.
    ``markup`` (an accepted markup repair) relaxes tags and the mnemonic count
    only; placeholders, punctuation, whitespace and newlines still hold.
    ``count_optional`` names the forms of a plural correction that exactly one
    count selects; such a form may omit ``%n``, as content QA allows.
    """
    pairs = _pairs(before, after)
    if pairs is None:
        return PLURAL_FORMS
    plural = isinstance(after, list)
    for index, (b, a) in enumerate(pairs):
        if not isinstance(a, str) or not a.strip() or not isinstance(b, str):
            return EMPTY
        reference = source if isinstance(source, str) else b
        optional = plural and index in count_optional
        if not _same_shape(reference, a, not markup, optional):
            return SHAPE
        if not markup and mnemonics(b) != mnemonics(a):
            return MNEMONIC
    return None


def safe(before: object, after: object, source: object = None) -> bool:
    """True when ``after`` breaks none of the rules ``problem`` checks."""
    return problem(before, after, source) is None
