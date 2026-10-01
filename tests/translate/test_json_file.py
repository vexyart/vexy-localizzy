# this_file: tests/translate/test_json_file.py
"""Flat JSON file translation: strict replies, retries, QA rejection, resume by key.

No endpoint is called: a fake ``request(system, payload)`` stands in for the
OpenAI transport and translates the items it is sent.
"""

import json
from pathlib import Path

import pytest

from vexy_localizzy.memory.glossary import Glossary
from vexy_localizzy.translate import json_file, json_request
from vexy_localizzy.translate.engine import EngineSpec
from vexy_localizzy.translate.json_file import (
    check_outputs,
    pending_rows,
    read_source,
    translate_json_file,
)
from vexy_localizzy.translate.json_request import (
    openai_request,
    parse_items,
    system_prompt,
    translate_rows,
)
from vexy_localizzy.translate.provider_errors import ModelResponse, ProviderUnavailable

SPEC = EngineSpec(endpoint="http://localhost:1/v1", models=("test-model",))


def write(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fake(translate, fail=(), seen=None):
    """A request that translates every item with ``translate``; ids in ``fail`` raise."""

    def request(system: str, payload: str) -> ModelResponse:
        rows = json.loads(payload.split("\n\nItems:\n", 1)[1])
        if seen is not None:
            seen.extend(row["id"] for row in rows)
        if any(row["id"] in fail for row in rows):
            raise ProviderUnavailable("http:503")
        items = [
            {"id": r["id"], "text": translate(r["text"])}
            | ({"title": translate(r["title"])} if "title" in r else {})
            for r in rows
        ]
        return ModelResponse(f"<output>{json.dumps(items)}</output>", "fake-model")

    return request


def run(source: Path, out: Path, request, **options) -> dict:
    options = {"batch_size": 1, "workers": 1} | options
    return translate_json_file(
        source, out, spec=SPEC, target_lang="pl", request=request, **options
    )


@pytest.mark.parametrize(
    "items",
    [
        [{"id": "a", "text": "Un"}, {"id": "a", "text": "Deux"}],
        [{"id": "a", "text": "Un"}, {}],
        [{"id": "a", "text": {"invalid": "object"}}],
        [{"id": "a", "text": "   "}],
    ],
)
def test_parse_items_when_duplicate_or_malformed_items_then_refused(items):
    with pytest.raises(ValueError):
        parse_items(json.dumps(items), [{"id": "a", "text": "One"}])


def test_parse_items_when_fenced_or_tagged_then_parsed():
    rows = [{"id": "a", "text": "One"}]
    fenced = '```json\n[{"id": "a", "text": "Un"}]\n```'
    assert parse_items(fenced, rows)["a"]["text"] == "Un", "a code fence is stripped"
    tagged = 'Sure: <output>[{"id": "a", "text": "Un"}]</output> done'
    assert parse_items(tagged, rows)["a"]["text"] == "Un", "only <output> is read"


def test_parse_items_when_title_missing_then_refused():
    with pytest.raises(ValueError):
        parse_items(
            '[{"id": "T", "text": "x"}]', [{"id": "T", "text": "a", "title": "T"}]
        )


def test_translate_rows_when_replies_stay_malformed_then_runtime_error(monkeypatch):
    sleeps = []
    monkeypatch.setattr(json_request.time, "sleep", sleeps.append)
    calls = []

    def request(system, payload):
        calls.append(payload)
        return ModelResponse("not json", "m")

    with pytest.raises(RuntimeError, match="batch failed"):
        translate_rows(request, "rules", [{"id": "a", "text": "One"}], {})
    assert len(calls) == json_request.MAX_ATTEMPTS, "each malformed reply is retried"
    assert len(sleeps) == json_request.MAX_ATTEMPTS - 1, "no sleep after the last try"


def test_translate_rows_when_provider_unavailable_then_raised_at_once():
    calls = []

    def request(system, payload):
        calls.append(payload)
        raise ProviderUnavailable("http:429")

    with pytest.raises(ProviderUnavailable):
        translate_rows(request, "rules", [{"id": "a", "text": "One"}], {"x": "y"})
    assert len(calls) == 1, "an outage is not retried in a loop"
    assert '"x": "y"' in calls[0], "glossary terms travel in the payload"


def test_system_prompt_when_product_and_style_then_both_present_and_formatted():
    text = system_prompt(
        source_lang="en", target_lang="pl", product="a photo editor", style="Be brief."
    )
    assert "help texts for a photo editor from en into pl" in text, text
    assert text.endswith("Style sheet:\nBe brief."), text
    assert "{product}" not in text and '{"id": "<id>"' in text, "braces formatted"
    assert "Style sheet" not in system_prompt(
        source_lang="en", target_lang="pl", product="x"
    ), "no empty style section"


def test_openai_request_when_key_missing_then_value_error(monkeypatch):
    pytest.importorskip("openai")
    monkeypatch.delenv("LOCALIZZY_TEST_MISSING_KEY", raising=False)
    spec = SPEC.model_copy(update={"api_key_env": "LOCALIZZY_TEST_MISSING_KEY"})
    with pytest.raises(ValueError, match="LOCALIZZY_TEST_MISSING_KEY"):
        openai_request(spec)


def test_read_source_when_nested_values_then_value_error(tmp_path):
    with pytest.raises(ValueError):
        read_source(write(tmp_path / "s.json", {"a": {"b": "c"}}))
    with pytest.raises(FileNotFoundError):
        read_source(tmp_path / "missing.json")


def test_pending_rows_when_titles_then_title_row_and_done_skipped():
    done = {}
    rows = pending_rows({"T1": "a", "T2": "b"}, done, titles=True)
    assert rows == [
        {"id": "T1", "text": "a", "title": "T1"},
        {"id": "T2", "text": "b", "title": "T2"},
    ], rows


def test_translate_json_file_when_titles_batch_fails_then_no_gap_file_and_resume_by_key(
    tmp_path,
):
    source = write(
        tmp_path / "tips.json",
        {f"Title {n}": f"Text {n}" for n in ("one", "two", "three", "four")},
    )
    out = tmp_path / "tips_pl.json"
    pl = lambda t: f"PL {t}"  # noqa: E731
    summary = run(source, out, fake(pl, fail={"Title two"}), titles=True)
    assert not summary["complete"] and not out.exists(), (
        "a file with gaps is not written"
    )
    partial = read(tmp_path / "tips_pl.partial.json")
    assert set(partial) == {"Title one", "Title three", "Title four"}, partial

    seen = []
    assert run(source, out, fake(pl, seen=seen), titles=True)["complete"], (
        "the resumed run completes"
    )
    assert seen == ["Title two"], "resume skips done keys whatever their position"
    assert list(read(out).items()) == [
        (f"PL Title {n}", f"PL Text {n}") for n in ("one", "two", "three", "four")
    ], "titles and texts stay paired in English order"
    assert not (tmp_path / "tips_pl.partial.json").exists(), "partial file removed"


def test_translate_json_file_when_titles_file_has_gap_and_no_sidecar_then_refused(
    tmp_path,
):
    source = write(tmp_path / "tips.json", {"T1": "a", "T2": "b", "T3": "c"})
    out = write(tmp_path / "tips_pl.json", {"PL T1": "PL a", "PL T3": "PL c"})
    before = out.read_bytes()
    with pytest.raises(ValueError, match="refusing"):
        run(source, out, fake(str.upper), titles=True)
    assert out.read_bytes() == before, "the existing output is untouched"


def test_translate_json_file_when_complete_file_has_no_sidecar_then_adopted_without_calls(
    tmp_path,
):
    source = write(tmp_path / "help.json", {"a": "Alpha", "b": "Beta"})
    out = write(tmp_path / "help_pl.json", {"a": "Alfa", "b": "Beta PL"})
    seen = []
    summary = run(source, out, fake(str.upper, seen=seen))
    assert summary["complete"] and seen == [], summary
    sidecar = read(tmp_path / "help_pl.localizzy.json")
    assert {v["state"] for v in sidecar["items"].values()} == {"adopted"}, sidecar


def test_translate_json_file_when_nothing_pending_then_no_transport_needed(tmp_path):
    source = write(tmp_path / "help.json", {})
    summary = translate_json_file(
        source, tmp_path / "help_pl.json", spec=SPEC, target_lang="pl"
    )
    assert summary["complete"] and read(tmp_path / "help_pl.json") == {}, summary


def test_translate_json_file_when_translation_drops_markup_then_batch_rejected(
    tmp_path,
):
    source = write(
        tmp_path / "help.json",
        {
            "tag": "Press <b>OK</b>",
            "link": "See [docs](https://example.com/a)",
            "code": "Run `x`",
            "ok": "Plain",
        },
    )

    def lossy(text):
        return (
            text.replace("<b>", "")
            .replace("</b>", "")
            .replace("(https://example.com/a)", "(https://example.com/b)")
            .replace("`x`", "x")
            + " PL"
        )

    out = tmp_path / "help_pl.json"
    summary = run(source, out, fake(lossy))
    assert summary["failed_batches"] == 3 and not out.exists(), summary
    partial = read(tmp_path / "help_pl.partial.json")
    assert set(partial) == {"ok"}, "only the clean item is kept"
    assert partial["ok"]["model"] == "fake-model", partial
    assert partial["ok"]["state"] == "machine", partial


def test_translate_json_file_when_source_text_changes_then_only_that_key_retranslated(
    tmp_path,
):
    source = write(tmp_path / "help.json", {"a": "Alpha", "b": "Beta"})
    out = tmp_path / "help_pl.json"
    assert run(source, out, fake(str.upper))["complete"], "the first run completes"
    sidecar = read(tmp_path / "help_pl.localizzy.json")
    assert sidecar["items"]["a"]["model"] == "fake-model", sidecar
    assert sidecar["model"] == "test-model", "the requested model is recorded too"

    write(source, {"a": "Alpha rewritten", "b": "Beta"})
    seen = []
    assert run(source, out, fake(str.upper, seen=seen))["complete"], (
        "the rerun completes"
    )
    assert seen == ["a"], "a changed English paragraph is translated again"
    assert read(out)["a"] == "ALPHA REWRITTEN", read(out)


def test_translate_json_file_when_glossary_then_relevant_terms_sent(tmp_path):
    tmx = tmp_path / "terms.tmx"
    tmx.write_text(
        '<?xml version="1.0" encoding="UTF-8"?><tmx version="1.4">'
        '<header srclang="en" datatype="plaintext" segtype="phrase" adminlang="en"'
        ' o-tmf="x" creationtool="t" creationtoolversion="1"/><body>'
        '<tu tuid="term:layer"><prop type="x-status">approved</prop>'
        '<tuv xml:lang="en"><seg>layer</seg></tuv>'
        '<tuv xml:lang="pl"><seg>warstwa</seg></tuv></tu></body></tmx>',
        encoding="utf-8",
    )
    glossary = Glossary.load([tmx], source_lang="en", target_lang="pl")
    payloads = []

    def request(system, payload):
        payloads.append(payload)
        return fake(str.upper)(system, payload)

    source = write(tmp_path / "help.json", {"a": "Add a layer", "b": "Plain"})
    run(source, tmp_path / "out.json", request, glossary=glossary)
    assert '"layer": "warstwa"' in payloads[0], payloads[0]
    assert "warstwa" not in payloads[1], "only terms an item mentions are sent"


def test_openai_request_when_called_then_temperature_model_and_messages_sent(
    monkeypatch,
):
    from types import SimpleNamespace as Obj

    pytest.importorskip("openai")
    monkeypatch.setenv("LOCALIZZY_TEST_KEY", "k")
    sent = {}

    def completion(api, **kwargs):
        sent.update(kwargs)
        message = Obj(content="[]")
        return Obj(choices=[Obj(message=message)], model="served-model")

    monkeypatch.setattr(json_request, "completion_request", completion)
    spec = SPEC.model_copy(
        update={"api_key_env": "LOCALIZZY_TEST_KEY", "temperature": 0.7}
    )
    response = openai_request(spec)("rules", "payload")
    assert sent["temperature"] == 0.7 and sent["model"] == "test-model", sent
    assert [m["content"] for m in sent["messages"]] == ["rules", "payload"], sent
    assert response == ModelResponse("[]", "served-model"), "the served model is kept"


def test_check_outputs_when_out_or_its_state_files_are_inputs_then_refused(tmp_path):
    source = tmp_path / "help.json"
    with pytest.raises(ValueError, match="overwrite an input"):
        check_outputs(source, [source])
    with pytest.raises(ValueError, match="help.localizzy.json"):
        check_outputs(source, [tmp_path / "help.localizzy.json"])
    check_outputs(tmp_path / "help_pl.json", [source])


def test_translate_json_file_when_out_is_source_then_refused_untouched(tmp_path):
    source = write(tmp_path / "help.json", {"a": "Alpha"})
    before = source.read_bytes()
    with pytest.raises(ValueError, match="overwrite an input"):
        run(source, source, fake(str.upper))
    assert source.read_bytes() == before, "English is never written as the translation"
    assert not (tmp_path / "help.localizzy.json").exists(), "no sidecar either"


def test_translate_json_file_when_out_is_style_or_glossary_then_refused(tmp_path):
    source = write(tmp_path / "help.json", {"a": "Alpha"})
    style = write(tmp_path / "style.json", {})
    with pytest.raises(ValueError, match="style.json"):
        run(source, style, fake(str.upper), protected=[style])
    tmx = tmp_path / "terms.tmx"
    tmx.write_text(
        '<?xml version="1.0" encoding="UTF-8"?><tmx version="1.4">'
        '<header srclang="en" datatype="plaintext" segtype="phrase" adminlang="en"'
        ' o-tmf="x" creationtool="t" creationtoolversion="1"/><body>'
        '<tu><prop type="x-status">approved</prop><tuv xml:lang="en"><seg>a</seg>'
        '</tuv><tuv xml:lang="pl"><seg>b</seg></tuv></tu></body></tmx>',
        encoding="utf-8",
    )
    glossary = Glossary.load([tmx], source_lang="en", target_lang="pl")
    with pytest.raises(ValueError, match="terms.tmx"):
        run(source, tmx, fake(str.upper), glossary=glossary)


def test_translate_json_file_when_batch_accepted_then_saved_while_run_continues(
    tmp_path,
):
    import time

    source = write(tmp_path / "help.json", {"a": "Alpha", "b": "Beta"})
    out = tmp_path / "help_pl.json"
    partial = tmp_path / "help_pl.partial.json"
    seen_partial = []

    def request(system, payload):
        if '"id": "b"' in payload:
            deadline = time.monotonic() + 2
            while not partial.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            seen_partial.append(set(read(partial)) if partial.exists() else None)
        return fake(str.upper)(system, payload)

    assert run(source, out, request)["complete"], "both batches succeed"
    assert seen_partial == [{"a"}], "batch a reaches disk while batch b is in flight"
    assert not partial.exists(), "a complete run removes the partial file"


def test_translate_json_file_when_interrupted_then_queue_cancelled_partial_kept(
    tmp_path, monkeypatch
):
    import threading

    source = write(tmp_path / "help.json", {"a": "A", "b": "B", "c": "C"})
    out = tmp_path / "help_pl.json"
    release, seen = threading.Event(), []

    def request(system, payload):
        rows = json.loads(payload.split("\n\nItems:\n", 1)[1])
        seen.extend(row["id"] for row in rows)
        if rows[0]["id"] == "b":
            release.wait(2)
        return fake(str.upper)(system, payload)

    def interrupted(futures):
        first = next(iter(futures))
        first.result()
        yield first
        raise KeyboardInterrupt

    monkeypatch.setattr(json_file, "as_completed", interrupted)
    timer = threading.Timer(0.3, release.set)
    timer.start()
    with pytest.raises(KeyboardInterrupt):
        run(source, out, request)
    timer.join()
    assert seen == ["a", "b"], "the queued batch c is never sent"
    assert set(read(tmp_path / "help_pl.partial.json")) == {"a"}, "paid work kept"
    assert not out.exists(), "an interrupted run writes no output"


def test_translate_json_file_when_titles_collide_then_keys_requested_again(tmp_path):
    source = write(tmp_path / "tips.json", {"Open": "o", "Save": "s", "Quit": "q"})
    out = tmp_path / "tips_pl.json"
    same = lambda t: "Plik" if t in ("Open", "Save") else t.upper()  # noqa: E731
    summary = run(source, out, fake(same), titles=True)
    assert summary["title_clashes"] == ["Open", "Save"], summary
    assert set(read(tmp_path / "tips_pl.partial.json")) == {"Quit"}, "clashes dropped"
    seen = []
    summary = run(source, out, fake(str.upper, seen=seen), titles=True)
    assert seen == ["Open", "Save"], "the clashing keys are requested again"
    assert summary["complete"], summary


def test_translate_json_file_when_state_files_malformed_then_value_error(tmp_path):
    source = write(tmp_path / "help.json", {"a": "Alpha"})
    out = tmp_path / "help_pl.json"
    write(tmp_path / "help_pl.partial.json", {"a": "not an object"})
    with pytest.raises(ValueError, match="partial"):
        run(source, out, fake(str.upper))
    (tmp_path / "help_pl.partial.json").unlink()
    write(tmp_path / "help_pl.localizzy.json", {"items": ["x"]})
    with pytest.raises(ValueError, match="localizzy"):
        run(source, out, fake(str.upper))
    (tmp_path / "help_pl.localizzy.json").unlink()
    write(out, {"a": {"nested": 1}})
    with pytest.raises(ValueError, match="flat JSON object"):
        run(source, out, fake(str.upper))
