<!-- this_file: TODO.md -->
# TODO

Minor findings of the issue 145 review (28 September 2026) left open:

- [ ] Upgrade: do not carry `extra-localizzy-key` across relocated and fuzzy ports; index id-bearing APPROVED messages by context, source and comment as well; add the comment to the loose-tier key.
- [ ] Upgrade: revive vanished APPROVED translations whose source returns, as unfinished ports.
- [ ] Upgrade: an empty-source FRESH message must not consume an APPROVED candidate; check ported plus retired ordinals against every APPROVED message.
- [ ] Upgrade: assign fuzzy candidates by descending score across all pairs, not greedily in document order.
- [ ] Upgrade: write NEW, RETIRED and the report as one transaction; `atomic_write` should keep the original file mode.
- [ ] Translate and upgrade should share one cache validation identity, and the engine identity should include the installed abersetz version.
- [ ] Splice writer: re-render only the translation subtree so character references in FRESH-owned elements stay untouched.
- [ ] `scripts/move_modules.py`: leave imports from package re-exports alone so a rerun is a no-op.
- [ ] Publish 1.x once abersetz 1.1 is on PyPI; fl10n then replaces its editable path source with a version pin.
