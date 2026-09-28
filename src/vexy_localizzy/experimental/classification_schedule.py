# this_file: src/vexy_localizzy/experimental/classification_schedule.py
"""Keep only the configured number of classification batches in flight."""

import sqlite3
from collections.abc import Callable, Iterable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from loguru import logger

from vexy_localizzy.experimental.classification import Entry
from vexy_localizzy.experimental.classification_cache import (
    CachedClassifier,
    ClassificationPending,
)
from vexy_localizzy.experimental.classification_checkpoints import (
    check_dispatch,
    check_saved,
    save_batch,
    save_pending,
)
from vexy_localizzy.experimental.classification_evidence import RunIdentity


def run_batches(
    groups: Iterable[list[Entry]],
    make_classifier: Callable[[], CachedClassifier],
    db: sqlite3.Connection,
    identity: RunIdentity,
    coverage: dict[str, int],
    rare: set[str],
    *,
    workers: int,
    verbose: bool,
) -> None:
    def resolve(batch: list[Entry]):
        with make_classifier() as classifier:
            result = classifier.classify_detailed(batch)
            if not result.identity_verified:
                raise ClassificationPending(
                    "Provider model identities are not verified"
                )
            return result

    groups = iter(groups)
    exhausted, completed = False, 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {}
        while pending or not exhausted:
            while len(pending) < workers and not exhausted:
                batch = next(groups, None)
                if batch is None:
                    exhausted = True
                else:
                    check_dispatch(db, batch, coverage)
                    if not check_saved(db, batch, coverage, identity, rare):
                        pending[pool.submit(resolve, batch)] = batch
            if not pending:
                continue
            ready, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in ready:
                batch = pending.pop(future)
                try:
                    result = future.result()
                except ClassificationPending as error:
                    save_pending(db, batch, error)
                    if verbose:
                        logger.warning(
                            "Classification batch {} pending: {}", batch[0].id, error
                        )
                else:
                    save_batch(db, batch, result, coverage, rare)
                    completed += len(batch)
                    if verbose:
                        logger.info("Saved {} new classification decisions", completed)
