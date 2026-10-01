# this_file: tests/translate/test_json_rescue.py
"""Flat JSON translation: repeated texts, fallback models, and the rescue of
items that fail their checks (alone, by paragraph, with masked markup).

No endpoint is called: fake ``request(system, payload)`` routes stand in for
the OpenAI transport and record what they are sent.
"""

import json
from pathlib import Path

import pytest

from vexy_localizzy.translate import json_file, json_request
from vexy_localizzy.translate.engine import EngineSpec
from vexy_localizzy.translate.json_file import distinct_rows, translate_json_file
from vexy_localizzy.translate.json_request import (
    MASK_RULES,
    Rejected,
    translate_checked,
)
from vexy_localizzy.translate.json_rescue import (
    mask,
    rescue_item,
    split_paragraphs,
    unmask,
)
from vexy_localizzy.translate.provider_errors import ModelResponse, ProviderUnavailable

SPEC = EngineSpec(endpoint="http://localhost:1/v1", models=("m1", "m2"))
TAGS = ("<b>", "</b>", "<i>", "</i>")


def write(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rows_of(payload: str) -> list[dict]:
    return json.loads(payload.split("\n\nItems:\n", 1)[1])


def reply(rows: list[dict], translate, model: str = "fake-model") -> ModelResponse:
    items = [
        {"id": r["id"], "text": translate(r["text"])}
        | ({"title": translate(r["title"])} if "title" in r else {})
        for r in rows
    ]
    return ModelResponse(f"<output>{json.dumps(items)}</output>", model)


class Route:
    """A fake transport: translates with ``translate`` and records every call."""

    def __init__(self, translate=str.upper, model="fake-model", down=False):
        self.translate, self.model, self.down = translate, model, down
        self.calls: list[tuple[str, list[dict]]] = []

    def __call__(self, system: str, payload: str) -> ModelResponse:
        rows = rows_of(payload)
        self.calls.append((system, rows))
        if self.down:
            raise ProviderUnavailable("http:503")
        return reply(rows, self.translate, self.model)

    @property
    def ids(self) -> list[list[str]]:
        return [[row["id"] for row in rows] for _, rows in self.calls]

    @property
    def texts(self) -> list[str]:
        return [row["text"] for _, rows in self.calls for row in rows]


def run(source: Path, out: Path, request, **options) -> dict:
    options = {"batch_size": 1, "workers": 1} | options
    return translate_json_file(
        source, out, spec=SPEC, target_lang="pl", request=request, **options
    )


def no_tags(text: str) -> str:
    """A translation that loses every tag: it always fails the markup check."""
    for tag in TAGS:
        text = text.replace(tag, "")
    return text.upper()


def no_tags_when_long(text: str) -> str:
    """Loses the tags of a text with several paragraphs, keeps them in one."""
    return no_tags(text) if "\n\n" in text else text.upper()


def tokens_only(text: str) -> str:
    """Keeps numbered tokens, loses real tags: only masked markup survives."""
    return no_tags(text)


# Repeated texts


def test_distinct_rows_when_texts_repeat_then_first_key_leads_the_others():
    rows = [
        {"id": "a", "text": "Same"},
        {"id": "b", "text": "Other"},
        {"id": "c", "text": "Same"},
        {"id": "d", "text": "Same"},
    ]
    kept, twins = distinct_rows(rows)
    assert [row["id"] for row in kept] == ["a", "b"], "one row per distinct text"
    assert twins == {"a": ["c", "d"]}, twins
    assert distinct_rows([]) == ([], {}), "no rows, nothing to send"


def test_distinct_rows_when_titled_then_every_row_is_its_own_item():
    rows = [
        {"id": "T1", "text": "Same", "title": "T1"},
        {"id": "T2", "text": "Same", "title": "T2"},
    ]
    assert distinct_rows(rows) == (rows, {}), "a title makes the item distinct"


def test_translate_json_file_when_texts_repeat_then_each_distinct_text_sent_once(
    tmp_path,
):
    source = write(
        tmp_path / "help.json", {"a": "Same", "b": "Other", "c": "Same", "d": "Same"}
    )
    out, route = tmp_path / "help_pl.json", Route()
    summary = run(source, out, route)
    assert route.ids == [["a"], ["b"]], "a repeated text is requested once"
    assert (summary["requested"], summary["reused"]) == (2, 2), summary
    assert read(out) == {"a": "SAME", "b": "OTHER", "c": "SAME", "d": "SAME"}, (
        "the translation is written under every key that has the text"
    )
    items = read(tmp_path / "help_pl.localizzy.json")["items"]
    assert list(items) == ["a", "b", "c", "d"], "the sidecar lists every key"
    assert items["c"] == items["a"], "a twin carries the same provenance"


def test_translate_json_file_when_repeated_text_fails_then_every_key_waits(tmp_path):
    source = write(tmp_path / "help.json", {"a": "Same", "b": "Other", "c": "Same"})
    out = tmp_path / "help_pl.json"

    def flaky(system, payload):
        rows = rows_of(payload)
        if rows[0]["text"] == "Same":
            raise ProviderUnavailable("http:503")
        return reply(rows, str.upper)

    summary = run(source, out, flaky)
    assert not summary["complete"] and not out.exists(), summary
    assert set(read(tmp_path / "help_pl.partial.json")) == {"b"}, "a and c both wait"
    route = Route()
    assert run(source, out, route)["complete"], "the resumed run completes"
    assert route.ids == [["a"]], "resume asks for the repeated text once"
    assert read(out)["c"] == "SAME", read(out)


def test_translate_json_file_when_new_key_repeats_a_done_text_then_not_requested(
    tmp_path,
):
    source = write(tmp_path / "help.json", {"a": "Same"})
    out = tmp_path / "help_pl.json"
    assert run(source, out, Route())["complete"], "first run"
    write(source, {"a": "Same", "b": "Same", "c": "New"})
    route = Route()
    summary = run(source, out, route)
    assert route.ids == [["c"]], "b reuses the translation of a"
    assert summary["reused"] == 1 and read(out)["b"] == "SAME", summary


def test_translate_json_file_when_titles_differ_for_one_text_then_each_requested(
    tmp_path,
):
    source = write(tmp_path / "tips.json", {"Open": "Same", "Save": "Same"})
    out, route = tmp_path / "tips_pl.json", Route()
    summary = run(source, out, route, titles=True)
    assert route.ids == [["Open"], ["Save"]], "each title needs its own translation"
    assert summary["reused"] == 0 and read(out) == {"OPEN": "SAME", "SAVE": "SAME"}, (
        summary
    )


# Fallback models


def routes_by_model(monkeypatch, **routes):
    """Make ``json_file`` build its transports from ``routes`` (model name → route)."""
    monkeypatch.setattr(
        json_file, "openai_request", lambda spec: routes[spec.models[0]]
    )


def test_translate_checked_when_first_route_down_then_next_route_answers():
    down, good = Route(down=True), Route(model="m2-served")
    rows = [{"id": "a", "text": "One"}]
    got, model = translate_checked([down, good], "rules", rows, {}, lambda got: [])
    assert (got["a"]["text"], model) == ("ONE", "m2-served"), got
    assert len(down.calls) == 1, "an outage is not retried on the same model"


def test_translate_checked_when_answer_rejected_then_next_route_tried():
    bad, good = Route(no_tags), Route(model="m2-served")
    rows = [{"id": "a", "text": "<b>One</b>"}]
    check = lambda got: [] if "<B>" in got["a"]["text"] else ["a: TAG-MISMATCH"]  # noqa: E731
    got, model = translate_checked([bad, good], "rules", rows, {}, check)
    assert model == "m2-served" and len(bad.calls) == 1, "one rejected answer per model"


def test_translate_checked_when_every_route_rejected_then_rejected_raised():
    rows = [{"id": "a", "text": "<b>One</b>"}]
    with pytest.raises(Rejected, match="TAG-MISMATCH"):
        translate_checked(
            [Route(), Route()], "rules", rows, {}, lambda got: ["a: TAG-MISMATCH"]
        )


def test_translate_checked_when_every_route_down_then_outage_raised():
    with pytest.raises(ProviderUnavailable):
        translate_checked(
            [Route(down=True), Route(down=True)],
            "rules",
            [{"id": "a", "text": "One"}],
            {},
            lambda got: [],
        )
    with pytest.raises(ValueError, match="at least one"):
        translate_checked([], "rules", [{"id": "a", "text": "One"}], {}, lambda g: [])


def test_translate_checked_when_one_rejects_and_one_is_down_then_rejected_raised():
    with pytest.raises(Rejected):
        translate_checked(
            [Route(), Route(down=True)],
            "rules",
            [{"id": "a", "text": "One"}],
            {},
            lambda got: ["a: TAG-MISMATCH"],
        )


def test_translate_json_file_when_first_model_down_then_fallback_fills_the_file(
    tmp_path, monkeypatch
):
    down, good = Route(down=True), Route(model="m2-served")
    routes_by_model(monkeypatch, m1=down, m2=good)
    source = write(tmp_path / "help.json", {"a": "Alpha"})
    out = tmp_path / "help_pl.json"
    summary = translate_json_file(source, out, spec=SPEC, target_lang="pl")
    assert summary["complete"] and read(out) == {"a": "ALPHA"}, summary
    sidecar = read(tmp_path / "help_pl.localizzy.json")
    assert sidecar["items"]["a"]["model"] == "m2-served", "the answering model"
    assert (sidecar["model"], sidecar["fallback_models"]) == ("m1", ["m2"]), sidecar


def test_translate_json_file_when_first_model_rejected_by_qa_then_fallback_used(
    tmp_path, monkeypatch
):
    lossy, good = Route(no_tags), Route(model="m2-served")
    routes_by_model(monkeypatch, m1=lossy, m2=good)
    source = write(tmp_path / "help.json", {"a": "Press <b>OK</b>"})
    out = tmp_path / "help_pl.json"
    summary = translate_json_file(source, out, spec=SPEC, target_lang="pl")
    assert summary["complete"] and read(out) == {"a": "PRESS <B>OK</B>"}, summary
    assert (len(lossy.calls), len(good.calls)) == (1, 1), "one request per model"


def test_translate_json_file_when_first_model_malformed_then_fallback_used(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(json_request.time, "sleep", lambda _: None)
    calls = []

    def garbled(system, payload):
        calls.append(payload)
        return ModelResponse("not json", "m1")

    routes_by_model(monkeypatch, m1=garbled, m2=Route(model="m2-served"))
    source = write(tmp_path / "help.json", {"a": "Alpha"})
    summary = translate_json_file(
        source, tmp_path / "help_pl.json", spec=SPEC, target_lang="pl"
    )
    assert summary["complete"] and len(calls) == json_request.MAX_ATTEMPTS, summary


# Splitting and masking


@pytest.mark.parametrize(
    "text",
    [
        "",
        "One paragraph.",
        "First.\n\nSecond.\n \n\nThird.",
        "  Indented.  \n\n\tTabbed.\n",
        "Intro.\n\n<pre>code\n\nmore code</pre>\n\nOutro.",
        "Before <PRE class='x'>a\n\nb</PRE > after.\n\nNext.",
        "\n\n",
    ],
)
def test_split_paragraphs_when_joined_then_text_is_unchanged(text):
    pieces = split_paragraphs(text)
    assert "".join(piece for piece, _ in pieces) == text, pieces
    assert all(piece.strip() == piece and piece for piece, send in pieces if send), (
        "a paragraph to translate has no edge whitespace and is not empty"
    )


def test_split_paragraphs_when_blank_lines_and_pre_then_paragraphs_and_block():
    pieces = split_paragraphs("Intro.\n\n<pre>code\n\nmore</pre>\n\nOne.\n\nTwo.")
    assert [piece for piece, send in pieces if send] == ["Intro.", "One.", "Two."]
    assert ("<pre>code\n\nmore</pre>", False) in pieces, "a pre block is kept verbatim"
    assert split_paragraphs("") == [], "an empty text has no pieces"


def test_mask_when_markup_then_numbered_tokens_and_exact_restore():
    text = 'See <a href="x?a=1&b=2">the <b>docs</b></a>, run `make all` or [go](u/v).'
    masked, markup = mask(text)
    assert masked == "See [[1]]the [[2]]docs[[3]][[4]], run [[5]] or [go][[6]].", masked
    assert markup[0] == '<a href="x?a=1&b=2">' and markup[4:] == ["`make all`", "(u/v)"]
    assert unmask(masked, markup) == text, "restoring gives the source markup back"
    assert unmask("[[2]]x[[3]] [[1]]y[[4]] [[6]] [[5]]", markup).startswith("<b>x</b>")
    assert mask("Plain text.") == ("Plain text.", []), "nothing to mask"


@pytest.mark.parametrize(
    "translated",
    ["[[1]]x", "[[1]]x[[2]][[2]]", "[[1]]x[[2]] [[3]]", "x", "[[1]]x[[2]][[02]]"],
)
def test_unmask_when_token_missing_repeated_or_unknown_then_rejected(translated):
    with pytest.raises(Rejected, match="token"):
        unmask(translated, ["<b>", "</b>"])


def test_mask_when_text_already_holds_a_token_then_rejected():
    with pytest.raises(Rejected, match="already"):
        mask("Type [[1]] and <b>go</b>.")


# Rescue


def ask_with(route):
    return json_request.Ask(routes=[route], system="rules", glossary=None)


def test_rescue_item_when_alone_passes_then_whole():
    route = Route()
    row = {"id": "a", "text": "Press <b>OK</b>.\n\nDone."}
    item, model, path = rescue_item(row, ask_with(route), alone=True)
    assert (item["text"], path) == ("PRESS <B>OK</B>.\n\nDONE.", "whole"), item
    assert route.ids == [["a"]] and model == "fake-model", route.ids


def test_rescue_item_when_whole_text_fails_then_paragraphs_translated_separately():
    route = Route(no_tags_when_long)
    row = {
        "id": "a",
        "text": "Press <b>OK</b>.\n\n<pre>x\n\ny</pre>\n\n  Then <i>go</i>.",
    }
    item, _, path = rescue_item(row, ask_with(route), alone=True)
    assert path == "paragraphs", "no paragraph needed masking"
    assert item["text"] == "PRESS <B>OK</B>.\n\n<pre>x\n\ny</pre>\n\n  THEN <I>GO</I>."
    assert route.texts == [row["text"], "Press <b>OK</b>.", "Then <i>go</i>."], (
        "the pre block is never sent, paragraphs go one per request"
    )


def test_rescue_item_when_paragraph_fails_then_markup_masked_and_restored():
    route = Route(tokens_only)
    row = {"id": "a", "text": "Plain start.\n\nPress <b>OK</b> now."}
    item, _, path = rescue_item(row, ask_with(route), alone=False)
    assert path == "masked" and item["text"] == "PLAIN START.\n\nPRESS <b>OK</b> NOW."
    masked_system, masked_rows = route.calls[-1]
    assert masked_rows == [{"id": "a#2", "text": "Press [[1]]OK[[2]] now."}], (
        masked_rows
    )
    assert masked_system == "rules" + MASK_RULES and "exactly once" in MASK_RULES, (
        "the prompt says each token must appear exactly once"
    )
    assert route.calls[0][0] == "rules", "plain requests keep the plain prompt"


def test_rescue_item_when_single_paragraph_already_tried_then_masked_at_once():
    route = Route(tokens_only)
    row = {"id": "a", "text": "Press <b>OK</b> now."}
    item, _, path = rescue_item(row, ask_with(route), alone=False)
    assert path == "masked" and item["text"] == "PRESS <b>OK</b> NOW.", item
    assert len(route.calls) == 1, "the same failing request is not sent twice"


def test_rescue_item_when_model_drops_a_token_then_rejected():
    route = Route(lambda text: no_tags(text).replace("[[2]]", ""))
    row = {"id": "a", "text": "Press <b>OK</b> now."}
    with pytest.raises(Rejected, match="token"):
        rescue_item(row, ask_with(route), alone=False)


def test_rescue_item_when_nothing_to_mask_then_rejected():
    route = Route()
    with pytest.raises(Rejected, match="no markup"):
        rescue_item({"id": "a", "text": "Plain."}, ask_with(route), alone=False)
    assert route.calls == [], "masking nothing would repeat the request that failed"


def test_rescue_item_when_reassembled_item_fails_its_checks_then_rejected():
    def swapped(text):
        text = no_tags(text).replace("[[1]]", "@").replace("[[2]]", "[[1]]")
        return text.replace("@", "[[2]]")

    route = Route(swapped)
    row = {"id": "a", "text": "Press <b>OK</b> now."}
    with pytest.raises(Rejected, match="TAG-"):
        rescue_item(row, ask_with(route), alone=False)


def test_rescue_item_when_text_is_one_pre_block_then_kept_without_a_request():
    route = Route()
    row = {"id": "a", "text": "<pre>x = 1\n\ny = 2</pre>\n"}
    item, model, path = rescue_item(row, ask_with(route), alone=False)
    assert (item, model, path) == ({"text": row["text"]}, None, "paragraphs"), item
    assert route.calls == [], "a pre block is never sent"


def test_rescue_item_when_several_models_answer_then_all_are_named():
    first = Route(no_tags, model="m1-served")
    second = Route(model="m2-served")
    ask = json_request.Ask(routes=[first, second], system="rules")
    row = {"id": "a", "text": "Plain start.\n\nPress <b>OK</b> now."}
    item, model, path = rescue_item(row, ask, alone=False)
    assert (model, path) == ("m1-served, m2-served", "paragraphs"), (model, path)
    assert item["text"] == "PLAIN START.\n\nPRESS <B>OK</B> NOW.", item


def test_rescue_item_when_provider_is_down_then_outage_raised_without_splitting():
    route = Route(down=True)
    row = {"id": "a", "text": "One.\n\nTwo."}
    with pytest.raises(ProviderUnavailable):
        rescue_item(row, ask_with(route), alone=True)
    assert len(route.calls) == 1, "an outage is not a reason to split the item"


def test_rescue_item_when_titled_then_title_translated_as_its_own_piece():
    route = Route(no_tags_when_long)
    row = {"id": "Tip", "title": "Tip", "text": "Press <b>OK</b>.\n\nDone."}
    item, _, path = rescue_item(row, ask_with(route), alone=False)
    assert item == {"title": "TIP", "text": "PRESS <B>OK</B>.\n\nDONE."}, item
    assert path == "paragraphs" and route.texts[0] == "Tip", route.texts


# The whole run


ARTICLE = "Press <b>OK</b>.\n\nThen <i>go</i>."


def test_translate_json_file_when_item_fails_whole_then_filled_by_paragraphs(
    tmp_path,
):
    source = write(
        tmp_path / "help.json", {"long": ARTICLE, "short": "Plain", "twin": ARTICLE}
    )
    out, route = tmp_path / "help_pl.json", Route(no_tags_when_long)
    summary = run(source, out, route, batch_size=5)
    assert summary["complete"] and summary["failed_batches"] == 1, summary
    assert (summary["rescued"], summary["reused"]) == (2, 1), summary
    assert read(out) == {
        "long": "PRESS <B>OK</B>.\n\nTHEN <I>GO</I>.",
        "short": "PLAIN",
        "twin": "PRESS <B>OK</B>.\n\nTHEN <I>GO</I>.",
    }, "the twin of a rescued item is filled too"
    items = read(tmp_path / "help_pl.localizzy.json")["items"]
    assert {key: item["path"] for key, item in items.items()} == {
        "long": "paragraphs",
        "short": "whole",
        "twin": "paragraphs",
    }, "the sidecar says which path filled each item"
    assert route.ids == [
        ["long", "short"],
        ["long"],
        ["long#0"],
        ["long#2"],
        ["short"],
    ], "the batch, then each item alone, and the failing one by paragraph"


def test_translate_json_file_when_single_item_batch_rejected_then_not_retried_alone(
    tmp_path,
):
    source = write(tmp_path / "help.json", {"a": "Press <b>OK</b> now."})
    out, route = tmp_path / "help_pl.json", Route(tokens_only)
    summary = run(source, out, route)
    assert summary["complete"] and read(out) == {"a": "PRESS <b>OK</b> NOW."}, summary
    assert route.ids == [["a"], ["a#0"]], "batch, then the masked paragraph"
    sidecar = read(tmp_path / "help_pl.localizzy.json")
    assert sidecar["items"]["a"]["path"] == "masked", sidecar


def test_translate_json_file_when_item_never_passes_then_out_untouched_and_exit_state(
    tmp_path,
):
    source = write(tmp_path / "help.json", {"bad": "Press <b>OK</b>.", "ok": "Plain"})
    out = write(tmp_path / "help_pl.json", {"old": "kept"})
    before = out.read_bytes()
    route = Route(lambda text: no_tags(text).replace("[[1]]", ""))
    summary = run(source, out, route)
    assert not summary["complete"] and summary["rescued"] == 0, summary
    assert out.read_bytes() == before, "OUT is untouched until every item is done"
    assert set(read(tmp_path / "help_pl.partial.json")) == {"ok"}, "the rest is kept"
    assert run(source, out, Route())["complete"], "a later run resumes by key"
    assert read(out) == {"bad": "PRESS <B>OK</B>.", "ok": "PLAIN"}, read(out)


def test_translate_json_file_when_rescue_off_then_failed_items_are_not_retried(
    tmp_path,
):
    source = write(tmp_path / "help.json", {"a": ARTICLE, "b": "Plain"})
    out, route = tmp_path / "help_pl.json", Route(no_tags_when_long)
    summary = run(source, out, route, batch_size=5, rescue=False)
    assert not summary["complete"] and summary["rescued"] == 0, summary
    assert route.ids == [["a", "b"]], "one request, as before"
    assert (
        not (tmp_path / "help_pl.partial.json").exists()
        or read(tmp_path / "help_pl.partial.json") == {}
    ), "one failing item rejects its whole batch"


def test_translate_json_file_when_provider_down_then_items_retried_alone_only(
    tmp_path,
):
    source = write(tmp_path / "help.json", {"a": "One.\n\nTwo.", "b": "Plain"})
    out, route = tmp_path / "help_pl.json", Route(down=True)
    summary = run(source, out, route, batch_size=5)
    assert not summary["complete"] and summary["failed_batches"] == 1, summary
    assert sorted(route.ids, key=len) == [["a"], ["b"], ["a", "b"]], (
        "each item is retried alone; an outage never leads to paragraph requests"
    )


def test_translate_json_file_when_titles_item_rescued_then_title_is_the_key(tmp_path):
    source = write(tmp_path / "tips.json", {"Tip": ARTICLE})
    out, route = tmp_path / "tips_pl.json", Route(no_tags_when_long)
    summary = run(source, out, route, titles=True)
    assert summary["complete"], summary
    assert read(out) == {"TIP": "PRESS <B>OK</B>.\n\nTHEN <I>GO</I>."}, read(out)


def test_translate_json_file_when_one_item_and_it_passes_then_path_is_whole(tmp_path):
    source = write(tmp_path / "help.json", {"a": "Alpha"})
    out = tmp_path / "help_pl.json"
    summary = run(source, out, Route())
    assert summary["complete"] and (summary["rescued"], summary["reused"]) == (0, 0)
    assert read(tmp_path / "help_pl.localizzy.json")["items"]["a"]["path"] == "whole"


def test_translate_json_file_when_source_empty_then_complete_without_requests(tmp_path):
    source = write(tmp_path / "help.json", {})
    route = Route()
    summary = run(source, tmp_path / "help_pl.json", route)
    assert summary["complete"] and route.calls == [], summary
    assert (summary["requested"], summary["rescued"], summary["reused"]) == (0, 0, 0)
