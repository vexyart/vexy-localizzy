# this_file: tests/test_translation_content_qa.py
"""Real content validation participates in durable fallback decisions."""

from vexy_localizzy.qa.text import validate_batch
from vexy_localizzy.translate.types import (
    TranslationBatch,
    TranslationItem,
    TranslationResult,
)


def test_cache_when_content_invalid_then_validated_fallback_survives_reopen(tmp_path):
    from collections import Counter

    from vexy_localizzy.translate.cache import TranslationCache

    calls = Counter()
    batch = TranslationBatch(
        source_lang="en",
        target_lang="pl",
        items=[TranslationItem(id="m", source="%L1 files")],
    )

    def request(model, batch):
        calls[model] += 1
        return TranslationResult(
            targets={"m": "%1 plików" if model == "bad" else "%L1 plików"},
            requested_model=model,
            reported_model=model,
        )

    options = dict(
        models=("bad", "good"),
        request=request,
        endpoint_identity="synthetic",
        engine_identity="synthetic:1",
        validation_identity="qt-qa:1",
        validate=validate_batch,
    )
    for _ in range(2):
        with TranslationCache(tmp_path / "cache.sqlite", **options) as cache:
            result = cache.translate(batch)
            assert result.reported_model == "good"
    assert calls == {"bad": 3, "good": 1}, (
        "QA must reject malformed output before caching, then reuse the validated fallback"
    )
