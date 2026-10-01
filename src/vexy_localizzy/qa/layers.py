# this_file: src/vexy_localizzy/qa/layers.py
"""Optional QA layers above the deterministic checks.

``qa.catalog`` is the gate every catalog passes: tokens, markup, length and
native plural shape, with no dependency. The layers here cost something and run
only when named: ``pofilter`` (Translate Toolkit's battery, needs the
``pofilter`` extra), ``qe`` (COMET quality estimation, needs ``unbabel-comet``)
and ``judge`` (an MQM score from a model behind an OpenAI-compatible endpoint,
on a sample). A missing dependency raises ``MissingDependencyError``; a layer
never silently skips. Referenced by ``localizzy qa --layers``.
"""

import importlib.util
import json
import random
import re
import subprocess
import tempfile
from pathlib import Path

from vexy_localizzy.catalog import Catalog, Finding, Unit
from vexy_localizzy.external import (
    MissingDependencyError,
    extra_installed,
    find_tool,
    install_command,
)
from vexy_localizzy.formats.qt_numerus import UnknownQtNumerus
from vexy_localizzy.formats.qt_numerus import count as numerus_count
from vexy_localizzy.plurals import (
    plural_forms_header,
    positional_categories,
    required_categories,
)

LAYERS = ("pofilter", "qe", "judge")
POFILTER_TESTS = (
    "variables",
    "xmltags",
    "escapes",
    "printf",
    "nplurals",
    "newlines",
    "accelerators",
)
POFILTER_TIMEOUT = 120  # seconds
QE_MODEL = "Unbabel/wmt22-cometkiwi-da"
QE_BATCH = 32
JUDGE_TIMEOUT = 60  # seconds per unit
CRITICAL_MQM = 50  # a score below this is critical, not major
_INACTIVE = ("untranslated", "vanished")
_POFILTER_TEST = re.compile(r"\(pofilter\)\s*([\w-]+):", re.IGNORECASE)

MQM_PROMPT = """\
You are a professional translation quality evaluator. Score the translation
using the MQM error taxonomy. For each error classify category (Accuracy:
mistranslation|omission|addition; Fluency: grammar|spelling|register|terminology)
and severity (minor=1pt, major=5pt, critical=25pt).
Final score = max(0, 100 - sum(penalties)).
Do NOT flag these brand terms as errors: __BRAND_TERMS__.
Output ONLY valid JSON: a "score" int 0-100 and an "errors" array of
{category, severity, span, explanation}.
"""


def native_plural_forms(catalog: Catalog) -> tuple[str, ...] | None:
    """The plural form keys the target language requires, in the catalog's convention.

    Indexed catalogs (Qt TS, gettext PO) get ``"0"…"n-1"`` from Qt's numerus
    count, or from the gettext table when Qt has no rule. Category-keyed
    catalogs get the CLDR categories. None when no active unit has native
    plural forms; mixed conventions raise ValueError.
    """
    plurals = [
        unit.plural
        for unit in catalog.units
        if unit.plural and unit.plural.icu is None and unit.state != "vanished"
    ]
    if not plurals:
        return None
    indexed = {plural.indexing == "index" for plural in plurals}
    if len(indexed) > 1:
        raise ValueError("Mixed plural conventions; pass the plural forms explicitly")
    if not indexed.pop():
        return tuple(sorted(required_categories(catalog.target_lang)))
    try:
        count = numerus_count(catalog.target_lang or "")
    except UnknownQtNumerus:
        count = len(positional_categories(catalog.target_lang))
    return tuple(str(index) for index in range(count))


def _write_po(catalog: Catalog, path: Path) -> None:
    """Project a catalog to PO for pofilter, stating the plural declaration."""
    from vexy_localizzy.conversion import convert_catalog

    categorical = any(
        unit.plural is not None
        and unit.plural.indexing == "cldr"
        and unit.plural.icu is None
        for unit in catalog.units
    )
    convert_catalog(
        catalog,
        "po",
        path,
        allow_loss=True,
        plural_forms=plural_forms_header(catalog.target_lang),
        plural_order=list(positional_categories(catalog.target_lang))
        if categorical
        else None,
    )


def parse_pofilter_errors(text: str, units: list[Unit]) -> list[Finding]:
    """Map a pofilter error PO back to ``POFILTER-*`` findings.

    The file is parsed as PO, so multi-line and non-ASCII sources keep their
    text. A failed test is a ``(pofilter) name: …`` translator comment; the
    entry is matched to its unit by context and source.
    """
    import polib

    by_identity = {(unit.context, unit.source): unit for unit in units}
    by_source = {unit.source: unit for unit in units}
    findings: list[Finding] = []
    for entry in polib.pofile(text):
        unit = by_identity.get((entry.msgctxt or "", entry.msgid)) or by_source.get(
            entry.msgid
        )
        for test in _POFILTER_TEST.findall(entry.tcomment or ""):
            findings.append(
                Finding(
                    rule_id=f"POFILTER-{test.upper()}",
                    severity="major",
                    message=f"pofilter '{test}' check failed.",
                    unit_key=unit.key if unit else None,
                    data={"test": test},
                )
            )
    return findings


def run_pofilter(catalog: Catalog) -> list[Finding]:
    """Translate Toolkit's ``pofilter`` battery over a PO projection of the catalog."""
    tool = find_tool("pofilter")
    if not extra_installed("pofilter") or tool.path is None:
        raise MissingDependencyError(
            "translate-toolkit (pofilter)", install_command("pofilter")
        )
    with tempfile.TemporaryDirectory(prefix="localizzy-pofilter-") as directory:
        po_in = Path(directory) / "in.po"
        po_errors = Path(directory) / "errors.po"
        _write_po(catalog, po_in)
        tests = [flag for test in POFILTER_TESTS for flag in ("-t", test)]
        try:
            result = subprocess.run(
                [tool.path, "--gnome", *tests, str(po_in), "-o", str(po_errors)],
                capture_output=True,
                text=True,
                timeout=POFILTER_TIMEOUT,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(
                f"pofilter timed out after {POFILTER_TIMEOUT} s"
            ) from error
        if result.returncode not in (0, 1):
            raise RuntimeError(f"pofilter failed: {result.stderr.strip()[:400]}")
        if not po_errors.exists():
            return []
        return parse_pofilter_errors(
            po_errors.read_text(encoding="utf-8"), list(catalog.units)
        )


def run_qe(catalog: Catalog, *, threshold: float = 0.7) -> list[Finding]:
    """Reference-free COMET quality estimation; a score below ``threshold`` is major."""
    if importlib.util.find_spec("comet") is None:
        raise MissingDependencyError("COMET-QE", "uv pip install unbabel-comet")
    from comet import download_model, load_from_checkpoint  # type: ignore

    scored = [u for u in catalog.units if u.target and u.state not in _INACTIVE]
    if not scored:
        return []
    model = load_from_checkpoint(download_model(QE_MODEL))
    rows = [{"src": unit.source, "mt": unit.target} for unit in scored]
    scores = model.predict(rows, batch_size=QE_BATCH, gpus=0).scores
    return [
        Finding(
            rule_id="QE-LOW-SCORE",
            severity="major",
            message=f"COMET-QE score {score:.3f} below threshold {threshold}.",
            unit_key=unit.key,
            data={"qe_score": float(score), "threshold": threshold},
        )
        for unit, score in zip(scored, scores, strict=True)
        if score < threshold
    ]


def judge_unit(
    unit: Unit,
    catalog: Catalog,
    *,
    model: str,
    system: str,
    endpoint: str,
    api_key: str,
) -> dict:
    """One MQM evaluation; returns the model's ``{"score", "errors"}`` object."""
    from vexy_localizzy.translate.openai_transport import chat_request

    payload = json.dumps(
        {
            "source_language": catalog.source_lang,
            "target_language": catalog.target_lang or "",
            "source": unit.source,
            "translation": unit.target or "",
            "context": unit.context,
            "key": unit.key,
        },
        ensure_ascii=False,
    )
    response = chat_request(
        model,
        system,
        payload,
        base_url=endpoint,
        api_key=api_key,
        timeout=JUDGE_TIMEOUT,
    )
    body = re.search(r"\{.*\}", response.content, re.DOTALL)
    if body is None:
        raise ValueError(f"Judge returned no JSON object for {unit.key}")
    try:
        data = json.loads(body.group())
        return {"score": int(data["score"]), "errors": list(data.get("errors", []))}
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Judge returned a malformed score for {unit.key}") from error


def run_judge(
    catalog: Catalog,
    *,
    model: str,
    endpoint: str,
    api_key: str,
    sample: float = 0.1,
    mqm_threshold: int = 80,
    brand_terms: list[str] | None = None,
    ignore_keys: list[str] | None = None,
    seed: int = 0,
) -> list[Finding]:
    """MQM scores from a model on a seeded sample; approved units are never judged."""
    if not extra_installed("llm"):
        raise MissingDependencyError("openai SDK for the judge", install_command("llm"))
    if not 0 < sample <= 1:
        raise ValueError("sample must be in (0, 1]")
    ignored = set(ignore_keys or [])
    eligible = [
        unit
        for unit in catalog.units
        if unit.target
        and unit.state not in (*_INACTIVE, "approved")
        and unit.key not in ignored
    ]
    if not eligible:
        return []
    size = min(len(eligible), max(1, int(len(eligible) * sample)))
    system = MQM_PROMPT.replace(
        "__BRAND_TERMS__", ", ".join(brand_terms or []) or "(none)"
    )
    findings: list[Finding] = []
    for unit in random.Random(seed).sample(eligible, size):
        result = judge_unit(
            unit,
            catalog,
            model=model,
            system=system,
            endpoint=endpoint,
            api_key=api_key,
        )
        if result["score"] < mqm_threshold:
            findings.append(
                Finding(
                    rule_id="MQM-LOW-SCORE",
                    severity="major" if result["score"] >= CRITICAL_MQM else "critical",
                    message=f"MQM score {result['score']}/100 (threshold {mqm_threshold}).",
                    unit_key=unit.key,
                    confidence="heuristic",
                    data={
                        "mqm_score": result["score"],
                        "judge_model": model,
                        "errors": result["errors"],
                    },
                )
            )
    return findings
