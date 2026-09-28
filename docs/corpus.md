---
this_file: docs/corpus.md
---
<!-- move-modules: skip (written after the move; names the corpus package) -->
# Voting corpus

`vexy_localizzy.corpus` builds translation memories whose entries can be traced
to their sources. It inventories XML translation memories, keeps competing
translations and selects winners by weighted source votes. Keep corpus data and
application configuration in a separate private workspace.

## Inventory

```sh
localizzy inventory /path/to/catalogs /private/work/manifest.jsonl
```

The inventory reports every `.tmx` and `.ts` XML file, including invalid ones.
Check the `invalid` count and the per-file status before using its totals.

## Import

`Corpus.import_tmx(path, family=..., weight=...)` (in `corpus.store`) imports
bilingual and multilingual memories and preserves inline XML. `iter_winners()`
streams the selected candidates, and `provenance(candidate_id)` resolves their
source links. Identical content cannot receive extra votes under another
family. Repeated occurrences within a family contribute one weighted vote.

The database `memory.sqlite` keeps raw input snapshots in `memory.sources/`.
Keep that directory with the database: it preserves the original text and
metadata after source paths change, and the snapshots keep their full original
XML. Imports expose exclusions for missing English and missing targets.

Mixed-product files can select families with `family_property` and an explicit
`family_map`. Duplicate-file aliases keep their paths but share a voting policy.
To change the policy of several aliases, deactivate those paths first and
reimport them consistently.

## Export

`export_tmx(path, entry_ids=ids)` atomically writes the selected winners; omit
`entry_ids` for all winners. The output keeps the original-source links and the
original decision scores and tie flags. `source_snapshot` and
`entry_map_sha256` bind saved IDs to a frozen corpus.

Reimport verifies the raw TU content, copies snapshots into the receiving corpus
and preserves the original votes. Keep referenced snapshots available when you
transfer exports. The database keeps alternative candidates. A winner-only
export records prior conflicts in TU decision properties, while reimport
computes ties among the candidates actually imported.

## Python API

```python
from vexy_localizzy.corpus.store import Corpus
```

Run `examples/quickstart.py` for a complete import and export. The research code
built on the corpus (classification, distillation, embeddings, clustering and
retrieval) lives in `vexy_localizzy.experimental`; see
[classification](classification.md) and [distillation](distillation.md).
