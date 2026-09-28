#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["vexy-localizzy"]
# ///
# this_file: examples/quickstart.py
"""Run with an installed checkout: python examples/quickstart.py."""

import tempfile
from pathlib import Path

from vexy_localizzy.corpus import Corpus

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with Corpus(root / "memory.sqlite") as corpus:
            for name, weight in [("manual", 3), ("reference", 2)]:
                source = root / f"{name}.tmx"
                source.write_text(
                    f'<tmx><body><tu tuid="{name}"><tuv lang="en"><seg>Moon</seg></tuv><tuv lang="pl"><seg>Księżyc</seg></tuv></tu></body></tmx>'
                )
                corpus.import_tmx(source, family=name, weight=weight)
            winner = next(corpus.iter_winners())
            links = corpus.provenance(winner["candidate_id"])
            print(
                f"winner={winner['target']} score={winner['score']} sources={len(links)}"
            )
