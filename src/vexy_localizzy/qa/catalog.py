# this_file: src/vexy_localizzy/qa/catalog.py
"""Check every active scalar/native form without trusting translation-state labels."""

from vexy_localizzy.catalog import Catalog, Finding, Unit
from vexy_localizzy.qa.text import TextPolicy, check_text


def scalar_targets(unit: Unit):
    """Yield form, source and target; gettext plural source remains distinct."""
    if unit.plural is not None and unit.plural.icu is None:
        for key, text in unit.plural.forms.items():
            source = (
                unit.source
                if key in ("0", "one")
                else unit.source_plural or unit.source
            )
            variants = unit.plural.variants.get(key)
            if variants:
                yield from (
                    (f"{key}:{i}", source, value) for i, value in enumerate(variants)
                )
            else:
                yield key, source, text
    elif unit.variants:
        yield from (
            (f"variant:{i}", unit.source, value)
            for i, value in enumerate(unit.variants)
        )
    else:
        yield "scalar", unit.source, unit.target


def shape_findings(unit: Unit, required: tuple[str, ...] | None) -> list[Finding]:
    """Plural positions are caller-supplied native rules, never guessed CLDR categories."""
    findings = []

    def add(rule, message):
        findings.append(
            Finding(
                rule_id=rule, message=message, severity="critical", unit_key=unit.key
            )
        )

    if unit.plural is not None and unit.plural.icu is None:
        forms, variants = unit.plural.forms, unit.plural.variants
        if required is None:
            add("PLURAL-RULE", "Required native plural forms must be configured.")
        else:
            if missing := set(required) - set(forms):
                add("PLURAL-MISS", f"Missing native plural forms: {sorted(missing)}")
            if extra := set(forms) - set(required):
                add("PLURAL-EXTRA", f"Unexpected native plural forms: {sorted(extra)}")
        for key, values in variants.items():
            if key not in forms or not values or forms[key] != values[0]:
                add(
                    "VARIANT-SHAPE",
                    f"Plural length variants disagree with form {key!r}.",
                )
    if unit.variants is not None and (
        not unit.variants
        or (unit.target is not None and unit.target != unit.variants[0])
    ):
        add("VARIANT-SHAPE", "Length variants disagree with the scalar target.")
    return findings


def check_catalog(
    catalog: Catalog,
    *,
    policy=TextPolicy(),
    required_plural_forms: tuple[str, ...] | None = None,
) -> list[Finding]:
    """Check all active nonblank sources, including missing/unfinished translations."""
    if required_plural_forms is not None and (
        not required_plural_forms
        or len(set(required_plural_forms)) != len(required_plural_forms)
        or any(not isinstance(key, str) or not key for key in required_plural_forms)
    ):
        raise ValueError("Required plural forms must be nonempty distinct keys")
    findings = []
    for unit in catalog.units:
        if unit.state == "vanished" or not unit.source.strip():
            continue
        findings.extend(shape_findings(unit, required_plural_forms))
        current = (
            policy.model_copy(update={"max_length": unit.max_length})
            if unit.max_length is not None
            else policy
        )
        for form, source, target in scalar_targets(unit):
            findings.extend(
                f.model_copy(update={"data": {**f.data, "form": form}})
                for f in check_text(source, target, policy=current, unit_key=unit.key)
            )
    return findings
