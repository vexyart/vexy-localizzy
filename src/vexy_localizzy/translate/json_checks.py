# this_file: src/vexy_localizzy/translate/json_checks.py
"""Text QA for translated Markdown items of a flat JSON file.

Each item passes ``check_text`` (HTML markup and Qt placeholders; accelerators
are off because help text uses ``&`` as prose) plus two Markdown checks that
``check_text`` cannot see: link targets must match, and inline code spans must
keep their count. Findings are returned as JSON dicts for the provenance
sidecar; a batch with any blocking finding is rejected by ``json_file``.
"""

import re

from vexy_localizzy.qa.text import TextPolicy, check_text

POLICY = TextPolicy(placeholder_styles=("qt",), markup="html", accelerators=False)
BLOCKING = frozenset({"major", "critical"})
LINK = re.compile(r"\]\(([^)\s]+)")
CODE = re.compile(r"`[^`\n]+`")


def _finding(rule: str, key: str, message: str) -> dict:
    return {"rule_id": rule, "severity": "major", "unit_key": key, "message": message}


def check(source: str, target: str, key: str) -> list[dict]:
    """``check_text`` findings plus Markdown link and code-span findings."""
    findings = [
        f.model_dump(mode="json")
        for f in check_text(source, target, policy=POLICY, unit_key=key)
    ]
    if sorted(LINK.findall(source)) != sorted(LINK.findall(target)):
        findings.append(_finding("MD-LINK", key, "Markdown link targets differ."))
    if len(CODE.findall(source)) != len(CODE.findall(target)):
        findings.append(
            _finding("MD-CODE", key, "Markdown code spans differ in number.")
        )
    return findings


def check_item(row: dict, item: dict) -> list[dict]:
    """Findings for one translated item: its text and, when given, its title."""
    findings = check(row["text"], item["text"], row["id"])
    if "title" in row:
        findings += check(row["title"], item.get("title") or "", row["id"])
    return findings


def blocking(findings: list[dict]) -> list[str]:
    """``key: rule`` labels of the findings that reject a batch, sorted."""
    return sorted(
        {
            f"{f['unit_key']}: {f['rule_id']}"
            for f in findings
            if f["severity"] in BLOCKING
        }
    )
