# this_file: src/vexy_localizzy/catalog_translation_inputs.py
"""Deterministic scalar addressing and reviewed-output checks for catalog translation."""

import json

from vexy_localizzy.catalog import Catalog, Unit, compute_source_hash
from vexy_localizzy.catalog_translation_types import Disposition
from vexy_localizzy.qa_catalog import check_catalog, scalar_targets, shape_findings
from vexy_localizzy.translation_types import TranslationItem


def item_id(unit: Unit, form: str) -> str:
    return json.dumps([unit.key, form], ensure_ascii=False, separators=(",", ":"))


def fill_unit(unit: Unit, values: dict[str, str], state: str = "needs_review") -> Unit:
    """Reassemble every native slot; partial responses leave explicit empty targets."""
    updates = {"state": state}
    if unit.plural is not None and unit.plural.icu is None:
        forms, variants = {}, {}
        for key in unit.plural.forms:
            if key in unit.plural.variants:
                variants[key] = [
                    values.get(f"{key}:{i}", "")
                    for i in range(len(unit.plural.variants[key]))
                ]
                forms[key] = variants[key][0]
            else:
                forms[key] = values.get(key, "")
        updates["plural"] = unit.plural.model_copy(
            update={"forms": forms, "variants": variants}
        )
    elif unit.variants is not None:
        updates["variants"] = [
            values.get(f"variant:{i}", "") for i in range(len(unit.variants))
        ]
        if unit.target is not None:
            updates["target"] = updates["variants"][0]
    else:
        updates["target"] = values.get("scalar", "")
    return unit.model_copy(update=updates)


def items_for(unit: Unit, plural_forms: dict[str, str]) -> list[TranslationItem]:
    rows = []
    for form, source, _ in scalar_targets(unit):
        description = plural_forms.get(form.split(":")[0], "") if unit.plural else ""
        rows.append(
            TranslationItem(
                id=item_id(unit, form),
                source=source,
                context=unit.context,
                comment=unit.disambiguation or "",
                notes=unit.notes,
                form=f"{form}: {description}" if description else form,
                max_length=unit.max_length,
            )
        )
    return rows


def prepare_units(
    template: Catalog, reviewed, invariants, plural_forms, policy, *, prefilled=None
):
    """Preflight all native shapes and explicit approvals before any model calls.

    ``prefilled`` maps unit keys to ``Prefill`` values (memory hits, kept targets).
    Such units may already carry targets; their filled form must pass shape and
    major/critical QA checks, or this raises before any provider call.
    """
    if len({u.key for u in template.units}) != len(template.units):
        raise ValueError("Catalog message keys must be distinct")
    prefilled = dict(prefilled or {})
    if set(prefilled) - {u.key for u in template.units}:
        raise ValueError("Unknown prefilled message keys")
    if reviewed is not None and (
        reviewed.target_lang != template.target_lang
        or reviewed.source_lang != template.source_lang
    ):
        raise ValueError("Reviewed catalog locales must match the template")
    previous = {u.key: u for u in reviewed.units} if reviewed else {}
    if reviewed and len(previous) != len(reviewed.units):
        raise ValueError("Reviewed message keys must be distinct")
    if set(invariants) - {u.key for u in template.units}:
        raise ValueError("Unknown invariant approval keys")
    fixed, dispositions, items = {}, {}, []
    for index, unit in enumerate(template.units):
        status, reason = None, ""
        prefill = prefilled.get(unit.key)
        if prefill is not None and (
            unit.state == "vanished" or not unit.source.strip()
        ):
            raise ValueError(f"Excluded message cannot be prefilled: {unit.key}")
        if unit.state == "vanished":
            status = "excluded_vanished"
        elif not unit.source.strip():
            status = "excluded_empty"
        else:
            if errors := shape_findings(
                unit, tuple(plural_forms) if plural_forms else None
            ):
                raise ValueError(
                    f"Invalid plural/variant template {unit.key}: {errors}"
                )
            if prefill is None and any(
                value and value.strip() for _, _, value in scalar_targets(unit)
            ):
                raise ValueError(
                    "Translation template must have empty eligible targets"
                )
            if unit.plural is not None and unit.plural.icu is not None:
                raise ValueError(
                    "ICU catalog translation needs an explicit format policy"
                )
            if prefill is not None:
                if unit.key in invariants:
                    raise ValueError(
                        f"Message is both prefilled and invariant: {unit.key}"
                    )
                values = dict(prefill.values)
                if set(values) != {form for form, _, _ in scalar_targets(unit)}:
                    raise ValueError(f"Prefilled target shape differs for {unit.key}")
                fixed[index] = fill_unit(unit, values, prefill.state)
                status, reason = prefill.status, prefill.reason
            elif approval := invariants.get(unit.key):
                if approval.source_hash != compute_source_hash(unit):
                    raise ValueError(f"Stale invariant approval for {unit.key}")
                fixed[index] = fill_unit(
                    unit,
                    {form: source for form, source, _ in scalar_targets(unit)},
                    "approved",
                )
                status, reason = "invariant", approval.reason
            elif (
                (old := previous.get(unit.key)) is not None
                and old.state == "approved"
                and compute_source_hash(old) == compute_source_hash(unit)
            ):
                if shape_findings(old, tuple(plural_forms) or None):
                    raise ValueError(f"Reviewed target shape is invalid for {unit.key}")
                values = {form: target for form, _, target in scalar_targets(old)}
                if set(values) != {form for form, _, _ in scalar_targets(unit)}:
                    raise ValueError(f"Reviewed target shape differs for {unit.key}")
                fixed[index] = fill_unit(unit, values, "approved")
                status = "reviewed"
            if index in fixed:
                errors = check_catalog(
                    template.model_copy(update={"units": [fixed[index]]}),
                    policy=policy,
                    required_plural_forms=tuple(plural_forms) or None,
                )
                if any(
                    f.severity in ("major", "critical")
                    or (f.rule_id == "TARGET-UNCHANGED" and status == "reviewed")
                    for f in errors
                ):
                    if status in ("memory", "kept"):
                        raise ValueError(
                            f"Prefilled output fails shape or QA checks: {unit.key}"
                        )
                    raise ValueError(
                        f"Reviewed output needs correction or explicit invariant approval: {unit.key}"
                    )
        if status:
            fixed.setdefault(index, unit)
            dispositions[index] = Disposition(
                key=unit.key, status=status, reason=reason
            )
        else:
            items.extend(items_for(unit, plural_forms))
    return fixed, dispositions, items
