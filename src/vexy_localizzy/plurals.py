# this_file: src/vexy_localizzy/plurals.py
"""CLDR cardinal plural categories and gettext ``Plural-Forms`` declarations.

The category table lists the CLDR cardinal categories reachable by integer
operands that matter for interface counts (Unicode CLDR supplemental
``plurals.xml``). French, Spanish, Italian and Portuguese also define ``many``
for multiples of a million and compact forms; the table leaves it out, as Qt
and the common gettext rules do. Qt numerus counts live in
``formats.qt_numerus``; this module serves catalogs that name categories and
PO files that need a declaration. Referenced by ``qa.layers``, ``pseudo`` and
``review.workspace``.
"""

import re

from vexy_localizzy.catalog import PluralForms
from vexy_localizzy.formats.qt_numerus import UnknownQtNumerus
from vexy_localizzy.formats.qt_numerus import count as numerus_count

CATEGORIES: dict[str, tuple[str, ...]] = {
    "en": ("one", "other"),
    "de": ("one", "other"),
    "fr": ("one", "other"),
    "es": ("one", "other"),
    "it": ("one", "other"),
    "pt": ("one", "other"),
    "ja": ("other",),
    "zh": ("other",),
    "ar": ("zero", "one", "two", "few", "many", "other"),
    "ru": ("one", "few", "many", "other"),
    "pl": ("one", "few", "many", "other"),
    "cs": ("one", "few", "many", "other"),
}

# gettext never derives this header; a PO projection must state it.
PLURAL_FORMS: dict[str, str] = {
    "en": "nplurals=2; plural=(n != 1);",
    "de": "nplurals=2; plural=(n != 1);",
    "fr": "nplurals=2; plural=(n > 1);",
    "es": "nplurals=2; plural=(n != 1);",
    "it": "nplurals=2; plural=(n != 1);",
    "pt": "nplurals=2; plural=(n != 1);",
    "ja": "nplurals=1; plural=0;",
    "zh": "nplurals=1; plural=0;",
    "ar": (
        "nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : "
        "n%100>=3 && n%100<=10 ? 3 : n%100>=11 ? 4 : 5);"
    ),
    "ru": (
        "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : "
        "n%10>=2 && n%10<=4 && (n%100<12 || n%100>14) ? 1 : 2);"
    ),
    "pl": (
        "nplurals=3; plural=(n==1 ? 0 : "
        "n%10>=2 && n%10<=4 && (n%100<12 || n%100>14) ? 1 : 2);"
    ),
    "cs": "nplurals=3; plural=(n==1 ? 0 : n>=2 && n<=4 ? 1 : 2);",
}

# Category order of the integer rules above, position by position.
POSITIONS: dict[str, tuple[str, ...]] = {
    "ru": ("one", "few", "many"),
    "pl": ("one", "few", "many"),
    "cs": ("one", "few", "other"),
    "ar": ("zero", "one", "two", "few", "many", "other"),
    "ja": ("other",),
    "zh": ("other",),
}


def _primary(lang: str | None) -> str:
    return (lang or "").replace("_", "-").split("-")[0].lower()


def required_categories(lang: str | None) -> frozenset[str]:
    """Required CLDR cardinal categories for a language; ``{other}`` when unknown."""
    return frozenset(CATEGORIES.get(_primary(lang), ("other",)))


def known_locales() -> list[str]:
    """Sorted languages covered by the category table."""
    return sorted(CATEGORIES)


def plural_forms_header(lang: str | None) -> str:
    """The gettext ``Plural-Forms`` declaration for a language.

    A language outside the table gets ``n != 1`` when Qt counts two forms for it
    and a single form when Qt counts one. A language with more forms and no rule
    here raises ValueError: a guessed rule would file translations under the
    wrong counts, so the caller must pass the declaration.
    """
    code = _primary(lang)
    if code in PLURAL_FORMS:
        return PLURAL_FORMS[code]
    try:
        count = numerus_count(lang or "")
    except UnknownQtNumerus:
        count = 0
    if count == 1:
        return "nplurals=1; plural=0;"
    if count == 2:
        return "nplurals=2; plural=(n != 1);"
    raise ValueError(f"No gettext plural rule for {lang!r}; pass plural_forms")


def positional_categories(lang: str | None) -> tuple[str, ...]:
    """Category names in gettext/Qt index order for the languages in the table.

    Native TS and PO readers keep indices. This mapping converts category-keyed
    catalogs; an unknown rule raises so the caller supplies ``plural_order``.
    """
    code = _primary(lang)
    if code not in PLURAL_FORMS:
        raise ValueError(
            f"No positional plural mapping for {lang!r}; supply plural_order"
        )
    return POSITIONS.get(code, ("one", "other"))


_ICU_PLURAL_START = re.compile(r"\{\s*\w+\s*,\s*plural\s*,")
_ICU_KEYWORD = re.compile(r"\s*(?:offset\s*:\s*\d+\s*)?(=?\w+)\s*\{")


def closing_brace(text: str, start: int) -> int | None:
    """Index of the brace that closes the one at ``start``; None when unbalanced."""
    depth = 0
    for index in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[index], 0)
        if depth == 0:
            return index
    return None


def parse_icu_plural(text: str) -> PluralForms | None:
    """Read the category arms of the first ICU ``{var, plural, …}`` block.

    The block and each arm are found by brace matching, so the block may sit
    anywhere in the message and an arm may hold nested placeholders. ``=0`` is
    recorded as ``zero``; ``offset:`` is skipped. Returns None when there is no
    complete block.
    """
    start = _ICU_PLURAL_START.search(text)
    if start is None or (end := closing_brace(text, start.start())) is None:
        return None
    forms: dict[str, str] = {}
    index = start.end()
    while keyword := _ICU_KEYWORD.match(text, index, end):
        opening = keyword.end() - 1
        closing = closing_brace(text, opening)
        if closing is None or closing > end:
            return None
        key = keyword.group(1)
        forms["zero" if key == "=0" else key] = text[opening + 1 : closing].strip()
        index = closing + 1
    return PluralForms(icu=text, forms=forms) if forms else None
