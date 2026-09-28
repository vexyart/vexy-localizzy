# this_file: src/vexy_localizzy/review_api_data.py
"""Browser projections exclude retained document bytes and expose every native slot."""

from collections import Counter

from vexy_localizzy.qa.catalog import scalar_targets


def summary(catalog_id, snapshot):
    eligible = [
        unit
        for unit in snapshot.catalog.units
        if unit.state != "vanished" and unit.source.strip()
    ]
    states = Counter(unit.state for unit in eligible)
    return {
        "id": catalog_id,
        "source_lang": snapshot.catalog.source_lang,
        "target_lang": snapshot.catalog.target_lang,
        "total": len(eligible),
        "approved": states["approved"],
        "states": dict(states),
        "revision": snapshot.revision,
    }


def present(catalog_id, snapshot):
    return {
        **summary(catalog_id, snapshot),
        "units": [
            {
                **unit.model_dump(),
                "slots": {
                    form: target or "" for form, _, target in scalar_targets(unit)
                },
                "editable": unit.state != "vanished" and bool(unit.source.strip()),
            }
            for unit in snapshot.catalog.units
        ],
    }


def select_unit(snapshot, key):
    return next((unit for unit in snapshot.catalog.units if unit.key == key), None)
