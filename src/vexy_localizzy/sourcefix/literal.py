# this_file: src/vexy_localizzy/sourcefix/literal.py
"""A parsed source literal with byte offsets and Qt identity constraints."""

from dataclasses import dataclass

from vexy_localizzy.sourcefix.catalog import Key


@dataclass(frozen=True)
class Literal:
    start: int
    end: int
    text: str
    first_line: int
    last_line: int
    anchors: tuple[int, ...] = ()
    prefix: str = ""
    context: str | None = None
    comment: str | None = None
    fragments: tuple[tuple[int, int], ...] = ()

    def matches(self, identity: Key, line: int | None) -> bool:
        return (
            self.text == identity[1]
            and (
                line is None
                or self.first_line <= line <= self.last_line
                or line in self.anchors
            )
            and (self.context is None or self.context == identity[0])
            and (self.comment is None or self.comment == identity[2])
        )
