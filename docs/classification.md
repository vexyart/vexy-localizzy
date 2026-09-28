---
this_file: docs/classification.md
---
# Completed classification to A/B export

`classification_export.export_ab()` connects a completed classification run to the
original corpus. It validates the entire input and decision set before selecting
A/B sources, then exports every weighted winner for those sources with original
lineage. Empty A/B selection produces an empty TMX, never the whole corpus.

```python
import json
from pathlib import Path

from vexy_localizzy.classification_export import export_ab
from vexy_localizzy.corpus import Corpus

with Corpus("memory.sqlite") as corpus:
    report = export_ab(
        corpus, "classification/run", "classification-input.jsonl", "ab.tmx"
    )
Path("ab-report.json").write_text(json.dumps(report, indent=2) + "\n")
```

Keep the returned report, original run/input files and raw source snapshots with
the export. The report binds the run ID, input hash, ordered decision digest,
corpus snapshot, entry map and output hash. `selected_entries` counts English
sources; `units` counts bilingual target units. They need not be equal.

## Run and resume classification

`classification_run.run_classification()` is the bounded producer. Install the
`llm` extra. Supply the frozen input, a separate run directory, shared response
cache, rubric, preferred models and transport:

```python
from functools import partial
from vexy_localizzy.classification_run import run_classification
from vexy_localizzy.translate.openai_transport import chat_request

report = run_classification(
    "classification-input.jsonl", "runs/first",
    cache_path="responses.sqlite",
    models=("model-a", "model-b", "model-c"),
    fallbacks={"model-c": ("alternate",)},
    prompt=rubric,
    request=partial(chat_request, base_url=endpoint, api_key=api_key, timeout=60),
    endpoint_identity=endpoint,
    workers=4,
    verbose=True,
)
```

Model labels, rubric and credentials come from the calling application. The default
four batch workers allow at most twelve simultaneous model calls; each batch has
at most 100 entries. A source larger than the 48 KB batch target is sent alone
when the full rubric/coverage/source request fits the 64 KB request limit; earlier
batch boundaries remain unchanged. Entries exceeding that full limit fail during
preflight without truncation or model calls. The transport must enforce its own
timeout. There is no
unbounded task queue or provider-reset sleep. Malformed/unavailable votes leave
`pending.json` and durable pending batches. Call again after recovery to resume;
completed decisions and successful response-cache votes are reused.

Fallback lists are tried in order when a preferred route is unavailable. HTTP
quota/reset timing is persisted in the shared cache, so even a multi-day cooldown
skips that route immediately across restarts. Connection failures use a short
cooldown. The SDK makes one attempt per call; it does not sleep before fallback.
Malformed responses get at most three attempts before trying an alternative.
Non-text content is rejected before attempt logging, so a malformed proxy reply
cannot abort fallback with a SQLite binding error. Custom transports must return
text or `ModelResponse`; invalid result types follow the same bounded retry and
fallback path. This uses the existing
[OpenAI SDK error handling](https://github.com/openai/openai-python#error-handling)
and disables its nested retries so the shared cache controls routing.
Reset hints are read in order: `retry-after-ms`, `Retry-After` (seconds or HTTP
date), gateway `reset_seconds`, then Google's structured `RetryInfo.retryDelay`.
Invalid hints are skipped; absent usable timing gets a short default cooldown.
The Google duration follows the official
[RetryInfo definition](https://github.com/googleapis/googleapis/blob/master/google/rpc/error_details.proto)
and [ProtoJSON duration format](https://protobuf.dev/programming-guides/json/).
Saved votes remain usable during cooldown, and completed fallback selections stay
fixed after the primary recovers. New batches can try the recovered primary again.
Each decision records the three actual models and their provider-reported
identities; aliases for the same model cannot supply multiple votes. If fewer
than three distinct models succeed, the batch stays pending with its successful
votes cached. Supply alternative routes through the configured transport; no
replacement is represented as an answer from the unavailable model.

The producer validates the entire input and existing checkpoints before requesting
anything. It records each preflight payload digest, checks it again before dispatch
and commit, and binds every committed batch to its input and exact decision/model
rows. Changing input between validation and dispatch cannot poison a checkpoint.
The final marker is published atomically only after complete evidence replay.
An interrupted marker write can be retried without requesting completed votes.

A file lock rejects another writer to the same run. Keep input/cache paths outside
the run directory. The database stores its immutable run identity from creation;
changed input, rubric, model policy or batch limits require a new run directory.
Changing only worker count is allowed. Historical cache responses without reported
model IDs require an explicit `model_identities` map; unknown reports remain null.

The native producer refuses unbound legacy decision databases. To migrate them,
replay the original input/configuration from the preserved response cache into a
new producer-owned directory and independently compare inherited decisions. This
establishes checkpoints from the actual cached votes rather than blessing copied
legacy decision rows. Use an isolated cache copy for offline migration audits.

## Required run evidence

The producer writes `identity.json`, `decisions.sqlite` and `complete.json` in its
run directory. Only the producer may establish completion after reconciling all
expected input IDs. No marker, unfinished batches or legacy unbound decisions
means the run is not ready for this handoff.

`identity.json` contains the exact input SHA-256, corpus `source_snapshot`,
`prompt_sha256`, three preferred `models`, ordered `fallbacks`, explicit
`model_identities`, `rare_threshold`, and `consensus_version: 1`. Other producer
fields may be present; all fields participate in the run hash:
`sha256(json.dumps(identity, sort_keys=True).encode())`.

SQLite tables use these columns:

- `decisions`: `entry_id` primary key, `class`, JSON `votes`, `reason`, `disagreement`.
- `decision_models`: `entry_id` primary key, JSON `models`, `requested_models`,
  `reported_models`, and `identity_verified` (0/1).
- `pending_batches`: producer-specific columns; it must contain no rows.

The completion marker contains `run_id`, `decision_sha256`, `entries`,
`expected_entries`, `pending_entries: 0`, `complete: true`, `classes` (observed
class counts) and sorted `rare_locales`. A matching count alone is insufficient.
After all writes finish, the producer holds one SQLite read transaction while
checking counts and calling `classification_results.decision_digest(db)`, then
atomically writes its marker. The digest covers every ordered joined decision/model
row, serialized as a compact JSON array with a trailing newline. It includes actual
votes and model reports, not merely class totals. The digest function itself is
not a completion validator.

`validated_results(run, inputs)` opens a read-only decision snapshot and checks:

- exact ordered input IDs, complete decision/model rows and the frozen input hash;
- recomputed locale coverage, rarity, consensus, reasons and disagreements;
- permitted routes, three distinct resolved identities, and the claimed preferred
  models; historical null provider reports remain null;
- class totals, expected counts, no pending batches, and the sealed decision digest.

Its `selected_ids()` iterator is usable only inside the context. A later writer
cannot change the decision set being exported. Export reconciles the complete
eligible source-ID set, every English text and every active target-locale list
inside the corpus transaction. It shares eligibility queries with input preparation
and stages them on disk, then checks source/entry-map fingerprints before resolving
winners. Input changes during export abort it.
An error before publication preserves an existing TMX.

## Legacy evidence

New `prepare_inputs()` output includes the entry-map digest. Older input files
need an independently audited ID/text/inline-XML binding supplied through
`entry_map_sha256=...`; never assume numeric IDs survive rebuilding a corpus.
The exporter still compares every frozen English text against its numeric ID.

A legacy completion marker without `decision_sha256` must be upgraded by its
producer after independently reconciling the saved votes to the original run/cache.
The reader deliberately refuses to create this binding from whatever database it
finds. Existing cached votes need not be discarded or requested again.

The public producer writes this contract. External producers may also implement
it. Partial classification cannot be exported as a complete A/B corpus through
this API. Full embeddings, distillation and final exports require their own
complete-data checks.
