# this_file: src/vexy_localizzy/qa/text.py
"""Deterministic scalar translation checks shared by caches, catalogs and review."""

import hashlib
import json
from typing import Annotated, Literal

from pydantic import Field, model_serializer

from vexy_localizzy.catalog import Finding
from vexy_localizzy.formats.qt_numerus import UnknownQtNumerus, single_number_forms
from vexy_localizzy.qa.markup import markup_pair, visible_text
from vexy_localizzy.qa.placeholders import accelerators, arguments
from vexy_localizzy.qa.printf import printf_error
from vexy_localizzy.translate.types import (
    TranslationBatch,
    TranslationRecord,
    TranslationResult,
    check_result,
)

PlaceholderStyle = Literal["qt", "python_brace", "printf", "i18next"]
# Qt's count placeholders: the tokens a one-count numerus form may leave out.
COUNT_TOKENS = ("%n", "%Ln")


class TextPolicy(TranslationRecord):
    """Select actual application syntax; brace checks must not inspect literal CSS.

    ``unit_styles`` overrides ``placeholder_styles`` per unit key (PO entries
    flagged ``c-format`` or ``python-brace-format``). The serialized form, used
    in cache validation identities, carries only a digest of that map, and
    nothing at all when it is empty.
    """

    placeholder_styles: tuple[PlaceholderStyle, ...] = ("qt",)
    markup: Literal["auto", "html", "none"] = "auto"
    accelerators: bool = True
    max_length: Annotated[int, Field(ge=0)] | None = None
    msgfmt: str = "msgfmt"
    unit_styles: dict[str, tuple[PlaceholderStyle, ...]] = Field(default_factory=dict)

    @model_serializer(mode="wrap")
    def _identity(self, handler):
        data = handler(self)
        styles = data.pop("unit_styles", None)
        if styles:
            blob = json.dumps(styles, sort_keys=True, ensure_ascii=False)
            data["unit_styles_sha256"] = hashlib.sha256(blob.encode()).hexdigest()
        return data

    def styles_for(self, unit_key: str | None) -> tuple[str, ...]:
        """Styles for one unit; batch item ids (``["key","form"]``) name their unit."""
        if unit_key is None or not self.unit_styles:
            return self.placeholder_styles
        if unit_key not in self.unit_styles and unit_key.startswith("["):
            try:
                unit_key = json.loads(unit_key)[0]
            except (ValueError, IndexError, KeyError, TypeError):
                pass
        return self.unit_styles.get(unit_key, self.placeholder_styles)


def check_text(
    source: str,
    target: str | None,
    *,
    policy: TextPolicy = TextPolicy(),
    unit_key: str | None = None,
    count_optional: bool = False,
) -> list[Finding]:
    """Report every applicable rule; unchanged prose is a review finding, not approval.

    ``count_optional`` is for a numerus form that exactly one count selects
    (Arabic zero, one and two; a singular chosen by n == 1): it may spell the
    number out and leave out ``%n`` or ``%Ln``. Every other argument is still
    required, and no argument may be added.
    """
    findings = []

    def add(rule, message, severity="critical", **data):
        findings.append(
            Finding(
                rule_id=rule,
                message=message,
                severity=severity,
                unit_key=unit_key,
                data=data,
            )
        )

    if (
        target is not None
        and policy.max_length is not None
        and len(target) > policy.max_length
    ):
        add(
            "LEN-OVER",
            f"Target exceeds the {policy.max_length}-character limit.",
            "major",
        )
    if target is None or not target.strip():
        add("TARGET-EMPTY", "Translation is missing or blank.")
        return findings
    if source == target:
        add(
            "TARGET-UNCHANGED",
            "Translation equals the source; review an invariant explicitly.",
            "minor",
        )
    for style in policy.styles_for(unit_key):
        if style == "printf":
            if error := printf_error(source, target, executable=policy.msgfmt):
                add("PH-MISMATCH", error, style=style)
            continue
        try:
            left, right = arguments(source, style), arguments(target, style)
        except ValueError as error:
            add("PH-SYNTAX", str(error), style=style)
            continue
        missing, extra = left - right, right - left
        if count_optional and style == "qt":
            for token in COUNT_TOKENS:
                del missing[token]
        if missing or extra:
            add(
                "PH-MISMATCH",
                f"{style} arguments or formatting differ.",
                style=style,
                missing=[str(v) for v in missing.elements()],
                extra=[str(v) for v in extra.elements()],
            )
    pair = markup_pair(source, target, policy.markup)
    if pair:
        left, right = pair
        if "".join(left.prose).strip() and not "".join(right.prose).strip():
            add("TARGET-EMPTY", "Translation removed all visible markup text.")
        if left.events != right.events:
            add("TAG-MISMATCH", "Markup structure or protected attributes differ.")
        if right.errors and (
            right.errors != left.errors or right.events != left.events
        ):
            add("TAG-SYNTAX", "Target markup is malformed.", errors=right.errors)
        if left.errors:
            add(
                "SOURCE-MARKUP",
                "Source markup is already malformed; review is required.",
                "minor",
                errors=left.errors,
            )
        source, target = visible_text(left), visible_text(right)
    if policy.accelerators and accelerators(source) != accelerators(target):
        add("ACCEL-MISMATCH", "Qt mnemonic count or invalid ampersand markers differ.")
    return findings


def numerus_form(item_id: str) -> int | None:
    """The numerus form index named by a batch item id (``["key","2"]`` or, for a
    length variant, ``["key","2:1"]``); None for a scalar or category-keyed item."""
    try:
        parts = json.loads(item_id)
    except ValueError:
        return None
    if not isinstance(parts, list) or len(parts) != 2 or not isinstance(parts[1], str):
        return None
    index = parts[1].split(":")[0]
    return int(index) if index.isascii() and index.isdigit() else None


def _one_count_forms(lang: str) -> frozenset[int]:
    try:
        return single_number_forms(lang)
    except UnknownQtNumerus:
        return frozenset()


def validate_batch(
    batch: TranslationBatch,
    result: TranslationResult,
    *,
    policy: TextPolicy = TextPolicy(),
) -> None:
    """TranslationCache callback: reject structural errors on fresh and cached results.

    An item that is a numerus form selected by exactly one count in the batch's
    target language may omit the count placeholder (see ``check_text``). The
    batch does not say how many forms its message has, so this trusts Qt's rule
    for the language; ``qa.catalog`` also compares the form count. The rule only
    accepts more than before, so cache validation identities stay as they were.
    """
    check_result(result, batch, result.requested_model)
    optional = _one_count_forms(batch.target_lang)
    findings = [
        finding
        for item in batch.items
        for finding in check_text(
            item.source,
            result.targets[item.id],
            policy=policy.model_copy(update={"max_length": item.max_length})
            if item.max_length is not None
            else policy,
            unit_key=item.id,
            count_optional=numerus_form(item.id) in optional,
        )
        if finding.severity in ("major", "critical")
    ]
    if findings:
        raise ValueError(
            "; ".join(f"{f.unit_key}: {f.rule_id}: {f.message}" for f in findings)
        )
