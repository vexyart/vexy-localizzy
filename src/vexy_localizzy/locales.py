# this_file: src/vexy_localizzy/locales.py
"""Canonical indexes for documented legacy locale labels; retain raw tags separately."""

from langcodes import standardize_tag

# IANA: https://www.iana.org/assignments/lang-subtags-templates/ijekavsk.txt
# CLDR: https://www.unicode.org/cldr/charts/48/summary/mni_Mtei.html
LEGACY_ALIASES = {
    "sr-ijekavian": "sr-ijekavsk",
    "sr-ijekavianlatin": "sr-Latn-ijekavsk",
    "mni-meiteimayek": "mni-Mtei",
}


def canonical_locale(raw: str) -> str:
    return standardize_tag(LEGACY_ALIASES.get(raw.lower().replace("_", "-"), raw))
