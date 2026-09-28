# this_file: src/vexy_localizzy/qa_icu.py
"""ICU checks through an explicitly installed, caller-pinned Node CLI."""

import json
import math
import subprocess
from collections.abc import Sequence

from vexy_localizzy.translation_types import (
    TranslationBatch,
    TranslationResult,
    check_result,
)


def check_pairs(
    pairs: Sequence[tuple[str, str, str]],
    *,
    command: Sequence[str],
    timeout: float = 15,
) -> list[list[str]]:
    """Check <=100 (source,target,locale) pairs; tooling failures are not bad translations."""
    if (
        isinstance(command, str)
        or not command
        or any(not isinstance(x, str) or not x for x in command)
    ):
        raise ValueError("Use a nonempty ICU command argument list")
    if not math.isfinite(timeout) or timeout <= 0 or len(pairs) > 100:
        raise ValueError("Use a positive ICU timeout and at most 100 pairs")
    if not pairs:
        return []
    rows = [
        {"source": source, "target": target, "locale": locale}
        for source, target, locale in pairs
    ]
    try:
        result = subprocess.run(
            list(command),
            input=json.dumps(rows),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError(
            "ICU checker failed; verify the installed command and locale"
        ) from error
    try:
        findings = json.loads(result.stdout)
    except ValueError as error:
        raise RuntimeError("ICU checker returned invalid JSON") from error
    if (
        not isinstance(findings, list)
        or len(findings) != len(pairs)
        or any(
            not isinstance(row, list) or any(not isinstance(item, str) for item in row)
            for row in findings
        )
    ):
        raise RuntimeError("ICU checker returned an invalid finding list")
    return findings


def validate_batch(
    batch: TranslationBatch,
    result: TranslationResult,
    *,
    command: Sequence[str],
    timeout: float = 15,
) -> None:
    """TranslationCache callback: structural failures trigger normal provider fallback."""
    check_result(result, batch, result.requested_model)
    findings = check_pairs(
        [
            (item.source, result.targets[item.id], batch.target_lang)
            for item in batch.items
        ],
        command=command,
        timeout=timeout,
    )
    errors = [
        f"{item.id}: {message}"
        for item, row in zip(batch.items, findings, strict=True)
        for message in row
    ]
    if errors:
        raise ValueError("; ".join(errors))
