# this_file: src/vexy_localizzy/classification_run_inputs.py
"""Frozen input validation and deterministic batch boundaries for the producer."""

import hashlib
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

from vexy_localizzy.classification import Entry, batches, request_text
from vexy_localizzy.classification_evidence import InputEntry, InputMetadata
from vexy_localizzy.json_sequence import values


def input_identity(inputs: Path) -> tuple[InputMetadata, str]:
    with inputs.open("rb") as stream:
        metadata = InputMetadata.model_validate_json(stream.readline())
        stream.seek(0)
        return metadata, hashlib.file_digest(stream, "sha256").hexdigest()


def input_batches(
    inputs: Path,
    metadata: InputMetadata,
    digest: str,
    *,
    batch_bytes: int,
    max_request_bytes: int,
    prompt: str,
) -> Iterator[list[Entry]]:
    """Recheck input bytes, exact IDs and coverage on every complete traversal."""
    count, previous = 0, 0
    coverage: Counter[str] = Counter()
    with inputs.open() as stream:
        records = values(stream)
        header = next(records, None)
        if header is None:
            raise ValueError("Classification input is empty")
        if InputMetadata.model_validate(header) != metadata:
            raise ValueError("Classification input metadata differs")

        def entries() -> Iterator[Entry]:
            nonlocal count, previous
            for record in records:
                row = InputEntry.model_validate(record)
                if (
                    row.id <= previous
                    or not row.locales
                    or row.locales != sorted(set(row.locales))
                ):
                    raise ValueError(
                        "Input IDs must increase and locales must be nonempty, unique and sorted"
                    )
                count += 1
                previous = row.id
                coverage.update(row.locales)
                yield Entry(row.id, row.text, tuple(row.locales))

        for batch in batches(
            entries(), max_bytes=batch_bytes, max_entry_bytes=max_request_bytes
        ):
            if (
                len(prompt.encode())
                + len(request_text(batch, metadata.coverage).encode())
                > max_request_bytes
            ):
                raise ValueError("Classification request exceeds byte budget")
            yield batch
    if (
        input_identity(inputs)[1] != digest
        or count != metadata.entries
        or dict(coverage) != metadata.coverage
    ):
        raise ValueError("Frozen classification input hash, count or coverage differs")
