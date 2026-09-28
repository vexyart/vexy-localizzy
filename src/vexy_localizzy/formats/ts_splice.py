# this_file: src/vexy_localizzy/formats/ts_splice.py
"""Splice re-rendered Qt messages into the original TS bytes.

Editing a few translations must not rewrite the whole catalog. ``ts_write.dump``
locates each ``<message>`` element as a byte span, renders only the edited
messages in the document's own style and splices them back. Every byte outside
the edited spans, and outside the ``<TS>`` start tag when its attributes change,
is copied verbatim.
"""

import copy
import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from xml.sax.saxutils import escape

from lxml import etree

_SKIP = rb"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<!DOCTYPE(?:[^\[>]|\[.*?\])*>"
_ATTR = rb"""\s+[^\s=/>]+\s*=\s*(?:"[^"]*"|'[^']*')"""
_MESSAGE = re.compile(
    _SKIP
    + rb"|(?P<open><message(?:"
    + _ATTR
    + rb")*\s*(?P<empty>/)?>)|(?P<close></message\s*>)",
    re.S,
)
_ROOT = re.compile(_SKIP + rb"|(?P<root><TS(?:" + _ATTR + rb")*\s*/?>)", re.S)
_ROOT_ATTR = re.compile(rb"""(\s+)([^\s=/>]+)(\s*=\s*)("[^"]*"|'[^']*')""")
_MARKUP = re.compile(rb"(" + _SKIP + rb"|<[^>]*>)", re.S)
_EXPANDED = re.compile(rb"<([A-Za-z_][\w.-]*)(?:\s[^<>]*)?></\1>")
_SELF_CLOSED = re.compile(rb"<([A-Za-z_][\w.-]*)(?:\s[^<>]*)?/>")
_LINE_INDENT = re.compile(rb"^([ \t]*)<(context|message)[\s>]", re.M)
_EOL_SPACES = re.compile(rb" +(?=\r?\n)")
_EOL_ENTITY = re.compile(rb"(?:&#32;)+(?=\r?\n)")
_STRUCTURAL = {"numerusform", "lengthvariant"}
_LAYOUT = {"translation", "numerusform"}


@dataclass(frozen=True)
class MessageSpan:
    ordinal: int
    start: int  # byte offset of "<message"
    end: int  # byte offset just after "</message>"
    indent: bytes  # whitespace preceding "<message" on its line


@dataclass(frozen=True)
class TsStyle:
    declaration: (
        bytes  # exact first line, e.g. b'<?xml version="1.0" encoding="utf-8"?>'
    )
    expanded_empty: frozenset[str]  # tags written as <x ...></x> when empty
    indent_unit: bytes  # b"    " detected from <context> depth
    newline: bytes  # b"\n" or b"\r\n"
    escape_apos: bool  # original text uses &apos;
    escape_quot: bool  # original text uses &quot;
    encoding: str = "UTF-8"
    escape_eol_space: bool = False  # spaces before a newline written as &#32;


def message_spans(raw: bytes) -> list[MessageSpan]:
    """Tokenize ``<message>`` elements, skipping comments, CDATA, PIs and DOCTYPE."""
    spans: list[MessageSpan] = []
    start = None
    for match in _MESSAGE.finditer(raw):
        if match.group("open"):
            if start is not None:
                raise ValueError("TS messages cannot nest")
            if match.group("empty"):
                spans.append(_span(raw, len(spans), match.start(), match.end()))
            else:
                start = match.start()
        elif match.group("close"):
            if start is None:
                raise ValueError("Unbalanced </message> in TS document")
            spans.append(_span(raw, len(spans), start, match.end()))
            start = None
    if start is not None:
        raise ValueError("Unterminated <message> in TS document")
    return spans


def _span(raw: bytes, ordinal: int, start: int, end: int) -> MessageSpan:
    prefix = raw[raw.rfind(b"\n", 0, start) + 1 : start]
    return MessageSpan(ordinal, start, end, b"" if prefix.strip(b" \t") else prefix)


def check_spans(
    raw: bytes, spans: Sequence[MessageSpan], elements: Sequence, encoding: str
) -> None:
    """Raise unless every span parses to the same XML as the lxml message element."""
    if len(spans) != len(elements):
        raise ValueError(
            "TS span tokenizer disagrees with XML parser at message "
            f"{min(len(spans), len(elements))}"
        )
    wrapped = [b"<all>"]
    for span, element in zip(spans, elements, strict=True):
        parent = element.getparent()
        scope = parent.nsmap if parent is not None else {}
        decls = "".join(
            f" xmlns{':' + prefix if prefix else ''}={_quote(uri)}"
            for prefix, uri in scope.items()
        )
        wrapped += [f"<w{decls}>".encode(encoding), raw[span.start : span.end], b"</w>"]
    wrapped.append(b"</all>")
    parser = etree.XMLParser(
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        strip_cdata=False,
        huge_tree=True,
        encoding=encoding,
    )
    try:
        parsed = etree.fromstring(b"".join(wrapped), parser)
    except etree.XMLSyntaxError as error:
        raise ValueError(
            "TS span tokenizer disagrees with XML parser (spans do not parse)"
        ) from error
    for ordinal, (wrapper, element) in enumerate(zip(parsed, elements, strict=True)):
        if len(wrapper) != 1 or _c14n(wrapper[0]) != _c14n(element):
            raise ValueError(
                f"TS span tokenizer disagrees with XML parser at message {ordinal}"
            )


def _c14n(element) -> bytes:
    return etree.tostring(element, method="c14n", exclusive=True, with_tail=False)


def _quote(value: str) -> str:
    return '"' + escape(value, {'"': "&quot;"}) + '"'


def detect_style(raw: bytes, encoding: str = "UTF-8") -> TsStyle:
    """Measure the conventions the original writer used."""
    first_end = raw.find(b"\n")
    first = raw if first_end < 0 else raw[:first_end]
    newline = b"\r\n" if first.endswith(b"\r") else b"\n"
    declaration = first.rstrip(b"\r") if raw.startswith(b"<?xml") else b""
    expanded: dict[str, int] = {}
    closed: dict[str, int] = {}
    for pattern, counts in ((_EXPANDED, expanded), (_SELF_CLOSED, closed)):
        for match in pattern.finditer(raw):
            name = match.group(1).decode("ascii")
            counts[name] = counts.get(name, 0) + 1
    names = {name for name in expanded if expanded[name] > closed.get(name, 0)}
    if "translation" not in expanded and "translation" not in closed:
        names.add("translation")  # lupdate always expands empty translations
    texts = _MARKUP.split(raw)[::2]
    text = b"\0".join(texts)  # separator keeps matches inside one text node
    indents = {
        m.group(2): m.group(1) for m in reversed(list(_LINE_INDENT.finditer(raw)))
    }
    outer, inner = indents.get(b"context", b""), indents.get(b"message")
    unit = b"    "
    if inner is not None and inner.startswith(outer) and len(inner) > len(outer):
        unit = inner[len(outer) :]
    return TsStyle(
        declaration=declaration,
        expanded_empty=frozenset(names),
        indent_unit=unit,
        newline=newline,
        escape_apos=text.count(b"&apos;") > text.count(b"'"),
        escape_quot=text.count(b"&quot;") > text.count(b'"'),
        encoding=encoding,
        escape_eol_space=len(_EOL_ENTITY.findall(text))
        > len(_EOL_SPACES.findall(text)),
    )


def render_message(
    message, style: TsStyle, indent: bytes, created: Collection = ()
) -> bytes:
    """Serialize one message element in the document's style.

    ``created`` names descendants added by this edit. Only they receive
    indentation, taken from their pretty-printed neighbours; whitespace already
    in the document is never re-laid-out.
    """
    order = list(message.iter())
    new_positions = {
        i for i, node in enumerate(order) if any(node is c for c in created)
    }
    clone = copy.deepcopy(message)
    clone.tail = None
    nodes = list(clone.iter())
    new_nodes = [nodes[i] for i in sorted(new_positions)]
    own_ws = "\n" + indent.decode(style.encoding)
    _indent_new(clone, new_nodes, own_ws, style.indent_unit.decode(style.encoding))
    for node in nodes:
        if not isinstance(node.tag, str) or len(node):
            continue
        name = etree.QName(node).localname
        if name in style.expanded_empty and node.text is None:
            node.text = ""
        elif name not in style.expanded_empty and node.text == "":
            node.text = None
    rendered = etree.tostring(
        clone, encoding=style.encoding, xml_declaration=False, with_tail=False
    )
    rendered = _strip_inherited_ns(rendered, message, style.encoding)
    rendered = _escape(rendered, style)
    if style.newline != b"\n":
        rendered = rendered.replace(b"\n", style.newline)
    return rendered


def _indent_new(clone, new_nodes, own_ws: str, unit: str) -> None:
    fresh = {id(node) for node in new_nodes}
    for node in new_nodes:
        parent = node.getparent()
        if parent is None:
            continue
        child_ws = _child_ws(parent, clone, own_ws, unit, fresh)
        if child_ws is None:
            continue
        kids = list(parent)
        index = kids.index(node)
        if index == len(kids) - 1:
            node.tail = _close_ws(parent, clone, own_ws)
            if index > 0:
                kids[index - 1].tail = child_ws
        else:
            node.tail = child_ws


def _is_ws(value: str | None) -> bool:
    return bool(value) and not value.strip() and "\n" in value


def _before_ws(node, clone, own_ws: str) -> str | None:
    if node is clone:
        return own_ws
    previous = node.getprevious()
    value = previous.tail if previous is not None else node.getparent().text
    return "\n" + value.rsplit("\n", 1)[-1] if _is_ws(value) else None


def _close_ws(parent, clone, own_ws: str) -> str:
    return _before_ws(parent, clone, own_ws) or "\n"


def _child_ws(parent, clone, own_ws, unit, fresh) -> str | None:
    """Indentation for new children of a layout container, or None.

    Only the message itself and ``translation``/``numerusform`` elements whose
    children are all ``numerusform``/``lengthvariant`` are layout containers.
    Anything else (text with ``<byte>`` children, for instance) is content, and
    whitespace there would change the translation.
    """
    if parent is not clone and (
        etree.QName(parent).localname not in _LAYOUT
        or any(
            not isinstance(kid.tag, str)
            or etree.QName(kid).localname not in _STRUCTURAL
            for kid in parent
        )
    ):
        return None
    if any((kid.tail or "").strip() for kid in parent):
        return None  # mixed content
    if _is_ws(parent.text):
        return "\n" + parent.text.rsplit("\n", 1)[-1]
    if parent.text or any(id(kid) not in fresh for kid in parent):
        return None  # compact layout stays compact
    before = _before_ws(parent, clone, own_ws)
    if before is None:
        return None
    parent.text = before + unit
    return parent.text


def _strip_inherited_ns(rendered: bytes, message, encoding: str) -> bytes:
    parent = message.getparent()
    if parent is None:
        return rendered
    inherited = {p: u for p, u in parent.nsmap.items() if message.nsmap.get(p) == u}
    end = rendered.find(b">")
    head = rendered[:end]
    for prefix, uri in inherited.items():
        decl = f" xmlns{':' + prefix if prefix else ''}={_quote(uri)}".encode(encoding)
        head = head.replace(decl, b"", 1)
    return head + rendered[end:]


def _escape(rendered: bytes, style: TsStyle) -> bytes:
    if not (style.escape_apos or style.escape_quot or style.escape_eol_space):
        return rendered
    pieces = _MARKUP.split(rendered)
    for i, piece in enumerate(pieces):
        if i % 2 == 0:
            if style.escape_apos:
                piece = piece.replace(b"'", b"&apos;")
            if style.escape_quot:
                piece = piece.replace(b'"', b"&quot;")
            if style.escape_eol_space:
                piece = _EOL_SPACES.sub(lambda m: b"&#32;" * len(m.group()), piece)
        elif style.escape_apos and not piece.startswith((b"<!", b"<?")):
            piece = piece.replace(b"'", b"&apos;")
        pieces[i] = piece
    return b"".join(pieces)


def splice(
    raw: bytes,
    replacements: Mapping[int, bytes],
    *,
    root_attrs: Mapping[str, str | None] | None = None,
    insert_after: Mapping[int, bytes] | None = None,
) -> bytes:
    """Replace message spans by ordinal; optionally rewrite ``<TS>`` attributes."""
    spans = message_spans(raw)
    insert_after = insert_after or {}
    unknown = (set(replacements) | set(insert_after)) - set(range(len(spans)))
    if unknown:
        raise ValueError(f"No TS message with ordinal {min(unknown)}")
    edits = [
        (spans[i].start, spans[i].end, replacement)
        for i, replacement in replacements.items()
    ]
    edits += [(spans[i].end, spans[i].end, extra) for i, extra in insert_after.items()]
    if root_attrs:
        start, end = _root_tag(raw)
        edits.append((start, end, _rewrite_root(raw[start:end], root_attrs)))
    out, cursor = [], 0
    for start, end, data in sorted(edits, key=lambda edit: (edit[0], edit[1])):
        if start < cursor:
            raise ValueError("Overlapping TS splice edits")
        out += [raw[cursor:start], data]
        cursor = end
    out.append(raw[cursor:])
    return b"".join(out)


def _root_tag(raw: bytes) -> tuple[int, int]:
    for match in _ROOT.finditer(raw):
        if match.group("root"):
            return match.start(), match.end()
    raise ValueError("TS start tag not found")


def _rewrite_root(tag: bytes, attrs: Mapping[str, str | None]) -> bytes:
    pending = dict(attrs)

    def replace(match: re.Match) -> bytes:
        name = match.group(2).decode("utf-8")
        if name not in pending:
            return match.group(0)
        value = pending.pop(name)
        if value is None:
            return b""
        quote = match.group(4)[:1]
        entities = {'"': "&quot;"} if quote == b'"' else {"'": "&apos;"}
        encoded = escape(value, entities).encode("utf-8")
        return (
            match.group(1) + match.group(2) + match.group(3) + quote + encoded + quote
        )

    head_end = len(tag) - (2 if tag.endswith(b"/>") else 1)
    head = _ROOT_ATTR.sub(replace, tag[:head_end])
    added = b"".join(
        f" {name}={_quote(value)}".encode()
        for name, value in pending.items()
        if value is not None
    )
    stem = len(head.rstrip())
    return head[:stem] + added + head[stem:] + tag[head_end:]
