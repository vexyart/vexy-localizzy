---
this_file: docs/review.md
---
# Browser catalog review

Install `vexy-localizzy[review]` for the loopback server and filesystem store.
The packaged browser application stores canonical JSON catalogs
with retained native documents, richer review states and an append-only journal.
It does not require the corpus database.

From a source checkout, build the browser assets before building a wheel:

```sh
cd review
npm ci
npm run build
npm test
cd ..
uv run --extra review python examples/review_sample.py /tmp/localizzy-sample
uv run --extra review localizzy review /tmp/localizzy-sample/review.toml
```

Open `http://127.0.0.1:8765`. Sample generation requires a new directory and
refuses to overwrite previous work. Installed wheels already contain the browser
assets and require no Node runtime. An sdist includes source and built assets.

Configuration is one TOML file. Paths are relative to its `root`, resolved from
the config directory. Explicit catalog IDs and UI IDs keep arbitrary files out
of the API. Import source TS once into a JSON catalog as shown below.

```toml
root = "."
suggestions = "suggestions.json" # optional
[catalogs]
main = "catalog.json"
[ui_files]
dialog = "dialog.ui"
[plural_forms]
main = ["0", "1", "2"]
```

Search or filter messages, click rendered text to select its unambiguous matching
context/source/comment, and edit every native target form. The preview updates
as you type; Original/Localized tabs and Fit/percentage scale are available.
Ctrl/Cmd+S saves a draft; Ctrl/Cmd+Enter approves and advances; Alt+Up/Down moves
between filtered messages. Unsaved navigation requires an explicit discard.
Save errors retain the draft. On a revision conflict, copy needed changes and
reload the saved version before reconciling them. Export TS downloads the saved
catalog; save pending changes first. UI-less messages remain editable.

The renderer handles standard Qt widgets and preserves their geometry. Custom
application widgets may appear as the renderer's generic placeholders. This is
a localization preview, not execution of application code. External/QRC resource
images are not loaded by this first reviewer; text remains available. An isolated
iframe disallows scripts/network resource loads, and corpus/translation markup
is sanitized or displayed literally. Text direction is automatic for RTL text.

Suggestions JSON maps catalog ID → message key → a list of objects with `source`,
`target` and `provenance`. `create_app(..., suggestions=callback)` can instead query
a memory at request time; the callback receives catalog ID and the selected Unit.

The API exposes GET `/api/catalogs`, `/api/catalogs/{id}`, `/api/ui`,
`/api/ui/{id}`, `/api/catalogs/{id}/suggestions?key=...`, and
`/api/catalogs/{id}/export.ts`. POST `/api/catalogs/{id}/validate` and `/edits`
accept `{key, revision, targets, action, reason}`; `reason` defaults to empty.
Successful edits return the new catalog projection/revision. Invalid edits return
422; stale revisions return 409. Retained native source bytes stay on the server.

```python
from vexy_localizzy.formats import json_io, ts
from vexy_localizzy.review.store import ReviewEdit, ReviewStore

# Import once into the configured review workspace.
json_io.dump(ts.load(source_ts), workspace / "catalog.json")
store = ReviewStore(
    workspace,
    {"main": "catalog.json"},
    plural_forms={"main": ("0", "1")},
)
current = store.open("main")
saved = store.save(
    "main",
    ReviewEdit(
        key=message_key,
        revision=current.revision,
        targets={"scalar": translated_text},
        action="draft",
    ),
)
ts.dump(saved.catalog, output_ts)
```

Supply the native plural keys for each configured catalog. `targets` must contain
every slot for the edited message: `scalar`, `variant:0`, or native plural keys
such as `0`, `1` and `2:0` for a plural length variant. Edits cannot change source
text, metadata or the native target shape. Configure `policies={catalog_id:
TextPolicy(...)}` when a catalog uses a different placeholder syntax.

Drafts remain `needs_review`; approval sets `approved`. Both actions reject
structural QA failures. Approval of unchanged text additionally requires a
nonblank `reason`, retained in the journal. Other messages are preserved, including
their unfinished state. Exporting TS leaves drafts unfinished and approved text
finished; canonical JSON retains the more precise distinction.

Each save checks the expected SHA-256 revision while holding the catalog's
file lock. A stale revision raises `ReviewConflict`; reopen and reconcile the
edit instead of overwriting another editor's work. Each catalog has adjacent
`.review.lock` and `.review.jsonl` files. Catalog IDs are explicitly configured;
catalog, lock and journal paths must stay inside the configured root. The complete
set of catalog and sidecar paths is checked for collisions and file aliases before
acquiring a lock, so a lock file cannot truncate a configured catalog.

The journal records an intent with old/new hashes and the edit before replacing
the catalog, then a completion marker. Journal creation and catalog replacement
directory entries are synced before completion. On reopen, an unfinished intent whose
old hash matches is recorded as unapplied; a matching new hash is recorded as
applied. A third hash raises an external-change conflict. Recovery never replays
edits. Malformed/truncated journal rows fail explicitly and remain intact for
inspection. Keep the journal together with its catalog.

The implementation follows the published [filelock context-manager
contract](https://py-filelock.readthedocs.io/en/latest/) and uses the existing
temporary-file/[atomic replacement](https://docs.python.org/3/library/os.html#os.replace)
writer. Review writes require a filesystem supporting directory synchronization;
unsupported operations fail explicitly with the journal preserved. Tests inject
interruption before and after replacement, check synchronization ordering and
exercise simultaneous stale submissions. No simulated test proves hardware
power-loss behavior on every filesystem.
