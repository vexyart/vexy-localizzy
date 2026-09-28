# this_file: src/vexy_localizzy/json_sequence.py
"""Read adjacent JSON values without assuming source strings are one physical line."""

import json
from collections.abc import Iterator
from typing import Any, TextIO


def values(stream: TextIO, *, chunk_size: int = 1 << 20) -> Iterator[Any]:
    """Yield one JSON value at a time, accepting literal source newlines."""
    decoder = json.JSONDecoder(strict=False)
    buffer = ""
    position = 0
    exhausted = False
    while True:
        start = position
        while start < len(buffer) and buffer[start].isspace():
            start += 1
        if start == len(buffer):
            if exhausted:
                return
            buffer = stream.read(chunk_size)
            position = 0
            exhausted = len(buffer) < chunk_size
            continue
        try:
            value, end = decoder.raw_decode(buffer, start)
        except json.JSONDecodeError as error:
            if exhausted:
                raise ValueError(
                    "Classification input is not a JSON sequence"
                ) from error
            buffer = buffer[start:] + stream.read(chunk_size)
            position = 0
            exhausted = len(buffer) < chunk_size
            continue
        yield value
        position = end
