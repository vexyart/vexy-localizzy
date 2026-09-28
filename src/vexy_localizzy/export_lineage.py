# this_file: src/vexy_localizzy/export_lineage.py
"""Recover source identities from exported TMX without creating derived votes."""

import gzip
import json
from pathlib import Path

from vexy_localizzy.exporter import LINEAGE_PROP, MANIFEST_PROP
from vexy_localizzy.memory.tmx_read import Unit, UnitError
from vexy_localizzy.snapshots import adopt_snapshot
from vexy_localizzy.source_store import family_id, origin_id
from vexy_localizzy.xmlio import records


def read_manifest(path: Path) -> dict | None:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        for kind, element, namespace in records(stream):
            if kind == "tu":
                return None
            if kind != "header":
                continue
            props = [
                p.text
                for p in element.findall(namespace + "prop")
                if p.get("type") == MANIFEST_PROP
            ]
            if not props:
                return None
            if len(props) != 1:
                raise ValueError("Duplicate lineage manifest")
            data = json.loads(props[0])
            if (
                not isinstance(data, dict)
                or data.get("version") != 1
                or not isinstance(data.get("origins"), dict)
                or not isinstance(data.get("families"), dict)
            ):
                raise ValueError("Unsupported lineage manifest")
            return data
    return None


class ExportLineage:
    """Map exported registry IDs to this corpus after verifying raw source hashes."""

    def __init__(self, db, data: dict, snapshot_directory: Path) -> None:
        self.origins, self.families = {}, {}
        self.snapshots = {}
        checked = {}
        try:
            with db:
                for key, row in data["origins"].items():
                    pair = row["snapshot"], row["sha256"]
                    if pair not in checked:
                        checked[pair] = adopt_snapshot(
                            Path(row["snapshot"]), row["sha256"], snapshot_directory
                        )
                    self.origins[key] = origin_id(
                        db, row["path"], row["sha256"], str(checked[pair])
                    )
                    self.snapshots[self.origins[key]] = checked[pair]
                for key, row in data["families"].items():
                    if (
                        not isinstance(row["name"], str)
                        or not row["name"].strip()
                        or type(row["weight"]) is not int
                        or row["weight"] < 1
                    ):
                        raise ValueError("Invalid lineage family")
                    self.families[key] = family_id(db, row["name"], row["weight"])
        except (KeyError, TypeError) as error:
            raise ValueError("Invalid lineage registry") from error

    def references(self, unit: Unit) -> list[tuple[int, int, int]]:
        try:
            props = [value for name, value in unit.properties if name == LINEAGE_PROP]
            if len(props) != 1 or len(unit.segments) != 2:
                raise ValueError("Expected one lineage list and two variants")
            refs = json.loads(props[0])
            if not isinstance(refs, list) or not refs:
                raise ValueError("Empty lineage references")
            result = []
            for ref in refs:
                if (
                    not isinstance(ref, list)
                    or len(ref) != 3
                    or any(type(x) is not int or x < 1 for x in ref)
                ):
                    raise ValueError("Invalid lineage reference")
                origin, ordinal, family = ref
                result.append(
                    (self.origins[str(origin)], ordinal, self.families[str(family)])
                )
            return result
        except (ValueError, KeyError, TypeError) as error:
            raise UnitError(unit.ordinal, f"Invalid lineage: {error}") from error
