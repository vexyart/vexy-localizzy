# this_file: src/vexy_localizzy/translate/engine.py
"""Wire an OpenAI-compatible endpoint through abersetz into the validated batch cache."""

import os
from collections.abc import Callable
from functools import partial
from pathlib import Path

from pydantic import Field

from vexy_localizzy.catalog import Record
from vexy_localizzy.qa import validate_batch
from vexy_localizzy.translation_cache import TranslationCache
from vexy_localizzy.translation_types import TranslationBatch, TranslationResult

Request = Callable[[str, TranslationBatch], TranslationResult]


class EngineSpec(Record):
    """Endpoint and ordered model routes: preferred first, then fallbacks."""

    endpoint: str = Field(min_length=1)
    models: tuple[str, ...] = Field(min_length=1)
    api_key_env: str = "OPENAI_API_KEY"
    temperature: float = Field(default=0.2, ge=0, le=2)
    timeout: float = Field(default=60, gt=0)


def engine_identity(spec: EngineSpec) -> str:
    """Transport version plus every generation setting that changes output."""
    from vexy_localizzy.abersetz_transport import TRANSPORT_ID

    return f"{TRANSPORT_ID};temperature={spec.temperature!r}"


def abersetz_request(spec: EngineSpec) -> Request:
    """Single-attempt abersetz call per model; the cache owns retry and fallback."""
    from vexy_localizzy.abersetz_transport import translate_batch

    api_key = os.environ.get(spec.api_key_env, "")
    if not api_key.strip():
        raise ValueError(f"Set the {spec.api_key_env} environment variable")
    return lambda model, batch: translate_batch(
        batch,
        model,
        base_url=spec.endpoint,
        api_key=api_key,
        timeout=spec.timeout,
        temperature=spec.temperature,
    )


def open_cache(
    spec: EngineSpec,
    cache_path: Path,
    *,
    validation_identity: str,
    request: Request | None = None,
) -> TranslationCache:
    """Open the durable cache for this engine; use it as a context manager.

    ``request`` replaces the abersetz transport (tests, other transports); the
    cache identity still names the abersetz transport and temperature, so pass a
    separate cache file when substituting a real alternative transport.
    """
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    return TranslationCache(
        cache_path,
        models=spec.models,
        request=request or abersetz_request(spec),
        endpoint_identity=spec.endpoint,
        engine_identity=engine_identity(spec),
        validation_identity=validation_identity,
        validate=partial(validate_batch),
    )
