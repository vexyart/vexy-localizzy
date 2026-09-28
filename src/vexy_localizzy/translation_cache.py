# this_file: src/vexy_localizzy/translation_cache.py
"""Durable validated translation batches with ordered provider fallback."""

import hashlib
import time
from copy import copy

from vexy_localizzy.provider_errors import ProviderUnavailable
from vexy_localizzy.translation_store import digest, encoded, open_store
from vexy_localizzy.translation_types import (
    TranslationBatch,
    TranslationResult,
    check_result,
)


class TranslationPending(RuntimeError):
    """No configured provider has supplied a validated result for this batch."""


class TranslationCache:
    """One caller owns each connection; separate callers may share the SQLite file.

    validate(batch,result) must raise on unacceptable content and otherwise return
    None. It runs for both fresh and cached results. Version every validator and
    transport configuration that can affect acceptance or generated text.
    """

    def __init__(
        self,
        path,
        *,
        models,
        request,
        endpoint_identity,
        engine_identity,
        validation_identity,
        validate,
        clock=time.time,
    ):
        if (
            isinstance(models, str)
            or not models
            or len(set(models)) != len(models)
            or any(not isinstance(m, str) or not m.strip() for m in models)
        ):
            raise ValueError("Provide distinct ordered model routes")
        if any(
            not isinstance(v, str) or not v.strip()
            for v in (endpoint_identity, engine_identity, validation_identity)
        ):
            raise ValueError("Endpoint, engine and validation identities are required")
        self.models = tuple(models)
        self.request, self.validate, self.clock = request, validate, clock
        self.endpoint = endpoint_identity
        self.identity = (endpoint_identity, engine_identity, validation_identity)
        self.db = open_store(path)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.db.close()

    def translate_checked(self, batch, *, validation_identity, validate):
        """Apply additional acceptance rules before caching, without changing the owner.

        The scoped view shares this connection and must not close it. Both validators
        retain mutation checks; the combined identity isolates stricter selections.
        """
        if not isinstance(validation_identity, str) or not validation_identity.strip():
            raise ValueError("Additional validation identity is required")

        def combined(value, result):
            self._check(result, value, result.requested_model)
            return validate(value, result)

        scoped = copy(self)
        scoped.identity = (*self.identity, validation_identity)
        scoped.validate = combined
        return scoped.translate(batch)

    def _check(self, result, batch, model):
        if not isinstance(result, TranslationResult):
            raise ValueError("Provider must return a TranslationResult")
        check_result(result, batch, model)
        safe_batch = TranslationBatch.model_validate_json(batch.model_dump_json())
        safe_result = TranslationResult.model_validate_json(result.model_dump_json())
        before = (safe_batch.model_dump_json(), safe_result.model_dump_json())
        if self.validate(safe_batch, safe_result) is not None:
            raise ValueError("Translation validator must raise or return None")
        if before != (safe_batch.model_dump_json(), safe_result.model_dump_json()):
            raise ValueError("Translation validators must not mutate inputs or results")

    def _read(self, key, request_sha, batch, model):
        row = self.db.execute(
            "SELECT model,request_sha256,result,checksum FROM responses WHERE key=?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        if row[0] != model or row[1] != request_sha:
            raise ValueError("Translation cache response identity differs")
        if hashlib.sha256(row[2].encode()).hexdigest() != row[3]:
            raise ValueError("Translation cache checksum differs")
        result = TranslationResult.model_validate_json(row[2])
        self._check(result, batch, model)
        return result

    def _attempt(self, model, batch, key):
        before = encoded(batch.model_dump())
        for _ in range(3):
            value = TranslationBatch.model_validate_json(before)
            try:
                result = self.request(model, value)
                if encoded(value.model_dump()) != before:
                    raise ValueError("Provider changed translation request inputs")
                self._check(result, batch, model)
                return result
            except ProviderUnavailable as error:
                with self.db:
                    self.db.execute(
                        "INSERT INTO attempts VALUES (?,?,?)",
                        (key, model, error.reason),
                    )
                    self.db.execute(
                        "INSERT INTO cooldowns VALUES (?,?,?,?) ON CONFLICT(endpoint,model) DO UPDATE SET until=MAX(until,excluded.until),reason=excluded.reason",
                        (
                            self.endpoint,
                            model,
                            self.clock() + error.retry_after,
                            error.reason,
                        ),
                    )
                return None
            except (ValueError, TypeError) as error:
                with self.db:
                    self.db.execute(
                        "INSERT INTO attempts VALUES (?,?,?)",
                        (key, model, type(error).__name__),
                    )
        return None

    def translate(self, batch: TranslationBatch) -> TranslationResult:
        """Reuse valid pinned output; otherwise request eligible alternatives once per route."""
        batch = TranslationBatch.model_validate_json(batch.model_dump_json())
        request_sha = digest(batch.model_dump())
        keys = {
            model: digest([self.identity, request_sha, model]) for model in self.models
        }
        route = digest([self.identity, request_sha, self.models])
        row = self.db.execute(
            "SELECT response_key FROM selections WHERE key=?", (route,)
        ).fetchone()
        if row:
            model = next((model for model, key in keys.items() if key == row[0]), None)
            if model is None:
                raise ValueError("Saved translation route is outside policy")
            result = self._read(row[0], request_sha, batch, model)
            if result is None:
                raise ValueError("Missing selected translation response")
            return result
        for model, key in keys.items():
            result = self._read(key, request_sha, batch, model)
            cooldown = self.db.execute(
                "SELECT until FROM cooldowns WHERE endpoint=? AND model=?",
                (self.endpoint, model),
            ).fetchone()
            if result is None and (cooldown is None or cooldown[0] <= self.clock()):
                result = self._attempt(model, batch, key)
            if result is None:
                continue
            data = result.model_dump_json()
            with self.db:
                self.db.execute(
                    "INSERT OR IGNORE INTO responses VALUES (?,?,?,?,?)",
                    (
                        key,
                        model,
                        request_sha,
                        data,
                        hashlib.sha256(data.encode()).hexdigest(),
                    ),
                )
                self.db.execute(
                    "INSERT OR IGNORE INTO selections VALUES (?,?)", (route, key)
                )
            # Re-read the winner if another connection committed a route first.
            return self.translate(batch)
        raise TranslationPending(
            "No validated translation from: " + ", ".join(self.models)
        )
