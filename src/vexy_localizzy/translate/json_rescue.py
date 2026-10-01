# this_file: src/vexy_localizzy/translate/json_rescue.py
"""Second chances for a JSON item that failed in its batch.

A long article with heavy inline HTML often fails its markup check as a whole,
on every retry, and one failing item rejects its whole batch. ``rescue_item``
takes one such item through three paths and says which one filled it:

- ``whole``: the item alone, in one request;
- ``paragraphs``: split at blank lines, one request per paragraph, a
  ``<pre>`` block kept verbatim and untranslated, then reassembled;
- ``masked``: a paragraph that still fails is sent with its markup replaced by
  numbered tokens (``[[1]]``); the markup is restored afterwards, and the
  paragraph is rejected if a token is missing or repeated.

The reassembled item passes the same checks as any other item
(``json_checks.check_item``) or it is rejected. An outage is never a reason to
split: only an answer that cannot be used is. Referenced by ``json_file``.
"""

import re

from vexy_localizzy.translate.json_checks import blocking, check, check_item
from vexy_localizzy.translate.json_request import MASK_RULES, Ask, Rejected

WHOLE, PARAGRAPHS, MASKED = "whole", "paragraphs", "masked"
PRE_BLOCK = re.compile(r"(<pre\b.*?</pre\s*>)", re.DOTALL | re.IGNORECASE)
BLANK_LINES = re.compile(r"(\n[ \t]*\n\s*)")
EDGES = re.compile(r"(\s*)(.*?)(\s*)", re.DOTALL)
# What a model damages most: tags and comments, inline code, Markdown link targets.
MARKUP = re.compile(
    r"<!--.*?-->|</?[A-Za-z][^<>]*>|`[^`\n]+`|(?<=\])\([^)\s]+\)", re.DOTALL
)
TOKEN = re.compile(r"\[\[(\d+)\]\]")


def split_paragraphs(text: str) -> list[tuple[str, bool]]:
    """``(piece, translate?)`` pairs that join back to ``text`` exactly.

    Pieces to translate are the paragraphs between blank lines, without their
    edge whitespace. Blank lines, edge whitespace and ``<pre>`` blocks (which
    may hold blank lines) are kept as they are.
    """
    pieces: list[tuple[str, bool]] = []
    for index, part in enumerate(PRE_BLOCK.split(text)):
        if index % 2:
            pieces.append((part, False))
            continue
        for chunk in BLANK_LINES.split(part):
            lead, core, trail = EDGES.fullmatch(chunk).groups()
            pieces += [(lead, False), (core, True), (trail, False)]
    return [(piece, send) for piece, send in pieces if piece]


def mask(text: str) -> tuple[str, list[str]]:
    """``text`` with each markup run replaced by ``[[n]]``, and the runs in order.

    Raises ``Rejected`` when the text already holds such a token, because the
    restored translation could not tell the two apart.
    """
    if TOKEN.search(text):
        raise Rejected("the text already contains a [[n]] token")
    markup: list[str] = []

    def token(match: re.Match) -> str:
        markup.append(match.group())
        return f"[[{len(markup)}]]"

    return MARKUP.sub(token, text), markup


def token_problems(translated: str, count: int) -> list[str]:
    """Why the tokens of a masked translation are wrong; empty when each of
    ``[[1]]`` to ``[[count]]`` appears exactly once and no other token does."""
    found = TOKEN.findall(translated)
    wanted = [str(number) for number in range(1, count + 1)]
    if sorted(found) == sorted(wanted):
        return []
    missing = [f"[[{n}]]" for n in wanted if n not in found]
    other = sorted({f"[[{n}]]" for n in found if found.count(n) > 1 or n not in wanted})
    return [f"token missing: {missing}; repeated or unknown: {other}"]


def unmask(translated: str, markup: list[str]) -> str:
    """Put the markup back; ``Rejected`` when a token is missing, repeated or unknown."""
    if problems := token_problems(translated, len(markup)):
        raise Rejected("; ".join(problems))
    return TOKEN.sub(lambda match: markup[int(match.group(1)) - 1], translated)


def _paragraph(
    row_id: str, text: str, ask: Ask, plain_first: bool
) -> tuple[str, str, bool]:
    """Translated paragraph, the reported model, and whether masking was needed."""
    if plain_first:
        try:
            got, model = ask(
                [{"id": row_id, "text": text}],
                lambda got: blocking(check(text, got[row_id]["text"], row_id)),
            )
            return got[row_id]["text"], model, False
        except Rejected:
            pass
    masked, markup = mask(text)
    if not markup:
        raise Rejected(f"{row_id}: no markup to mask")
    got, model = ask(
        [{"id": row_id, "text": masked}],
        lambda got: token_problems(got[row_id]["text"], len(markup)),
        MASK_RULES,
    )
    return unmask(got[row_id]["text"], markup), model, True


def by_paragraphs(row: dict, ask: Ask) -> tuple[dict, str | None, str]:
    """``row`` translated piece by piece: the item, its models and the path.

    A title is translated as a piece of its own. A paragraph is first sent as
    it is, unless that would repeat the request that already failed (an item of
    one paragraph and no title), then with masked markup. The models that
    answered are joined with commas; None when nothing had to be sent (a text
    that is one ``<pre>`` block). Raises ``Rejected`` when a paragraph cannot
    be translated or the reassembled item fails its checks; an outage
    propagates.
    """
    pieces = split_paragraphs(row["text"])
    plain_first = "title" in row or sum(send for _, send in pieces) > 1
    item, models, path = {}, [], PARAGRAPHS
    todo = [(f"{row['id']}#{n}", piece, send) for n, (piece, send) in enumerate(pieces)]
    if "title" in row:
        todo.insert(0, (f"{row['id']}#title", row["title"], True))
    parts = []
    for piece_id, piece, send in todo:
        if send:
            piece, model, masked = _paragraph(piece_id, piece, ask, plain_first)
            models.append(model)
            path = MASKED if masked else path
        parts.append(piece)
    if "title" in row:
        item["title"] = parts.pop(0)
    item["text"] = "".join(parts)
    if rejected := blocking(check_item(row, item)):
        raise Rejected(f"rejected by QA: {rejected}")
    return item, ", ".join(dict.fromkeys(models)) or None, path


def rescue_item(row: dict, ask: Ask, *, alone: bool) -> tuple[dict, str | None, str]:
    """The translated item for ``row``, the reported model, and the path taken.

    ``alone`` sends the whole item in a request of its own first; pass False
    when that request was already made and its answer rejected. Raises
    ``Rejected`` when no path gives an item that passes its checks, and the
    transport error when the provider is unavailable.
    """
    if alone:
        try:
            got, model = ask(
                [row], lambda got: blocking(check_item(row, got[row["id"]]))
            )
            return got[row["id"]], model, WHOLE
        except Rejected:
            pass
    return by_paragraphs(row, ask)
