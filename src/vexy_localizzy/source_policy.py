# this_file: src/vexy_localizzy/source_policy.py
"""Explicit source-family policies, independent of any particular product."""

import json
from dataclasses import asdict, dataclass, field

from vexy_localizzy.tmx import Unit, UnitError


@dataclass(frozen=True)
class SourcePolicy:
    family: str
    weight: int
    family_property: str | None = None
    family_map: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.family.strip() or type(self.weight) is not int or self.weight < 1:
            raise ValueError(
                "A nonempty family and positive integer weight are required"
            )
        if self.family_map and not self.family_property:
            raise ValueError("family_map requires family_property")
        if any(
            not isinstance(k, str) or not isinstance(v, str) or not v.strip()
            for k, v in self.family_map.items()
        ):
            raise ValueError(
                "Family mappings require string keys and nonempty family names"
            )

    @property
    def identity(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    def family_for(self, unit: Unit) -> str:
        if not self.family_property:
            return self.family
        values = {
            v for k, v in unit.properties if k == self.family_property and v.strip()
        }
        if not values:
            return self.family
        if len(values) > 1:
            raise UnitError(unit.ordinal, "Ambiguous source family property")
        value = values.pop()
        if self.family_map:
            if value not in self.family_map:
                raise UnitError(
                    unit.ordinal, f"Unmapped source family property: {value}"
                )
            return self.family_map[value]
        return f"{self.family}:{value}"
