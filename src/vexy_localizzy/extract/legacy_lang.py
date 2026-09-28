# this_file: src/vexy_localizzy/extract/legacy_lang.py
"""Historical language-tag and text policy of the fl10n TMX converters.

Verbatim port of ``adobe2tmx.norm_lang``/``clean_text``, the ``oss2tmx`` extra
region and script tables, and ``ts2tmx.stem_lang``. This policy shortens
default regions and may guess from filenames; the strict extractor in
``vexy_localizzy.extract.single`` does neither. Adapted from fl10n; see NOTICE.

Deliberate departures from the legacy tools: script subtags (``sr-Latn``) and
numeric regions (``es-419``) are kept instead of being dropped; European
Portuguese is written ``pt-PT`` instead of ``pt``; and Apple's ``pt.lproj``,
which is Brazilian Portuguese, becomes ``pt-BR``.
"""

import re

PIVOT = "en"
XML_BAD = re.compile("[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\ud800-\\udfff\\ufffe\\uffff]")

# Region suffixes that are the default for a language and can be dropped.
DEFAULT_REGION = {
    "en": "US",
    "de": "DE",
    "fr": "FR",
    "ja": "JP",
    "es": "ES",
    "sv": "SE",
    "da": "DK",
    "nl": "NL",
    "it": "IT",
    "nb": "NO",
    "no": "NO",
    "fi": "FI",
    "el": "GR",
    "cs": "CZ",
    "pl": "PL",
    "hu": "HU",
    "ru": "RU",
    "tr": "TR",
    "ro": "RO",
    "uk": "UA",
    "he": "IL",
    "ar": "AE",
    "ko": "KR",
    "id": "ID",
    "vi": "VN",
    "th": "TH",
    "sk": "SK",
    "sl": "SI",
    "hr": "HR",
    "bg": "BG",
    "ca": "ES",
    "cy": "GB",
    "et": "EE",
    "lt": "LT",
    "lv": "LV",
    "ms": "MY",
    "fil": "PH",
    "hi": "IN",
    "bn": "IN",
    "ta": "IN",
}
LANG_ALIASES = {
    "english": "en",
    "no": "nb",
    "zh-hans": "zh-CN",
    "zh-hant": "zh-TW",
    "zh": "zh-CN",
    "pt": "pt-PT",
    "cs-cs": "cs",
    "iw": "he",
}
PSEUDO_LANGS = {"zz", "xm", "en-xm", "zz-zz", "en-zz", "x-pseudo"}
# Apple .lproj names whose meaning differs from the same bare tag elsewhere.
APPLE_LPROJ = {"pt": "pt-BR"}

# Default regions beyond DEFAULT_REGION, dropped by oss2tmx to shorten codes.
EXTRA_DEFAULT_REGION = {
    "af": "ZA",
    "am": "ET",
    "az": "AZ",
    "be": "BY",
    "bs": "BA",
    "eu": "ES",
    "fa": "IR",
    "ga": "IE",
    "gd": "GB",
    "gl": "ES",
    "gu": "IN",
    "hy": "AM",
    "is": "IS",
    "ka": "GE",
    "kk": "KZ",
    "km": "KH",
    "kn": "IN",
    "ky": "KG",
    "lo": "LA",
    "mk": "MK",
    "ml": "IN",
    "mn": "MN",
    "mr": "IN",
    "my": "MM",
    "ne": "NP",
    "nn": "NO",
    "or": "IN",
    "pa": "IN",
    "sa": "IN",
    "si": "LK",
    "sq": "AL",
    "sr": "RS",
    "sw": "KE",
    "te": "IN",
    "tg": "TJ",
    "tk": "TM",
    "ur": "PK",
    "uz": "UZ",
    "xh": "ZA",
    "zu": "ZA",
}
SCRIPT_TAGS = {
    "latin": "Latn",
    "cyrillic": "Cyrl",
    "arabic": "Arab",
    "devanagari": "Deva",
}


def norm_lang(tag: str | None) -> str | None:
    """Turn Adobe/Apple locale spellings into BCP-47 style ISO codes, or None."""
    if not tag:
        return None
    t = tag.strip().replace("_", "-").lower()
    if t.endswith(".lproj"):
        t = t.removesuffix(".lproj")
        t = APPLE_LPROJ.get(t, t).lower()
    t = LANG_ALIASES.get(t, t)
    if t in PSEUDO_LANGS:
        return None
    parts = t.split("-")
    lang = parts[0]
    if not (2 <= len(lang) <= 3 and lang.isalpha()):
        return None
    rest = parts[1:]
    script = None
    if rest and len(rest[0]) == 4 and rest[0].isalpha():
        script, rest = rest[0].title(), rest[1:]
    region = rest[0].upper() if rest else None
    if region == "XM":
        return None
    if region is not None and not (
        (len(region) == 2 and region.isalpha())
        or (len(region) == 3 and region.isdigit())
    ):
        region = None
    if lang == "zh" and script in ("Hans", "Hant"):
        legacy = "CN" if script == "Hans" else "TW"
        if region in (None, legacy):
            return f"zh-{legacy}"
    if region is not None and DEFAULT_REGION.get(lang) == region:
        region = None
    return "-".join(p for p in (lang, script, region) if p)


def clean_text(text: str) -> str:
    """Strip characters that XML 1.0 cannot carry."""
    return XML_BAD.sub("", text)


def stem_lang(stem: str) -> str | None:
    """``scribus.de`` -> de, ``app_pt_BR`` -> pt-BR, ``de`` -> de."""
    parts = stem.rsplit(".", 1)[-1].split("_")
    regional = (
        len(parts) >= 2
        and re.fullmatch(r"[a-z]{2,3}", parts[-2])
        and re.fullmatch(r"[A-Z]{2}|[A-Z][a-z]{3}|\d{3,4}", parts[-1])
    )
    return norm_lang("_".join(parts[-2:]) if regional else parts[-1])
