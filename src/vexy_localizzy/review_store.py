# this_file: src/vexy_localizzy/review_store.py
"""Filesystem review store: canonical JSON, per-catalog lock and durable edit journal."""

import hashlib
from pathlib import Path
from uuid import uuid4

from filelock import FileLock

from vexy_localizzy.catalog import Catalog
from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.qa.catalog import check_catalog, scalar_targets, shape_findings
from vexy_localizzy.qa.text import TextPolicy
from vexy_localizzy.review_journal import append, reconcile, sync_directory
from vexy_localizzy.review_types import (
    Completion,
    Intent,
    ReviewConflict,
    ReviewEdit,
    ReviewSnapshot,
)
from vexy_localizzy.translate.inputs import fill_unit


def _revision(raw):
    return hashlib.sha256(raw).hexdigest()


class ReviewStore:
    """Serve explicitly configured canonical catalogs beneath one root.

    Canonical JSON retains native source documents and approval states; native
    files can be exported with the existing format writers. No corpus DB needed.
    """

    def __init__(self, root, catalogs, *, policies=None, plural_forms=None):
        self.root = Path(root).resolve(strict=True)
        self.paths = {
            key: self._contained(self.root / path) for key, path in catalogs.items()
        }
        if len(set(self.paths.values())) != len(self.paths):
            raise ValueError("Catalog IDs must refer to distinct files")
        self.policies = dict(policies or {})
        self.plural_forms = {
            key: tuple(forms) for key, forms in (plural_forms or {}).items()
        }
        if (set(self.policies) | set(self.plural_forms)) - set(self.paths):
            raise ValueError("Review policy names an unknown catalog")
        self._namespace()

    def _contained(self, path):
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root) or resolved == self.root:
            raise ValueError("Review paths must remain inside the configured root")
        return resolved

    def _namespace(self):
        files, paths, inodes = {}, set(), set()
        for key, configured in self.paths.items():
            path = self._contained(configured)
            triple = tuple(
                self._contained(candidate)
                for candidate in (
                    path,
                    path.with_name(path.name + ".review.jsonl"),
                    path.with_name(path.name + ".review.lock"),
                )
            )
            for candidate in triple:
                if candidate in paths:
                    raise ValueError("Review catalog and sidecar paths collide")
                paths.add(candidate)
                if candidate.exists():
                    info = candidate.stat()
                    inode = (info.st_dev, info.st_ino)
                    if inode in inodes:
                        raise ValueError("Review files must not alias the same inode")
                    inodes.add(inode)
            files[key] = triple
        return files

    def _files(self, catalog_id):
        path, journal, lock = self._namespace()[catalog_id]
        return path, journal, FileLock(lock, timeout=10)

    def _read(self, path, journal):
        raw = path.read_bytes()
        revision = _revision(raw)
        reconcile(journal, revision)
        catalog = Catalog.model_validate_json(raw)
        if len({unit.key for unit in catalog.units}) != len(catalog.units):
            raise ValueError("Review catalog contains duplicate message keys")
        return ReviewSnapshot(revision=revision, catalog=catalog)

    def open(self, catalog_id):
        path, journal, lock = self._files(catalog_id)
        with lock:
            return self._read(path, journal)

    def _edited(self, catalog_id, catalog, edit):
        indices = {unit.key: i for i, unit in enumerate(catalog.units)}
        if edit.key not in indices:
            raise KeyError(edit.key)
        index = indices[edit.key]
        unit = catalog.units[index]
        if unit.state == "vanished" or not unit.source.strip():
            raise ValueError("Excluded messages cannot be edited")
        if unit.plural is not None and unit.plural.icu is not None:
            raise ValueError("ICU review needs an explicit format policy")
        if shape_findings(unit, self.plural_forms.get(catalog_id)):
            raise ValueError(
                "Existing native target shape needs correction before review"
            )
        if set(edit.targets) != {form for form, _, _ in scalar_targets(unit)}:
            raise ValueError("Edit must supply every native target slot exactly once")
        updated = fill_unit(
            unit,
            edit.targets,
            "approved" if edit.action == "approve" else "needs_review",
        )
        findings = check_catalog(
            catalog.model_copy(update={"units": [updated]}),
            policy=self.policies.get(catalog_id, TextPolicy()),
            required_plural_forms=self.plural_forms.get(catalog_id),
        )
        errors = [
            finding
            for finding in findings
            if finding.severity in ("major", "critical")
            or (
                edit.action == "approve"
                and finding.rule_id == "TARGET-UNCHANGED"
                and not edit.reason.strip()
            )
        ]
        if errors:
            raise ValueError(
                "Review edit failed QA: " + "; ".join(f.rule_id for f in errors)
            )
        units = list(catalog.units)
        units[index] = updated
        return catalog.model_copy(update={"units": units})

    def save(self, catalog_id, edit: ReviewEdit):
        edit = ReviewEdit.model_validate_json(edit.model_dump_json())
        path, journal, lock = self._files(catalog_id)
        with lock:
            previous = self._read(path, journal)
            if edit.revision != previous.revision:
                raise ReviewConflict("Catalog changed; reopen before saving")
            catalog = self._edited(catalog_id, previous.catalog, edit)
            raw = catalog.model_dump_json(indent=2).encode() + b"\n"
            revision = _revision(raw)
            if revision == previous.revision:
                return previous
            intent = Intent(
                id=uuid4().hex, old=previous.revision, new=revision, edit=edit
            )
            append(journal, intent)
            atomic_write(path, raw)
            sync_directory(path.parent)
            append(journal, Completion(id=intent.id, status="applied"))
            return ReviewSnapshot(revision=revision, catalog=catalog)

    def preview(self, catalog_id, edit: ReviewEdit):
        """Check an edit against its current revision without saving the candidate."""
        edit = ReviewEdit.model_validate_json(edit.model_dump_json())
        path, journal, lock = self._files(catalog_id)
        with lock:
            previous = self._read(path, journal)
            if edit.revision != previous.revision:
                raise ReviewConflict("Catalog changed; reopen before validating")
            catalog = self._edited(catalog_id, previous.catalog, edit)
            return ReviewSnapshot(revision=previous.revision, catalog=catalog)
