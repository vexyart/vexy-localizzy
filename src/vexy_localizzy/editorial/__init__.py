# this_file: src/vexy_localizzy/editorial/__init__.py
"""Editorial review of an already translated catalog: propose, then apply with guards.

``candidates`` asks a model to review a catalog batch by batch and appends the
corrections it proposes to a JSONL file; it never edits the catalog. ``apply``
writes the accepted candidates back only while the catalog still holds what the
reviewer saw and the correction keeps the source's placeholders, punctuation
and mnemonics, and records every change, skip and stale candidate in a ledger.
"""
