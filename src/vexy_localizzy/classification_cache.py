# this_file: src/vexy_localizzy/classification_cache.py
"""Three distinct model routes with persistent caching and provider fallbacks."""

import hashlib
import json
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from pathlib import Path

from vexy_localizzy.classification import Entry, parse_votes, request_text
from vexy_localizzy.classification_models import (
    Request,
    assign_models,
    model_chains,
    request_votes,
)
from vexy_localizzy.classification_store import open_cache
from vexy_localizzy.provider_errors import ProviderUnavailable


@dataclass(frozen=True)
class ClassificationBatch:
    """Routed labels and reported identities follow the order of each entry's votes.

    identity_verified means identities resolve through provider reports or the
    explicit alias map. Legacy string responses leave reported_models unknown.
    """

    votes: dict[int, list[str]]
    models: tuple[str, str, str]
    requested_models: tuple[str, str, str]
    reported_models: tuple[str | None, str | None, str | None] = (None, None, None)
    identity_verified: bool = False


class ClassificationPending(RuntimeError):
    """No complete three-model decision is currently available for a batch."""


@dataclass(frozen=True)
class ResponseBatch:
    """Validated raw responses and durable routing identities for a model panel."""

    responses: tuple[str, str, str]
    models: tuple[str, str, str]
    requested_models: tuple[str, str, str]
    reported_models: tuple[str | None, str | None, str | None]
    identity_verified: bool


def _key(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest()


class CachedClassifier:
    """One caller owns each connection; only transport calls run concurrently.

    Fallbacks are ordered model lists per requested model. Successful fallback
    choices are pinned per input and policy, including after a primary recovers.
    """

    _parse_response = staticmethod(parse_votes)
    _PROBE_INTERVAL = 300
    _FETCH_DEADLINE = 15
    _DEADLINE_COOLDOWN = _PROBE_INTERVAL + 1

    def __init__(
        self,
        path: str | Path,
        *,
        models: Sequence[str],
        prompt: str,
        coverage: dict[str, int],
        request: Request,
        endpoint_identity: str,
        max_request_bytes: int = 64000,
        fallbacks: dict[str, Sequence[str]] | None = None,
        clock: Callable[[], float] = time.time,
        model_identities: dict[str, str] | None = None,
    ):
        self.chains = model_chains(models, fallbacks)
        self.models, self.prompt, self.coverage, self.request = (
            tuple(models),
            prompt,
            dict(coverage),
            request,
        )
        self.endpoint_identity, self.max_request_bytes = (
            endpoint_identity,
            max_request_bytes,
        )
        self.model_identities = dict(model_identities or {})
        candidates = {model for chain in self.chains for model in chain}
        if set(self.model_identities) - candidates or any(
            not isinstance(v, str) or not v for v in self.model_identities.values()
        ):
            raise ValueError("Invalid configured model identities")
        self.clock = clock
        self.db = open_cache(path)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.db.close()

    def defer(self, model: str, seconds: float, reason: str) -> None:
        """Persist known provider recovery time; already cached responses stay usable."""
        failure = ProviderUnavailable(reason, retry_after=seconds)
        now = self.clock()
        until = now + failure.retry_after
        with self.db:
            self.db.execute(
                "INSERT INTO cooldowns VALUES (?,?,?,?) ON CONFLICT(endpoint,model) DO UPDATE SET until=MAX(until,excluded.until),reason=excluded.reason",
                (
                    self.endpoint_identity,
                    model,
                    until,
                    failure.reason,
                ),
            )

            self.db.execute(
                "INSERT INTO model_health VALUES (?,?,?,?,?,?) ON CONFLICT(endpoint,model) DO UPDATE SET state='cool',last_failure=excluded.last_failure,probe_after=excluded.probe_after",
                (
                    self.endpoint_identity,
                    model,
                    "cool",
                    None,
                    now,
                    min(until, now + self._PROBE_INTERVAL),
                ),
            )

    def _record_success(self, model: str) -> None:
        """Make successful routes warm immediately and persist the observation."""
        self.db.execute(
            "INSERT INTO model_health VALUES (?,?,?,?,?,?) ON CONFLICT(endpoint,model) DO UPDATE SET state='warm',last_success=excluded.last_success,last_failure=NULL,probe_after=NULL",
            (self.endpoint_identity, model, "warm", self.clock(), None, None),
        )

    def _health(self, model: str) -> tuple[str, float | None]:
        row = self.db.execute(
            "SELECT state,probe_after FROM model_health WHERE endpoint=? AND model=?",
            (self.endpoint_identity, model),
        ).fetchone()
        if row and row[0] == "cool" and self._available(model):
            return "recovered", None
        return (row[0], row[1]) if row else ("unknown", None)

    def _available(self, model):
        row = self.db.execute(
            "SELECT until FROM cooldowns WHERE endpoint=? AND model=?",
            (self.endpoint_identity, model),
        ).fetchone()
        return row is None or row[0] <= self.clock()

    def _due_probe(self, excluded: set[str]) -> str | None:
        """Return one cooled route whose bounded health probe is due."""
        now = self.clock()
        for model in dict.fromkeys(model for chain in self.chains for model in chain):
            state, probe_after = self._health(model)
            if (
                model not in excluded
                and state == "cool"
                and not self._available(model)
                and probe_after is not None
                and probe_after <= now
            ):
                return model
        return None

    def _response(self, model, payload):
        key = _key([self.endpoint_identity, model, self.prompt, payload])
        row = self.db.execute(
            "SELECT response FROM responses WHERE key=?", (key,)
        ).fetchone()
        return key, row[0] if row else None

    def _identity(self, model: str, payload: str) -> tuple[str | None, str | None]:
        key, _ = self._response(model, payload)
        row = self.db.execute(
            "SELECT model FROM response_models WHERE key=?", (key,)
        ).fetchone()
        reported = row[0] if row else None
        return reported, reported or self.model_identities.get(model)

    def _fetch(self, models, payload, count):
        pool = ThreadPoolExecutor(max_workers=3)
        futures = {
            pool.submit(
                request_votes,
                self.request,
                m,
                self.prompt,
                payload,
                count,
                self._parse_response,
            ): m
            for m in models
        }
        try:
            for future in as_completed(futures, timeout=self._FETCH_DEADLINE):
                model = futures[future]
                attempts, response, unavailable, reported = future.result()
                key, _ = self._response(model, payload)
                with self.db:
                    self.db.executemany(
                        "INSERT INTO attempts(key,model,response,error) VALUES (?,?,?,?)",
                        [(key, model, text, error) for text, error in attempts],
                    )
                    if response is not None:
                        inserted = self.db.execute(
                            "INSERT OR IGNORE INTO responses VALUES (?,?,?,?,?,?)",
                            (
                                key,
                                model,
                                self.endpoint_identity,
                                self.prompt,
                                payload,
                                response,
                            ),
                        )
                        if inserted.rowcount and reported is not None:
                            self.db.execute(
                                "INSERT INTO response_models VALUES (?,?)",
                                (key, reported),
                            )
                    if response is not None:
                        self._record_success(model)
                if unavailable is not None:
                    self.defer(model, unavailable.retry_after, unavailable.reason)
        except FuturesTimeoutError:
            for future, model in futures.items():
                if future.done():
                    continue
                key, _ = self._response(model, payload)
                with self.db:
                    self.db.execute(
                        "INSERT INTO attempts(key,model,response,error) VALUES (?,?,?,?)",
                        (key, model, None, "request_deadline"),
                    )
                # A socket that outlives the request deadline must not enter
                # the next ordinary panel as soon as its 15-second deadline
                # expires. Keep it cool until the scheduled five-minute probe.
                self.defer(model, self._DEADLINE_COOLDOWN, "request_deadline")
        finally:
            # A proxy can retain a socket beyond the client timeout. Do not let
            # such a thread block the durable fallback scheduler indefinitely.
            pool.shutdown(wait=False, cancel_futures=True)

    def _resolve(self, payload: str, count: int) -> tuple[str, str, str]:
        attempted: set[str] = set()
        while True:
            cached, eligible, identities = {}, set(), {}
            for model in dict.fromkeys(
                model for chain in self.chains for model in chain
            ):
                _, response = self._response(model, payload)
                if response is not None:
                    cached[model] = self._parse_response(response, count)
                identity = self._identity(model, payload)[1]
                identities[model] = (
                    "known:" + identity if identity else "unverified:" + model
                )
                if model in cached or (
                    model not in attempted and self._available(model)
                ):
                    eligible.add(model)
            # Resolve a complete cached panel before considering any new requests.
            # Overlapping chains may need reassignment to reuse all three votes.
            selected = assign_models(
                [
                    [model for model in chain if model in cached]
                    for chain in self.chains
                ],
                identities,
            )
            if len(selected) != 3:
                selected = assign_models(
                    [
                        sorted(
                            (model for model in chain if model in eligible),
                            key=lambda model: (
                                model not in cached,
                                self._health(model)[0] != "recovered",
                                self._health(model)[0] != "warm",
                            ),
                        )
                        for chain in self.chains
                    ],
                    identities,
                    initial=selected,
                )
            missing = [model for model in selected.values() if model not in cached]
            if not missing:
                break
            self._fetch(missing, payload, count)
            attempted.update(missing)
        if len(selected) != 3:
            failed = [
                model for slot, model in enumerate(self.models) if slot not in selected
            ]
            raise ClassificationPending(
                "Classification pending; failed models: " + ", ".join(failed)
            )
        probe = self._due_probe(set(selected.values()))
        if probe is not None:
            # A probe is deliberately extra work: its result cannot displace the
            # warm three-route panel currently serving this batch.
            self._fetch([probe], payload, count)
        return tuple(selected[slot] for slot in range(3))

    def classify_detailed(self, entries: list[Entry]) -> ClassificationBatch:
        """Require distinct routes/resolved identities; preserve pending work on exhaustion."""
        payload = request_text(entries, self.coverage)
        if len({entry.id for entry in entries}) != len(entries):
            raise ValueError("Duplicate input entry identities")
        panel = self._panel(payload, len(entries))
        votes = [parse_votes(response, len(entries)) for response in panel.responses]
        return ClassificationBatch(
            {
                entry.id: [model_votes[i] for model_votes in votes]
                for i, entry in enumerate(entries)
            },
            panel.models,
            panel.requested_models,
            panel.reported_models,
            panel.identity_verified,
        )

    def _panel(self, payload: str, count: int) -> ResponseBatch:
        """Share routing/cache semantics with numbered subset selection."""
        if len(self.prompt.encode()) + len(payload.encode()) > self.max_request_bytes:
            raise ValueError("Model request exceeds byte budget")
        route = [self.endpoint_identity, self.prompt, payload, self.chains]
        if self.model_identities:
            route.append(sorted(self.model_identities.items()))
        route_key = _key(route)
        row = self.db.execute(
            "SELECT models FROM selections WHERE key=?", (route_key,)
        ).fetchone()
        selected = tuple(json.loads(row[0])) if row else None
        if selected is not None:
            # A cached assignment may have been created before a provider
            # entered cooldown. Re-resolve only the unfinished route; cached
            # responses remain reusable and completed panels stay immutable.
            if any(
                self._response(model, payload)[1] is None and not self._available(model)
                for model in selected
            ):
                selected = self._resolve(payload, count)
        else:
            selected = self._resolve(payload, count)
        if (
            len(selected) != 3
            or len(set(selected)) != 3
            or any(model not in self.chains[i] for i, model in enumerate(selected))
        ):
            raise ValueError("Invalid cached model selection")
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO selections VALUES (?,?)",
                (route_key, json.dumps(selected)),
            )
        selected = tuple(
            json.loads(
                self.db.execute(
                    "SELECT models FROM selections WHERE key=?", (route_key,)
                ).fetchone()[0]
            )
        )
        identities = [self._identity(model, payload) for model in selected]
        known = [identity for _, identity in identities if identity is not None]
        if len(set(known)) != len(known):
            raise ClassificationPending(
                "Classification pending; provider aliases share a model identity"
            )
        responses = tuple(self._response(model, payload)[1] for model in selected)
        for response in responses:
            self._parse_response(response, count)
        return ResponseBatch(
            responses,
            selected,
            self.models,
            tuple(reported for reported, _ in identities),
            len(known) == 3,
        )

    def classify(self, entries: list[Entry]) -> dict[int, list[str]]:
        """Compatibility interface; use classify_detailed to persist actual model IDs."""
        return self.classify_detailed(entries).votes
