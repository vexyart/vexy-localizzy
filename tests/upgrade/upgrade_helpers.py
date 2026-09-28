# this_file: tests/upgrade/upgrade_helpers.py
"""Shared synthetic inputs for the TS upgrade tests."""

from pathlib import Path

from vexy_localizzy.memory import DirectMemory, Glossary
from vexy_localizzy.qa import validate_batch
from vexy_localizzy.translation_cache import TranslationCache
from vexy_localizzy.translation_types import TranslationResult
from vexy_localizzy.upgrade import message_refs

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "upgrade"
FRESH = FIXTURES / "fresh.ts"
APPROVED = FIXTURES / "approved.ts"


def doc(body: str, language: str = "de_DE", source: str = "en") -> bytes:
    """Wrap context XML in a TS document in lupdate's layout."""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n'
        f'<TS version="2.1" language="{language}" sourcelanguage="{source}">\n'
        f"{body}</TS>\n"
    ).encode()


def context(name: str, *messages: str) -> str:
    inner = "".join(messages)
    return f"    <context>\n        <name>{name}</name>\n{inner}    </context>\n"


def message(
    source: str,
    translation: str = "",
    *,
    unfinished: bool = False,
    extra: str = "",
    attrs: str = "",
    location: str = "",
) -> str:
    kind = ' type="unfinished"' if unfinished else ""
    loc = f"            {location}\n" if location else ""
    return (
        f"        <message{attrs}>\n{loc}            <source>{source}</source>\n{extra}"
        f"            <translation{kind}>{translation}</translation>\n        </message>\n"
    )


def direct_memory() -> DirectMemory:
    return DirectMemory.load(
        [FIXTURES / "ui-de.tmx"], source_lang="en", target_lang="de_DE"
    )


def glossary() -> Glossary:
    return Glossary.load(
        [FIXTURES / "core-de.tmx"], source_lang="en", target_lang="de_DE"
    )


class FakeEngine:
    """Records every batch; answers 'DE <source>' or fails when told to."""

    def __init__(self, fail: bool = False) -> None:
        self.batches = []
        self.fail = fail

    def __call__(self, model, batch):
        self.batches.append(batch)
        if self.fail:
            raise ValueError("synthetic failure")
        return TranslationResult(
            targets={i.id: "DE " + i.source for i in batch.items},
            requested_model=model,
            reported_model=model + "-reported",
        )


def fake_cache(path: Path, engine: FakeEngine) -> TranslationCache:
    return TranslationCache(
        path,
        models=("synthetic-model",),
        request=engine,
        endpoint_identity="synthetic",
        engine_identity="synthetic:1",
        validation_identity="upgrade-test:1",
        validate=validate_batch,
    )


def by_source(report) -> dict:
    return {m.source: m for m in report.messages}


def new_message(raw: bytes, source: str):
    """The NEW message element whose source text equals `source`."""
    return next(r for r in message_refs(raw) if r.source == source).element


def report_accounts_for_approved(report) -> bool:
    """From the report alone: ported ordinals and retired ones cover APPROVED once."""
    ported = [
        m.approved_ordinal
        for m in report.messages
        if m.approved_ordinal is not None and m.category != "shape_changed"
    ]
    retired = report.retired_ordinals
    together = ported + retired
    return len(together) == len(set(together)) and set(together) == set(
        range(report.approved.messages)
    )


FRESH_OWNED = ("location", "source", "comment", "extracomment")


def fresh_side_unchanged(fresh: bytes, new: bytes) -> int:
    """Assert bytes outside spans and FRESH-owned children are unchanged.

    Returns the number of message spans whose bytes differ.
    """
    from lxml import etree

    from vexy_localizzy.formats.ts_splice import message_spans

    a, b = message_spans(fresh), message_spans(new)
    assert len(a) == len(b), "message count changed"
    gaps_a = [fresh[x.end : y.start] for x, y in zip(a, a[1:], strict=False)]
    gaps_b = [new[x.end : y.start] for x, y in zip(b, b[1:], strict=False)]
    assert gaps_a == gaps_b, "bytes between messages changed"
    assert fresh[a[-1].end :] == new[b[-1].end :], "trailing bytes changed"
    old_refs, new_refs = message_refs(fresh), message_refs(new)
    differ = 0
    for x, y, old, now in zip(a, b, old_refs, new_refs, strict=True):
        if fresh[x.start : x.end] == new[y.start : y.end]:
            continue
        differ += 1
        assert dict(old.element.attrib) == dict(now.element.attrib), old.source
        assert old.context == now.context, old.source
        for tag in FRESH_OWNED:
            before = [etree.tostring(e, method="c14n") for e in old.element.iter(tag)]
            after = [etree.tostring(e, method="c14n") for e in now.element.iter(tag)]
            assert before == after, f"{tag} changed for {old.source!r}"
    return differ
