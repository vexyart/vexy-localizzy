# this_file: src/vexy_localizzy/qt/cpp_text.py
"""Lightweight C++ text helpers for the heuristic scan: comments, braces, lines.

This is not a C++ parser. It strips ``//`` comments outside string literals and
brace-matches blocks, which is enough for the regex detectors in
``qt.scan_cpp`` and ``qt.scan_scope``. Block comments and raw strings are not
understood; the findings these helpers feed are marked ``heuristic``.
"""


def strip_comment(line: str) -> str:
    """Drop a ``//`` comment from one line, ignoring ``//`` inside string literals."""
    in_str = False
    for i in range(len(line) - 1):
        c = line[i]
        if c == '"' and (i == 0 or line[i - 1] != "\\"):
            in_str = not in_str
        elif not in_str and c == "/" and line[i + 1] == "/":
            return line[:i]
    return line


def code_text(text: str) -> str:
    """The whole file with ``//`` comments removed; line numbers are preserved."""
    return "\n".join(strip_comment(line) for line in text.splitlines())


def block_span(text: str, start: int) -> tuple[int, int] | None:
    """Span of the first brace-matched ``{...}`` at or after ``start``.

    An unbalanced block runs to the end of the text; no ``{`` returns None.
    """
    brace = text.find("{", start)
    if brace == -1:
        return None
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return brace, i + 1
    return brace, len(text)


def line_of(text: str, pos: int) -> int:
    """1-based line number of character offset ``pos``."""
    return text.count("\n", 0, pos) + 1


def inside(pos: int, spans: list[tuple[int, int]]) -> bool:
    """True when ``pos`` falls within any of ``spans``."""
    return any(start <= pos < end for start, end in spans)
