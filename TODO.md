<!-- this_file: TODO.md -->
# TODO

Minor findings of the issue 145 review (28 September 2026) left open:

- [ ] Upgrade: do not carry `extra-localizzy-key` across relocated and fuzzy ports; index id-bearing APPROVED messages by context, source and comment as well; add the comment to the loose-tier key.
- [ ] Upgrade: revive vanished APPROVED translations whose source returns, as unfinished ports.
- [ ] Upgrade: an empty-source FRESH message must not consume an APPROVED candidate; check ported plus retired ordinals against every APPROVED message.
- [ ] Upgrade: assign fuzzy candidates by descending score across all pairs, not greedily in document order.
- [ ] Upgrade: write NEW, RETIRED and the report as one transaction.
- [ ] Translate and upgrade should share one cache validation identity, and the engine identity should include the installed abersetz version.
- [ ] Splice writer: re-render only the translation subtree so character references in FRESH-owned elements stay untouched.
- [ ] `scripts/move_modules.py`: leave imports from package re-exports alone so a rerun is a no-op.
- [ ] Publish abersetz 1.1, then drop the editable `[tool.uv.sources]` entry and refresh `uv.lock`; until then the `translation` extra installs only from a checkout.

Tooling that arrived with the Qt and project commands (1 October 2026):

- [ ] Fresh-install check from PyPI in a clean environment (`doctor`, memory-only `translate`, `qa`, `qt scan`, `review`).
- [ ] Tag-triggered trusted-publishing workflow; needs the PyPI project to name the workflow first.
- [ ] `qt scan --engine clang`: verify on a real project with `compile_commands.json`; move `QT-NS-004` and `QT-STATIC-005` to the AST.
- [ ] Judge layer: measure agreement with human review ledgers before its score gates anything.
- [ ] COMET quality estimation: decide between an extra and the documented manual install.
- [ ] Nightly vocabulary benchmark (`vocab export`, `translate`, `vocab compare`) with a kept series.
- [ ] Upgrade: Norwegian and `sr@latin` plural counts.
- [ ] Translate: exit code when the report says `ready: false`; finished glossary term hits.
