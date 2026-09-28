# this_file: src/vexy_localizzy/translate/batches.py
"""Bound enriched requests without truncating message or reference data."""

from collections import deque

from vexy_localizzy.translate.catalog_types import PromptContext
from vexy_localizzy.translate.types import TranslationBatch, TranslationItem


def batches(items, template, context, batch_size, max_batch_bytes):
    """Split oversized groups deterministically; a single oversized item fails explicitly."""
    for start in range(0, len(items), batch_size):
        pending = deque([items[start : start + batch_size]])
        while pending:
            chunk = pending.popleft()
            safe = [
                TranslationItem.model_validate_json(i.model_dump_json()) for i in chunk
            ]
            extra = context(safe) if context else PromptContext()
            if safe != chunk:
                raise ValueError("Context retrieval must not change translation items")
            if not isinstance(extra, PromptContext):
                raise ValueError("Context retrieval must return PromptContext")
            batch = TranslationBatch(
                source_lang=template.source_lang,
                target_lang=template.target_lang,
                items=chunk,
                **extra.model_dump(),
            )
            if len(batch.model_dump_json().encode()) <= max_batch_bytes:
                yield batch
            elif len(chunk) == 1:
                raise ValueError(
                    f"Single enriched translation item exceeds byte budget: {chunk[0].id}"
                )
            else:
                middle = len(chunk) // 2
                pending.appendleft(chunk[middle:])
                pending.appendleft(chunk[:middle])
