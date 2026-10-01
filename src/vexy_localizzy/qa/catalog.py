# this_file: src/vexy_localizzy/qa/catalog.py
"""Check every active scalar/native form without trusting translation-state labels."""

from vexy_localizzy.catalog import Catalog, Finding, Unit
from vexy_localizzy.formats import qt_numerus
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


def count_optional_forms(unit: Unit, lang: str | None) -> frozenset[str]:
    """Keys of the numerus forms of ``unit`` that exactly one count selects in ``lang``.

    Such a form may spell its number out and omit ``%n`` (Arabic zero, one and
    two; the singular of a language whose rule is n == 1). Empty for a scalar
    message, category-keyed plurals, a language without a Qt rule, and a message
    whose forms are not the ones Qt counts for the language.
    """
    plural = unit.plural
    if plural is None or plural.icu is not None or plural.indexing != "index":
        return frozenset()
    try:
        single = qt_numerus.single_number_forms(lang or "")
        count = qt_numerus.count(lang or "")
    except qt_numerus.UnknownQtNumerus:
        return frozenset()
    if set(plural.forms) != {str(index) for index in range(count)}:
        return frozenset()
    return frozenset(str(index) for index in single)


def form_findings(
    unit: Unit,
    policy: TextPolicy,
    lang: str | None,
    values: dict[str, str] | None = None,
) -> list[Finding]:
    """``check_text`` for every native form of ``unit``; each finding names its form.

    ``values`` replaces the unit's own targets (form key to text), for a
    candidate that is not written yet. The unit's ``max_length`` applies, and a
    one-count numerus form may omit the count placeholder. Referenced by
    ``check_catalog`` and ``translate.run``.
    """
    if unit.max_length is not None:
        policy = policy.model_copy(update={"max_length": unit.max_length})
    optional = count_optional_forms(unit, lang)
    findings = []
    for form, source, target in scalar_targets(unit):
        found = check_text(
            source,
            target if values is None else values.get(form),
            policy=policy,
            unit_key=unit.key,
            count_optional=form.split(":")[0] in optional,
        )
        findings.extend(
            f.model_copy(update={"data": {**f.data, "form": form}}) for f in found
        )
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
        findings.extend(form_findings(unit, policy, catalog.target_lang))
    return findings
