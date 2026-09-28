# this_file: src/vexy_localizzy/cli/_args.py
"""Normalize Python Fire list flags: a comma string, a tuple/list, or None.

Fire passes ``--flag a.tmx,b.tmx`` as a string but ``--flag=a,b`` as a tuple, and a
repeated flag keeps only its last value. Document comma-separated lists only.
"""

from pathlib import Path


def csv_strings(value: object) -> list[str]:
    """``"a,b"``, ``("a", "b")``, ``["a,b"]`` → ``["a", "b"]``; ``None`` → ``[]``."""
    if value is None:
        return []
    items = value if isinstance(value, list | tuple) else [value]
    return [
        part.strip() for item in items for part in str(item).split(",") if part.strip()
    ]


def csv_paths(value: object) -> list[Path]:
    """Like ``csv_strings``, as paths."""
    return [Path(item) for item in csv_strings(value)]
