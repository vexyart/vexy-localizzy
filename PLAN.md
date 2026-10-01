---
this_file: PLAN.md
---
# Plan

vexy-localizzy is the localization software: catalogs, memories, memory-aware
translation, TS upgrades, QA, review, Qt tooling. `abersetz` is the engine below
it; a project (its `localizzy.toml`, catalogs, memories and review records) sits
on top. The package never holds a product path, name or language roster.

[TODO.md](TODO.md) is the flat backlog, [CHANGELOG.md](CHANGELOG.md) records
what shipped, [WORK.md](WORK.md) holds the current checkpoint and test results.

## 1. Release gates

1. **Engine pin.** The `translation` extra needs `abersetz>=1.1`. Until abersetz
   1.1 is on PyPI the extra installs only from a checkout. Publish abersetz
   first, then drop the editable `[tool.uv.sources]` entry and refresh `uv.lock`.
2. **Fresh-install check.** In a clean environment: `uv tool install
   'vexy-localizzy[translation,sources,review]'`, then `localizzy doctor`, a
   memory-only `translate`, `qa`, `qt scan` and `review` on the example data.
3. **Trusted publishing.** A tag-triggered GitHub Actions workflow that builds
   the wheel (with the review frontend already built) and publishes through PyPI
   trusted publishing. Needs the PyPI project to name the workflow; until then
   releases are built and uploaded by hand.

## 2. Upgrade and translation engine

The open findings of the September 2026 review, in [TODO.md](TODO.md): provenance
keys on relocated and fuzzy ports, vanished-message revival, empty-source
candidates, fuzzy assignment by score, one transaction for NEW, RETIRED and the
report, one cache identity for translate and upgrade, and a splice writer that
re-renders only the translation subtree. Each needs a failing test first.

## 3. Qt source scanner

- The clang engine is the engine of record for context drift and non-literal
  arguments, but only with a compilation database. Verify it on a real project
  with `compile_commands.json`, then move namespace and static-scope detection
  (`QT-NS-004`, `QT-STATIC-005`) to the AST as well.
- Detectors are additive. Candidates: `QCoreApplication::translate` with a
  context that no class declares, and `tr()` inside a lambda captured before a
  translator is installed.

## 4. Quality layers

- Calibrate the judge layer against human review ledgers before using its score
  as a gate; report agreement, not only a threshold.
- Decide whether COMET quality estimation earns an extra (it pulls in a large
  model runtime) or stays a documented manual install.
- A nightly benchmark: export the example vocabulary corpus, translate it, run
  `vocab compare`, and keep the series. The pieces exist; the schedule does not.

## 5. Later, each with its own acceptance scenario

- **Assisted instrumentation.** `qt fix`: propose `tr()` wrapping and `Q_OBJECT`
  insertions for scanner findings as a diff; dry run by default, never a silent
  source edit.
- **TMS synchronization.** Crowdin or Weblate push and pull with explicit
  catalog ownership and a round-trip check that proves no reviewed target
  changed.
- **Model re-benchmarking.** Quarterly comparison of translation models on the
  vocabulary corpus and a held-out reviewed catalog.
- **ICU translation.** Catalog translation refuses ICU plural messages until an
  application supplies its format policy; design that policy input.
