# this_file: src/vexy_localizzy/qa_tokens.py
"""Literal-token compatibility checks for consumers of the legacy catalog model.

These preserve existing PH/TAG finding contracts. For syntax-aware Python/printf
validation, use qa.check_text with an explicit TextPolicy. ICU matching here is
the catalog's legacy token inventory, not a complete ICU message validator.
"""

from collections import Counter

from vexy_localizzy.catalog import PLACEHOLDER_PATTERNS, Finding, PlaceholderStyle
from vexy_localizzy.qa_placeholders import arguments

ARG_STYLES: tuple[PlaceholderStyle, ...] = (
    "qt",
    "printf",
    "python_brace",
    "i18next",
    "icu",
)


def check_tokens(
    source: str,
    target: str | None,
    *,
    styles: tuple[PlaceholderStyle, ...] = ARG_STYLES,
    unit_key: str | None = None,
) -> list[Finding]:
    """Compare token multiplicity, retaining legacy IDs, messages and data fields."""
    if set(styles) - PLACEHOLDER_PATTERNS.keys():
        raise ValueError("Unknown literal placeholder style")
    if target is None:
        return []
    findings = []
    for style in styles:
        left, right = (
            (arguments(source, style), arguments(target, style))
            if style == "qt"
            else (
                Counter(PLACEHOLDER_PATTERNS[style].findall(source)),
                Counter(PLACEHOLDER_PATTERNS[style].findall(target)),
            )
        )
        html = style == "html"
        noun, kind = ("HTML/XML tag", "TAG") if html else ("Placeholder", "PH")
        for change, values in (("MISS", left - right), ("EXTRA", right - left)):
            for token in sorted(values):
                message = (
                    f"{noun} {token!r} missing in target."
                    if change == "MISS"
                    else f"Unexpected {noun.lower()} {token!r} in target."
                )
                if html and change == "EXTRA":
                    message = f"Unexpected HTML/XML tag {token!r} in target."
                findings.append(
                    Finding(
                        rule_id=f"{kind}-{change}",
                        severity="critical",
                        message=message,
                        unit_key=unit_key,
                        data={"tag": token}
                        if html
                        else {"token": token, "style": style},
                    )
                )
    return findings
