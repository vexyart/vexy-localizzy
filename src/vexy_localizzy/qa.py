# this_file: src/vexy_localizzy/qa.py
"""Deterministic scalar translation checks shared by caches, catalogs and review."""

from typing import Annotated, Literal

from pydantic import Field

from vexy_localizzy.catalog import Finding
from vexy_localizzy.qa_markup import markup_pair, visible_text
from vexy_localizzy.qa_placeholders import accelerators, arguments
from vexy_localizzy.qa_printf import printf_error
from vexy_localizzy.translation_types import (
    TranslationBatch,
    TranslationRecord,
    TranslationResult,
    check_result,
)


class TextPolicy(TranslationRecord):
    """Select actual application syntax; brace checks must not inspect literal CSS."""

    placeholder_styles: tuple[Literal["qt", "python_brace", "printf"], ...] = ("qt",)
    markup: Literal["auto", "html", "none"] = "auto"
    accelerators: bool = True
    max_length: Annotated[int, Field(ge=0)] | None = None
    msgfmt: str = "msgfmt"


def check_text(
    source: str,
    target: str | None,
    *,
    policy: TextPolicy = TextPolicy(),
    unit_key: str | None = None,
) -> list[Finding]:
    """Report every applicable rule; unchanged prose is a review finding, not approval."""
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
    for style in policy.placeholder_styles:
        if style == "printf":
            if error := printf_error(source, target, executable=policy.msgfmt):
                add("PH-MISMATCH", error, style=style)
            continue
        try:
            left, right = arguments(source, style), arguments(target, style)
        except ValueError as error:
            add("PH-SYNTAX", str(error), style=style)
            continue
        if left != right:
            add(
                "PH-MISMATCH",
                f"{style} arguments or formatting differ.",
                style=style,
                missing=[str(v) for v in (left - right).elements()],
                extra=[str(v) for v in (right - left).elements()],
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


def validate_batch(
    batch: TranslationBatch,
    result: TranslationResult,
    *,
    policy: TextPolicy = TextPolicy(),
) -> None:
    """TranslationCache callback: reject structural errors on fresh and cached results."""
    check_result(result, batch, result.requested_model)
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
        )
        if finding.severity in ("major", "critical")
    ]
    if findings:
        raise ValueError(
            "; ".join(f"{f.unit_key}: {f.rule_id}: {f.message}" for f in findings)
        )
