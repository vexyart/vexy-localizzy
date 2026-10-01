# this_file: tests/editorial/test_editorial_review.py
"""The reviewer: prompt, resume identity, parsing, retries and the candidates file."""

import json

import pytest
from editorial_fixtures import FakeEndpoint, glossary, ts, write_json

from vexy_localizzy.editorial import review_request
from vexy_localizzy.editorial.candidates import kept_corrections, review_catalog
from vexy_localizzy.editorial.review_prompt import (
    DEFAULT_PRODUCT,
    batch_id,
    language_name,
    parse_corrections,
    system_prompt,
    user_message,
)
from vexy_localizzy.editorial.review_request import review_batch

MESSAGES = [
    "<source>Open</source><translation>Ouvrir</translation>",
    "<source>Kerning</source><translation>Approche</translation>",
    '<source>Gone</source><translation type="vanished">Parti</translation>',
    '<source>New</source><translation type="unfinished"></translation>',
]


def _catalog(tmp_path):
    path = tmp_path / "app_fr.ts"
    path.write_text(ts(MESSAGES), encoding="utf-8")
    return path


def _review(tmp_path, endpoint, **options):
    options = {"model": "m", "request": endpoint, "sleep": lambda _: None} | options
    return review_catalog(_catalog(tmp_path), "fr", tmp_path / "c.jsonl", **options)


def _no_sleep(_):
    return None


def test_user_message_when_language_named_then_prompt_carries_the_name():
    user = user_message([{"id": "x"}], {}, "Polish")
    assert "(English: Polish)" in user and "{name}" not in user, user


def test_system_prompt_when_product_given_then_named_and_neutral_by_default():
    named = system_prompt("French", "a professional font editor", "")
    assert "French localization of a professional font editor." in named, named
    neutral = system_prompt("French", DEFAULT_PRODUCT, "Use vous.")
    assert DEFAULT_PRODUCT in neutral, "neutral default product"
    assert neutral.endswith("Style sheet:\nUse vous."), "style sheet appended"


def test_language_name_when_known_or_unknown_then_display_name_or_code():
    assert language_name("fr_FR") == "French (France)", "region named"
    assert language_name("xx-bogus") == "xx-bogus", "unknown code kept"


def test_batch_id_when_model_prompt_or_terms_change_then_id_changes():
    rows = [{"id": "x", "source": "Open", "current": "Ouvrir"}]
    base = batch_id(rows, model="m1", system="s", terms={"a": "b"})
    assert base == batch_id(rows, model="m1", system="s", terms={"a": "b"}), "stable"
    assert base != batch_id(rows, model="m2", system="s", terms={"a": "b"}), "model"
    assert base != batch_id(rows, model="m1", system="s2", terms={"a": "b"}), "prompt"
    assert base != batch_id(rows, model="m1", system="s", terms={"a": "c"}), "terms"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("<output>[]</output>", []),
        ('Sure.\n<output>\n```json\n[{"id": "x"}]\n```\n</output>', [{"id": "x"}]),
        ('[{"id": "y"}]', [{"id": "y"}]),
        ('<output>[{"id": "z"}]', [{"id": "z"}]),
    ],
)
def test_parse_corrections_when_wrapped_then_array_returned(text, expected):
    assert parse_corrections(text) == expected, text


def test_parse_corrections_when_not_an_array_then_refused():
    with pytest.raises(ValueError, match="not a JSON array"):
        parse_corrections('<output>{"id": "x"}</output>')


def test_review_batch_when_endpoint_fails_twice_then_third_attempt_wins():
    endpoint = FakeEndpoint(fail=2)
    delays = []
    corrections, model = review_batch(
        endpoint, "sys", [{"id": "x"}], {}, "French", sleep=delays.append
    )
    assert (corrections, model) == ([], "fake-model"), "third reply used"
    assert len(endpoint.calls) == 3 and len(delays) == 2, (endpoint.calls, delays)


def test_review_batch_when_every_attempt_fails_then_runtime_error():
    endpoint = FakeEndpoint(reply=lambda user: "not json")
    with pytest.raises(RuntimeError, match="batch failed after 3 attempts"):
        review_batch(endpoint, "sys", [{"id": "x"}], {}, "French", sleep=_no_sleep)


def test_kept_corrections_when_unknown_empty_or_repeated_ids_then_dropped():
    rows = [{"id": "a", "context": "C", "source": "Open", "current": "Ouvrir"}]
    corrections = [
        {"id": "a", "revised": "Ouvrez"},
        {"id": "a", "revised": "Ouvre"},
        {"id": "b", "revised": "x"},
        {"id": "a", "revised": ""},
        "junk",
    ]
    kept, dropped = kept_corrections(corrections, rows)
    assert [c["revised"] for c in kept] == ["Ouvrez"], "first per id wins"
    assert kept[0]["before"] == "Ouvrir" and kept[0]["source"] == "Open", kept
    assert dropped == 4, dropped


def test_review_catalog_when_vanished_or_untranslated_then_counted_not_sent(tmp_path):
    endpoint = FakeEndpoint()
    summary = _review(tmp_path, endpoint)
    sent = [row["source"] for row in endpoint.items()]
    assert sent == ["Open", "Kerning"], sent
    assert summary["left_out"] == {"vanished": 1, "variants": 0, "untranslated": 1}, (
        summary
    )
    assert summary["reviewed"] == 1 and summary["failed"] == 0, summary


def test_review_catalog_when_model_answers_then_record_carries_before_and_source(
    tmp_path,
):
    answer = [
        {"id": "Main.open", "revised": "Ouvrez", "reason": "r", "family": "style"}
    ]
    endpoint = FakeEndpoint(reply=lambda user: f"<output>{json.dumps(answer)}</output>")
    _review(tmp_path, endpoint)
    record = json.loads((tmp_path / "c.jsonl").read_text("utf-8").splitlines()[0])
    assert record["model"] == "fake-model" and record["dropped"] == 0, record
    assert (
        record["corrections"][0] | {"before": "Ouvrir", "source": "Open"}
        == (record["corrections"][0])
    ), "the reviewed text travels with the correction"


def test_review_catalog_when_rerun_unchanged_then_batches_skipped(tmp_path):
    _review(tmp_path, FakeEndpoint())
    endpoint = FakeEndpoint()
    summary = _review(tmp_path, endpoint)
    assert endpoint.calls == [] and summary["already_reviewed"] == 1, summary


@pytest.mark.parametrize(
    "change",
    [
        {"model": "m2"},
        {"product": "a professional font editor"},
        {"style": "Use vous."},
    ],
)
def test_review_catalog_when_model_product_or_style_change_then_reviewed_again(
    tmp_path, change
):
    _review(tmp_path, FakeEndpoint())
    endpoint = FakeEndpoint()
    summary = _review(tmp_path, endpoint, **change)
    assert len(endpoint.calls) == 1 and summary["already_reviewed"] == 0, change


def test_review_catalog_when_glossary_terms_change_then_reviewed_again(tmp_path):
    first = glossary(tmp_path / "a.tmx", ("Kerning", "Crénage"))
    second = glossary(tmp_path / "b.tmx", ("Kerning", "Approche"))
    endpoint = FakeEndpoint()
    _review(tmp_path, endpoint, glossaries=[first])
    assert "Crénage" in endpoint.calls[0][1], "relevant terms are sent"
    again = FakeEndpoint()
    _review(tmp_path, again, glossaries=[second])
    assert len(again.calls) == 1, "new terms review the batch again"


def test_review_catalog_when_batch_fails_then_counted_and_not_recorded(tmp_path):
    summary = _review(tmp_path, FakeEndpoint(fail=3))
    assert summary["failed"] == 1 and summary["reviewed"] == 0, summary
    assert (tmp_path / "c.jsonl").read_text("utf-8") == "", "no record for a failure"


def test_review_catalog_when_limit_then_only_first_batches(tmp_path):
    endpoint = FakeEndpoint()
    summary = _review(tmp_path, endpoint, batch_size=1, limit=1)
    assert len(endpoint.calls) == 1 and summary["batches"] == 2, summary


def test_review_catalog_when_json_file_then_units_from_both_files(tmp_path):
    en = write_json(tmp_path / "en.json", {"a": "Alpha"})
    fr = write_json(tmp_path / "fr.json", {"a": "Alfa"})
    endpoint = FakeEndpoint()
    review_catalog(
        fr,
        "fr",
        tmp_path / "c.jsonl",
        model="m",
        request=endpoint,
        source_json=en,
        sleep=_no_sleep,
    )
    assert endpoint.items() == [
        {"id": "a", "context": "json", "source": "Alpha", "current": "Alfa"}
    ], endpoint.items()


def test_endpoint_request_when_key_missing_then_refused(monkeypatch):
    pytest.importorskip("openai")
    monkeypatch.delenv("EDITORIAL_TEST_KEY", raising=False)
    with pytest.raises(ValueError, match="EDITORIAL_TEST_KEY"):
        review_request.endpoint_request(
            "http://localhost/v1",
            "m",
            api_key_env="EDITORIAL_TEST_KEY",
            temperature=0.1,
            timeout=10,
        )


def test_endpoint_request_when_temperature_out_of_range_then_refused(monkeypatch):
    pytest.importorskip("openai")
    monkeypatch.setenv("EDITORIAL_TEST_KEY", "k")
    with pytest.raises(ValueError, match="Temperature"):
        review_request.endpoint_request(
            "http://localhost/v1",
            "m",
            api_key_env="EDITORIAL_TEST_KEY",
            temperature=3,
            timeout=10,
        )


def _install_transport(monkeypatch, handle):
    """Route the real SDK through ``handle`` (an httpx request → response function)."""
    openai = pytest.importorskip("openai")
    httpx = pytest.importorskip("httpx")
    original = openai.OpenAI
    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: original(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handle))
        ),
    )
    monkeypatch.setenv("EDITORIAL_TEST_KEY", "k")
    return review_request.endpoint_request(
        "http://localhost/v1",
        "m",
        api_key_env="EDITORIAL_TEST_KEY",
        temperature=0.3,
        timeout=10,
    )


def _completion(content: str, model: str = "served-model"):
    httpx = pytest.importorskip("httpx")
    choice = {
        "index": 0,
        "finish_reason": "stop",
        "message": {"role": "assistant", "content": content},
    }
    body = {"id": "t", "object": "chat.completion", "created": 0, "model": model}
    return httpx.Response(200, json=body | {"choices": [choice]})


def test_endpoint_request_when_called_then_model_temperature_and_messages_sent(
    monkeypatch,
):
    sent = []

    def handle(request):
        sent.append(json.loads(request.content))
        return _completion("<output>[]</output>")

    response = _install_transport(monkeypatch, handle)("the rules", "the items")
    assert response.content == "<output>[]</output>", response
    assert response.reported_model == "served-model", "the served model is kept"
    body = sent[0]
    assert (body["model"], body["temperature"]) == ("m", 0.3), body
    assert [m["content"] for m in body["messages"]] == ["the rules", "the items"], body


def test_endpoint_request_when_provider_fails_then_provider_unavailable(monkeypatch):
    from vexy_localizzy.translate.provider_errors import ProviderUnavailable

    httpx = pytest.importorskip("httpx")
    request = _install_transport(
        monkeypatch, lambda _: httpx.Response(503, json={"error": "busy"})
    )
    with pytest.raises(ProviderUnavailable, match="http:503"):
        request("s", "u")


def test_review_catalog_when_scalar_has_length_variants_then_left_out_as_variants(
    tmp_path,
):
    path = tmp_path / "v_fr.ts"
    path.write_text(
        ts(
            [
                '<source>Long label</source><translation variants="yes">'
                "<lengthvariant>Libellé long</lengthvariant>"
                "<lengthvariant>Court</lengthvariant></translation>",
                "<source>Open</source><translation>Ouvrir</translation>",
            ]
        ),
        encoding="utf-8",
    )
    endpoint = FakeEndpoint()
    summary = review_catalog(
        path, "fr", tmp_path / "c.jsonl", model="m", request=endpoint, sleep=_no_sleep
    )
    assert summary["left_out"] == {"vanished": 0, "variants": 1, "untranslated": 0}, (
        summary["left_out"]
    )
    assert [r["source"] for r in endpoint.items()] == ["Open"], "variants not sent"


def _record(batch: str) -> str:
    return json.dumps({"batch": batch, "model": "m", "corrections": []})


def test_review_catalog_when_last_line_cut_off_then_dropped_and_resumed(tmp_path):
    out = tmp_path / "c.jsonl"
    _review(tmp_path, FakeEndpoint())
    complete = out.read_text("utf-8")
    out.write_text(complete + '{"batch": "half', encoding="utf-8")
    endpoint = FakeEndpoint()
    summary = _review(tmp_path, endpoint)
    assert endpoint.calls == [] and summary["already_reviewed"] == 1, summary
    assert out.read_text("utf-8") == complete, "the partial line is removed"


def test_review_catalog_when_last_line_lacks_newline_then_next_record_on_own_line(
    tmp_path,
):
    out = tmp_path / "c.jsonl"
    out.write_text(_record("other"), encoding="utf-8")
    _review(tmp_path, FakeEndpoint())
    lines = out.read_text("utf-8").splitlines()
    assert len(lines) == 2 and all(json.loads(line) for line in lines), lines


def test_review_catalog_when_middle_line_malformed_then_refused(tmp_path):
    out = tmp_path / "c.jsonl"
    out.write_text(f"{_record('a')}\nnot json\n{_record('b')}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        _review(tmp_path, FakeEndpoint())
    assert "not json" in out.read_text("utf-8"), "a damaged file is not rewritten"


@pytest.mark.parametrize("name", ["app_fr.ts", "en.json"])
def test_review_catalog_when_out_is_an_input_then_refused(tmp_path, name):
    catalog = _catalog(tmp_path)
    en = write_json(tmp_path / "en.json", {"a": "A"})
    before = catalog.read_bytes()
    with pytest.raises(ValueError, match="same file"):
        review_catalog(
            catalog,
            "fr",
            tmp_path / name,
            model="m",
            request=FakeEndpoint(),
            source_json=en,
        )
    assert catalog.read_bytes() == before, "the catalog is not touched"
