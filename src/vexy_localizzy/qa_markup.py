# this_file: src/vexy_localizzy/qa_markup.py
"""Structural HTML comparison using the standard parser and explicit nesting checks."""

import re
from html import unescape
from html.entities import html5
from html.parser import HTMLParser

VOID = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)
HTML_TAG = re.compile(
    r"</?(?:html|head|body|title|style|script|p|div|span|a|b|i|u|s|strong|em|small|big|"
    r"sub|sup|pre|code|blockquote|ul|ol|li|table|tr|td|th|thead|tbody|h[1-6]|"
    r"br|hr|img|meta|link|input)(?=[\s/>]|$)",
    re.IGNORECASE,
)


class Markup(HTMLParser):
    """Ignore prose, preserve tags/attributes and nonprose style/script contents."""

    def __init__(self, text: str):
        super().__init__(convert_charrefs=False)
        self.events: list[tuple] = []
        self.stack: list[str] = []
        self.errors: list[str] = []
        self.visible: list[str] = []
        self.prose: list[str] = []
        self.feed(text)
        self.close()
        if self.stack:
            self.errors.append("Unclosed tags: " + ",".join(self.stack))

    def handle_starttag(self, tag, attrs):
        if len({name for name, _ in attrs}) != len(attrs):
            self.errors.append("Duplicate attributes: " + tag)
        protected = tuple(
            sorted(
                (name, None if name in ("title", "alt") else value)
                for name, value in attrs
            )
        )
        self.events.append(("start", tag, protected))
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        self.events.append(("end", tag))
        if not self.stack or self.stack[-1] != tag:
            self.errors.append("Mismatched closing tag: " + tag)
        else:
            self.stack.pop()

    def handle_data(self, data):
        if self.stack and self.stack[-1] in ("style", "script"):
            self.events.append(("literal", data))
        else:
            self.visible.append(data)
            self.prose.append(data)
            if re.search(r"<[A-Za-z/!]", data):
                self.errors.append("Incomplete markup")

    def handle_entityref(self, name):
        self.prose.append(unescape("&" + name + ";"))
        if name + ";" not in html5:
            self.visible.append("&" + name)

    def handle_charref(self, name):
        self.prose.append(unescape("&#" + name + ";"))

    def handle_pi(self, data):
        self.events.append(("instruction", data))

    def handle_decl(self, decl):
        self.events.append(("declaration", decl))

    def handle_comment(self, data):
        self.events.append(("comment", data))


def markup_pair(source: str, target: str, mode: str):
    """Return signatures only for explicit HTML or a recognized HTML tag."""
    if mode == "none" or (mode == "auto" and not HTML_TAG.search(source + target)):
        return None
    return Markup(source), Markup(target)


def visible_text(markup: Markup) -> str:
    """Entities and attribute ampersands cannot introduce menu mnemonics."""
    return "".join(markup.visible)
