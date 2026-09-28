# this_file: src/vexy_localizzy/formats/qt_numerus.py
"""Qt Linguist numerus form counts per language.

Qt decides how many ``<numerusform>`` elements a ``.ts`` message carries from
its own rule table, not from CLDR plural categories. French has two Qt forms
(n <= 1) while CLDR lists three categories; Polish has three Qt forms while
CLDR has four. Callers that prepare a catalog for a new language must use this
table, or pass an explicit count.

Source: qttools ``src/linguist/shared/numerus.cpp`` (branch 5.15), read on
2026-09-28. The table is factual data about Qt's behaviour; Qt itself is
licensed under the LGPL/GPL and none of its code is copied here. Language
names were mapped to ISO 639 codes with ``langcodes``. Brazilian Portuguese
uses Qt's "French style" rule (n > 1) but the count is the same as
European Portuguese.
"""

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


class UnknownQtNumerus(ValueError):
    """Qt has no numerus rule for this language; pass ``plural_count`` explicitly."""


def count(lang: str) -> int:
    """Return Qt's numerus form count for a BCP 47 or Qt-style tag such as ``pl``, ``es_MX``."""
    tag = lang.replace("_", "-")
    try:
        primary = Language.get(tag).language or ""
    except Exception as error:  # noqa: BLE001 - any parse failure is an unknown tag
        raise UnknownQtNumerus(f"Cannot parse language tag {lang!r}") from error
    if primary in QT_NUMERUS_FORMS:
        return QT_NUMERUS_FORMS[primary]
    raise UnknownQtNumerus(
        f"Qt Linguist has no numerus rule for {lang!r}; pass an explicit plural count"
    )
