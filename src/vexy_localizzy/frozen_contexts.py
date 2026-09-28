# this_file: src/vexy_localizzy/frozen_contexts.py
"""Sealed prompt contexts transfer between embedding and translation runtimes."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import Field

from vexy_localizzy.catalog import Catalog
from vexy_localizzy.catalog_translation_batches import batches
from vexy_localizzy.catalog_translation_inputs import prepare_units
from vexy_localizzy.catalog_translation_types import PromptContext
from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.json_values import invalid_constant, unique_object
from vexy_localizzy.qa import TextPolicy
from vexy_localizzy.translation_store import digest, encoded
from vexy_localizzy.translation_types import TranslationRecord


def _items_digest(items):
    return digest([item.model_dump() for item in items])


def _batch_bytes_digest(batch):
    return hashlib.sha256(batch.model_dump_json().encode()).hexdigest()


class _Payload(TranslationRecord):
    format: Literal["localizzy-contexts-1"] = "localizzy-contexts-1"
    template_sha256: str
    items_sha256: str
    batch_size: int = Field(ge=1, le=100)
    max_batch_bytes: int = Field(gt=0)
    contexts: dict[str, PromptContext]
    batch_digests: list[str]
    batch_bytes_sha256: list[str]
    evidence: dict = Field(default_factory=dict)


class _Envelope(TranslationRecord):
    payload: _Payload
    checksum: str


class FrozenContexts:
    """Callable contexts with full preflight before any consumer provider request."""

    def __init__(self, envelope):
        parsed = _Envelope.model_validate(envelope)
        if digest(parsed.payload.model_dump()) != parsed.checksum:
            raise ValueError("Frozen context checksum differs")
        self._envelope = encoded(parsed.model_dump())
        self._payload = parsed.payload
        self._contexts = {
            key: value.model_dump_json()
            for key, value in parsed.payload.contexts.items()
        }

    @classmethod
    def load(cls, path):
        return cls(
            json.loads(
                Path(path).read_text(),
                object_pairs_hook=unique_object,
                parse_constant=invalid_constant,
            )
        )

    def write(self, path):
        atomic_write(Path(path), (self._envelope + "\n").encode())

    @property
    def identity(self):
        return json.loads(self._envelope)["checksum"]

    @property
    def evidence(self):
        return json.loads(self._envelope)["payload"]["evidence"]

    @property
    def batch_digests(self):
        return list(self._payload.batch_digests)

    def __call__(self, items):
        key = _items_digest(items)
        if key not in self._contexts:
            raise ValueError("Missing frozen context for these exact translation items")
        return PromptContext.model_validate_json(self._contexts[key])

    def validate_for(self, template, items, batch_size, max_batch_bytes):
        expected = (
            self._payload.template_sha256,
            self._payload.items_sha256,
            self._payload.batch_size,
            self._payload.max_batch_bytes,
        )
        actual = (
            digest(template.model_dump()),
            _items_digest(items),
            batch_size,
            max_batch_bytes,
        )
        if actual != expected:
            raise ValueError(
                "Frozen context catalog, item or batching identity differs"
            )
        observed, byte_digests = [], []
        for batch in batches(items, template, self, batch_size, max_batch_bytes):
            observed.append(digest(batch.model_dump()))
            byte_digests.append(_batch_bytes_digest(batch))
        if (
            observed != self._payload.batch_digests
            or byte_digests != self._payload.batch_bytes_sha256
        ):
            raise ValueError("Frozen context batch coverage or content differs")


def prepare_contexts(
    template,
    context,
    *,
    plural_forms=None,
    reviewed=None,
    invariants=None,
    policy=TextPolicy(),
    batch_size=50,
    max_batch_bytes=48000,
    evidence=None,
):
    """Run retrieval once, including recursive splits, without calling a translator.

    Evidence may be a zero-argument callback, evaluated after retrieval so it can
    capture all used provenance records. Save the returned sealed artifact only
    after complete preparation; interrupted/invalid preparation produces no file.
    """
    if type(batch_size) is not int or not 1 <= batch_size <= 100:
        raise ValueError("batch_size must be an integer from one through 100")
    if type(max_batch_bytes) is not int or max_batch_bytes < 1:
        raise ValueError("max_batch_bytes must be a positive integer")
    template = Catalog.model_validate_json(template.model_dump_json())
    if not template.target_lang or template.target_lang == template.source_lang:
        raise ValueError("Translation requires a distinct target locale")
    items = prepare_units(
        template, reviewed, invariants or {}, plural_forms or {}, policy
    )[2]
    records = {}

    def record(values):
        key = _items_digest(values)
        result = context(values)
        if not isinstance(result, PromptContext):
            raise ValueError("Context retrieval must return PromptContext")
        result = PromptContext.model_validate_json(encoded(result.model_dump()))
        data = result.model_dump()
        if key in records and records[key] != data:
            raise ValueError("Context retrieval changed for identical items")
        records[key] = data
        return result

    batch_digests, byte_digests = [], []
    for batch in batches(items, template, record, batch_size, max_batch_bytes):
        batch_digests.append(digest(batch.model_dump()))
        byte_digests.append(_batch_bytes_digest(batch))
    payload = _Payload(
        template_sha256=digest(template.model_dump()),
        items_sha256=_items_digest(items),
        batch_size=batch_size,
        max_batch_bytes=max_batch_bytes,
        contexts=records,
        batch_digests=batch_digests,
        batch_bytes_sha256=byte_digests,
        evidence=(evidence() if callable(evidence) else evidence) or {},
    )
    result = FrozenContexts(
        {"payload": payload.model_dump(), "checksum": digest(payload.model_dump())}
    )
    result.validate_for(template, items, batch_size, max_batch_bytes)
    return result
