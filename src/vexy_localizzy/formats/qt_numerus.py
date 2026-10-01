# this_file: src/vexy_localizzy/formats/qt_numerus.py
"""Qt Linguist numerus form counts and selection rules per language.

Qt decides how many ``<numerusform>`` elements a ``.ts`` message carries from
its own rule table, not from CLDR plural categories. French has two Qt forms
(n <= 1) while CLDR lists three categories; Polish has three Qt forms while
CLDR has four. Callers that prepare a catalog for a new language must use this
table, or pass an explicit count.

``form_index`` says which form Qt shows for a count, and
``single_number_forms`` which forms exactly one count selects; content QA
lets such a form omit ``%n``.

Source: qttools ``src/linguist/shared/numerus.cpp`` (branch 5.15), read on
2026-09-28 (counts) and 2026-10-01 (rules). The tables are factual data about
Qt's behaviour; Qt itself is licensed under the LGPL/GPL and none of its code
is copied here. Language names were mapped to ISO 639 codes with
``langcodes``. Brazilian Portuguese uses Qt's "French style" rule (n > 1) but
the count is the same as European Portuguese.
"""

from collections import Counter
from collections.abc import Callable
from functools import cache

from langcodes import Language

QT_NUMERUS_FORMS: dict[str, int] = {
    "aa": 2,
    "ab": 2,
    "af": 2,
    "am": 2,
    "ar": 6,
    "as": 2,
    "ay": 2,
    "az": 2,
    "ba": 2,
    "be": 3,
    "bg": 2,
    "bi": 1,
    "bn": 2,
    "bo": 1,
    "br": 2,
    "bs": 3,
    "ca": 2,
    "co": 2,
    "cs": 3,
    "cy": 5,
    "da": 2,
    "de": 2,
    "dv": 3,
    "dz": 1,
    "el": 2,
    "en": 2,
    "eo": 2,
    "es": 2,
    "et": 2,
    "eu": 2,
    "fa": 1,
    "fi": 2,
    "fil": 3,
    "fj": 1,
    "fo": 2,
    "fr": 2,
    "fur": 2,
    "fy": 2,
    "ga": 3,
    "gd": 4,
    "gl": 2,
    "gn": 1,
    "gu": 2,
    "gv": 3,
    "ha": 2,
    "he": 2,
    "hi": 2,
    "hr": 3,
    "hu": 1,
    "hy": 2,
    "ia": 2,
    "id": 1,
    "ie": 2,
    "ik": 3,
    "is": 2,
    "it": 2,
    "iu": 3,
    "ja": 1,
    "jv": 1,
    "ka": 2,
    "kk": 2,
    "kl": 2,
    "km": 2,
    "kn": 2,
    "ko": 1,
    "ks": 2,
    "ku": 2,
    "kw": 2,
    "ky": 2,
    "la": 2,
    "lb": 2,
    "lg": 2,
    "ln": 2,
    "lo": 2,
    "lt": 3,
    "lv": 3,
    "mg": 2,
    "mi": 3,
    "mk": 3,
    "ml": 2,
    "mn": 2,
    "mr": 2,
    "ms": 1,
    "mt": 4,
    "my": 1,
    "na": 1,
    "nb": 2,
    "no": 2,  # Qt's QLocale::Norwegian; the macrolanguage of nb and nn
    "ne": 2,
    "nl": 2,
    "nn": 2,
    "nso": 2,
    "oc": 2,
    "om": 1,
    "or": 2,
    "pa": 2,
    "pl": 3,
    "ps": 2,
    "pt": 2,
    "qu": 2,
    "rm": 2,
    "rn": 2,
    "ro": 3,
    "ru": 3,
    "rw": 2,
    "sa": 3,
    "sd": 2,
    "se": 3,
    "si": 2,
    "sk": 3,
    "sl": 4,
    "sm": 3,
    "sn": 2,
    "so": 2,
    "sq": 2,
    "sr": 3,
    "ss": 2,
    "st": 2,
    "su": 1,
    "sv": 2,
    "sw": 2,
    "ta": 2,
    "te": 2,
    "tg": 2,
    "th": 1,
    "ti": 2,
    "tk": 2,
    "tl": 3,
    "tn": 2,
    "to": 2,
    "tr": 1,
    "ts": 2,
    "tt": 1,
    "ug": 2,
    "uk": 3,
    "ur": 2,
    "uz": 2,
    "vi": 1,
    "vo": 2,
    "wa": 2,
    "wo": 2,
    "xh": 2,
    "yi": 2,
    "yo": 1,
    "za": 1,
    "zh": 1,
    "zu": 2,
}


Rule = Callable[[int], bool]


def _teens(n: int) -> bool:
    return 10 <= n % 100 <= 19


# One test per form except the last, tried in order; the last form takes every
# other count. Transcribed from the rule arrays of numerus.cpp, which Qt
# evaluates at run time (its gettext strings differ for Macedonian and Tagalog).
STYLE_RULES: dict[str, tuple[Rule, ...]] = {
    "japanese": (),
    "english": (lambda n: n == 1,),
    "french": (lambda n: n <= 1,),
    "latvian": (lambda n: n % 10 == 1 and n % 100 != 11, lambda n: n != 0),
    "icelandic": (lambda n: n % 10 == 1 and n % 100 != 11,),
    "irish": (lambda n: n == 1, lambda n: n == 2),
    "gaelic": (
        lambda n: n in (1, 11),
        lambda n: n in (2, 12),
        lambda n: 3 <= n <= 19,
    ),
    "slovak": (lambda n: n == 1, lambda n: 2 <= n <= 4),
    "macedonian": (lambda n: n % 10 == 1, lambda n: n % 10 == 2),
    "lithuanian": (
        lambda n: n % 10 == 1 and n % 100 != 11,
        lambda n: n % 10 != 0 and not _teens(n),
    ),
    "russian": (
        lambda n: n % 10 == 1 and n % 100 != 11,
        lambda n: 2 <= n % 10 <= 4 and not _teens(n),
    ),
    "polish": (lambda n: n == 1, lambda n: 2 <= n % 10 <= 4 and not _teens(n)),
    "romanian": (lambda n: n == 1, lambda n: n == 0 or 1 <= n % 100 <= 19),
    "slovenian": (
        lambda n: n % 100 == 1,
        lambda n: n % 100 == 2,
        lambda n: 3 <= n % 100 <= 4,
    ),
    "maltese": (
        lambda n: n == 1,
        lambda n: n == 0 or 1 <= n % 100 <= 10,
        lambda n: 11 <= n % 100 <= 19,
    ),
    "welsh": (
        lambda n: n == 0,
        lambda n: n == 1,
        lambda n: 2 <= n <= 5,
        lambda n: n == 6,
    ),
    "arabic": (
        lambda n: n == 0,
        lambda n: n == 1,
        lambda n: n == 2,
        lambda n: 3 <= n % 100 <= 10,
        lambda n: n % 100 >= 11,
    ),
    "tagalog": (lambda n: n <= 1, lambda n: n % 10 in (4, 6, 9)),
}

# Languages whose rule is not the usual one for their count: a language with one
# form uses "japanese" and one with two forms "english" unless it is named here.
# numerus.cpp lists Filipino under both the French and the Tagalog rule; the
# count table above gives it three forms, so it follows the Tagalog rule here.
LANGUAGE_STYLES: dict[str, str] = {
    **dict.fromkeys(("br", "fr", "hy", "ti", "wa"), "french"),
    **dict.fromkeys(("dv", "ga", "gv", "ik", "iu", "mi", "sa", "se", "sm"), "irish"),
    **dict.fromkeys(("cs", "sk"), "slovak"),
    **dict.fromkeys(("be", "bs", "hr", "ru", "sr", "uk"), "russian"),
    **dict.fromkeys(("fil", "tl"), "tagalog"),
    "ar": "arabic",
    "cy": "welsh",
    "gd": "gaelic",
    "is": "icelandic",
    "lt": "lithuanian",
    "lv": "latvian",
    "mk": "macedonian",
    "mt": "maltese",
    "pl": "polish",
    "ro": "romanian",
    "sl": "slovenian",
}
DEFAULT_STYLES = {1: "japanese", 2: "english"}
# Portuguese follows the English rule, Brazilian Portuguese the French one.
FRENCH_STYLE_REGIONS = {("pt", "BR")}
# Every rule depends on the count below 20 or on its last two digits, so a form
# that several counts select shows at least two of them below this bound.
PROBED_COUNTS = 300


class UnknownQtNumerus(ValueError):
    """Qt has no numerus rule for this language; pass ``plural_count`` explicitly."""


def _language(lang: str) -> Language:
    """Parse a BCP 47 or Qt-style tag; an ``@modifier`` is dropped."""
    tag = lang.split("@", 1)[0].replace("_", "-")
    try:
        return Language.get(tag)
    except Exception as error:  # noqa: BLE001 - any parse failure is an unknown tag
        raise UnknownQtNumerus(f"Cannot parse language tag {lang!r}") from error


def count(lang: str) -> int:
    """Return Qt's numerus form count for a BCP 47 or Qt-style tag such as ``pl``,
    ``es_MX`` or ``sr@latin`` (an ``@modifier`` never changes the count)."""
    primary = _language(lang).language or ""
    if primary in QT_NUMERUS_FORMS:
        return QT_NUMERUS_FORMS[primary]
    raise UnknownQtNumerus(
        f"Qt Linguist has no numerus rule for {lang!r}; pass an explicit plural count"
    )


def _rules(lang: str) -> tuple[Rule, ...]:
    """The form tests of ``lang``; UnknownQtNumerus when Qt has no rule for it."""
    forms = count(lang)
    language = _language(lang)
    if (language.language, language.territory) in FRENCH_STYLE_REGIONS:
        return STYLE_RULES["french"]
    style = LANGUAGE_STYLES.get(language.language or "") or DEFAULT_STYLES.get(forms)
    if style is None:
        raise UnknownQtNumerus(f"No numerus rule is recorded for {lang!r}")
    return STYLE_RULES[style]


def form_index(lang: str, n: int) -> int:
    """The index of the numerus form Qt shows for the count ``n`` in ``lang``."""
    rules = _rules(lang)
    return next((i for i, rule in enumerate(rules) if rule(n)), len(rules))


@cache
def single_number_forms(lang: str) -> frozenset[int]:
    """Indices of the forms of ``lang`` that exactly one count selects.

    Arabic has three (zero, one, two), English and Polish one (the singular),
    Russian none, because its first form also serves 21, 31 and 101. Such a
    form can spell its number out, so a translation may leave ``%n`` out of
    it. Referenced by ``qa.catalog`` and ``qa.text``.
    """
    hits = Counter(form_index(lang, n) for n in range(PROBED_COUNTS))
    return frozenset(form for form, selected in hits.items() if selected == 1)
