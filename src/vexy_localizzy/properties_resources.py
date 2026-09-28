# this_file: src/vexy_localizzy/properties_resources.py
"""Java-style properties projection with caller-owned decoding and key policy."""

import javaproperties


def parse_properties(text: str) -> list[tuple[str, str]]:
    """Return all ordered pairs, including duplicate keys and empty values.

    Decode input before calling. Native escapes and odd-backslash continuations
    follow javaproperties; malformed Unicode escapes fail before returning pairs.
    Used by source extraction and consumer resource-discovery wrappers.
    """
    return javaproperties.loads(text, object_pairs_hook=list)
