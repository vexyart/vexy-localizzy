# this_file: src/vexy_localizzy/corpus_identity.py
"""Stable fingerprints for corpus-local source identities, including inline XML."""

import hashlib
import json


def entry_map_sha256(db) -> str:
    """Hash ordered [integer ID, source text, source XML] JSON lines in bounded memory."""
    digest = hashlib.sha256()
    for row in db.execute("SELECT id,source,source_xml FROM main.entries ORDER BY id"):
        digest.update(
            json.dumps(list(row), ensure_ascii=False, separators=(",", ":")).encode()
        )
        digest.update(b"\n")
    return digest.hexdigest()
