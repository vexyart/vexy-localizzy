# this_file: src/vexy_localizzy/experimental/classification_run.py
"""Resumable bounded classification with sealed per-batch and final evidence."""

import hashlib
import json
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from vexy_localizzy.experimental.classification_cache import CachedClassifier
from vexy_localizzy.experimental.classification_checkpoints import (
    batch_key,
    check_saved,
    payload_digest,
)
from vexy_localizzy.experimental.classification_evidence import RunIdentity, policy
from vexy_localizzy.experimental.classification_models import Request, model_chains
from vexy_localizzy.experimental.classification_results import validated_results
from vexy_localizzy.experimental.classification_run_completion import finish_run
from vexy_localizzy.experimental.classification_run_inputs import (
    input_batches,
    input_identity,
)
from vexy_localizzy.experimental.classification_run_store import open_run
from vexy_localizzy.experimental.classification_schedule import run_batches


def run_classification(
    inputs: str | Path,
    directory: str | Path,
    *,
    cache_path: str | Path,
    models: Sequence[str],
    prompt: str,
    request: Request,
    endpoint_identity: str,
    fallbacks: dict[str, Sequence[str]] | None = None,
    model_identities: dict[str, str] | None = None,
    rare_threshold: float = 0.01,
    workers: int = 4,
    batch_bytes: int = 48000,
    max_request_bytes: int = 64000,
    clock: Callable[[], float] = time.time,
    verbose: bool = False,
) -> dict:
    """Classify a frozen input, retaining missing work and completing only exact IDs.

    Install the llm extra for the file lock. Inputs and the response cache must be
    outside the run directory. Each transport must have its own bounded timeout.
    A changed rubric/input/policy/batch size requires a separate run directory;
    compatible response cache entries remain reusable. No network calls are made
    until the entire input and every existing batch checkpoint have been checked.
    """
    from filelock import FileLock

    model_chains(models, fallbacks)
    if (
        any(
            type(n) is not int or n < 1
            for n in (workers, batch_bytes, max_request_bytes)
        )
        or workers > 32
    ):
        raise ValueError("Use 1–32 workers and positive integer byte budgets")
    if (
        not isinstance(prompt, str)
        or not prompt
        or not isinstance(endpoint_identity, str)
        or not endpoint_identity
    ):
        raise ValueError("A rubric and endpoint identity are required")
    inputs, directory, cache_path = (
        Path(inputs).resolve(),
        Path(directory).resolve(),
        Path(cache_path).resolve(),
    )
    if (
        inputs == cache_path
        or inputs.is_relative_to(directory)
        or cache_path.is_relative_to(directory)
    ):
        raise ValueError("Keep input and response cache outside the run directory")
    metadata, digest = input_identity(inputs)
    identity = json.loads(
        json.dumps(
            {
                "input_sha256": digest,
                "source_snapshot": metadata.source_snapshot,
                "models": models,
                "fallbacks": fallbacks or {},
                "model_identities": model_identities or {},
                "endpoint": endpoint_identity,
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "rare_threshold": rare_threshold,
                "consensus_version": 1,
                "batching_version": 2,
                "batch_bytes": batch_bytes,
                "max_request_bytes": max_request_bytes,
            }
        )
    )
    parsed = RunIdentity.model_validate(identity)
    _, rare = policy(parsed, metadata)
    run_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)

    def groups():
        return input_batches(
            inputs,
            metadata,
            digest,
            batch_bytes=batch_bytes,
            max_request_bytes=max_request_bytes,
            prompt=prompt,
        )

    def make_classifier():
        return CachedClassifier(
            cache_path,
            models=models,
            prompt=prompt,
            coverage=metadata.coverage,
            request=request,
            endpoint_identity=endpoint_identity,
            fallbacks=fallbacks,
            model_identities=model_identities,
            max_request_bytes=max_request_bytes,
            clock=clock,
        )

    with (
        FileLock(directory / ".run.lock", timeout=0),
        open_run(directory, identity) as db,
    ):
        if (directory / "complete.json").exists():
            with validated_results(directory, inputs):
                return json.loads((directory / "complete.json").read_text())
        db.execute(
            "CREATE TEMP TABLE dispatch_inputs(key TEXT PRIMARY KEY,input_sha256 TEXT NOT NULL)"
        )
        saved_entries = saved_batches = 0
        for batch in groups():
            db.execute(
                "INSERT INTO dispatch_inputs VALUES (?,?)",
                (batch_key(batch), payload_digest(batch, metadata.coverage)),
            )
            if check_saved(db, batch, metadata.coverage, parsed, rare):
                saved_entries += len(batch)
                saved_batches += 1
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != count
            for table, count in (
                ("decisions", saved_entries),
                ("decision_models", saved_entries),
                ("completed_batches", saved_batches),
            )
        ):
            raise ValueError(
                "Classification contains extra or unsealed checkpoint evidence"
            )
        db.commit()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with make_classifier():
            pass  # Initialize the shared response cache before workers connect.
        run_batches(
            groups(),
            make_classifier,
            db,
            parsed,
            metadata.coverage,
            rare,
            workers=workers,
            verbose=verbose,
        )
        return finish_run(db, directory, inputs, metadata, parsed, run_id, rare)
