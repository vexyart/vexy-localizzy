# this_file: tests/editorial/test_editorial_cli.py
"""``cli.editorial``: flag parsing, exit codes and the end-to-end review → apply path."""

import json
import sys

import pytest
from editorial_fixtures import (
    FakeEndpoint,
    candidate,
    glossary,
    ts,
    units,
    write_candidates,
    write_json,
)

from vexy_localizzy.cli import editorial
from vexy_localizzy.editorial import review_request


@pytest.fixture
def catalog(tmp_path):
    path = tmp_path / "app_fr.ts"
    path.write_text(
        ts(["<source>Open</source><translation>Ouvrir</translation>"]), encoding="utf-8"
    )
    return path


@pytest.fixture
def endpoint(monkeypatch):
    """Replace the request seam; the fake proposes one correction for Main.open."""
    answer = [
        {
            "id": "Main.open",
            "revised": "Ouvrez",
            "reason": "r",
            "family": "style",
            "severity": "minor",
        }
    ]
    fake = FakeEndpoint(reply=lambda user: f"<output>{json.dumps(answer)}</output>")
    monkeypatch.setattr(review_request, "endpoint_request", lambda *a, **k: fake)
    return fake


def _exit_code(call) -> int:
    with pytest.raises(SystemExit) as raised:
        call()
    return raised.value.code


def test_review_when_model_or_endpoint_missing_then_exit_2(catalog, tmp_path):
    out = tmp_path / "c.jsonl"
    no_endpoint = _exit_code(lambda: editorial.review(catalog, "fr", out, model="m"))
    assert no_endpoint == 2, "--endpoint is required"
    no_model = _exit_code(lambda: editorial.review(catalog, "fr", out, endpoint="e"))
    assert no_model == 2, "--model is required"


@pytest.mark.parametrize(
    "flags",
    [
        {"workers": 0},
        {"batch_size": -1},
        {"limit": -1},
        {"style_file": "missing.md"},
        {"glossary_memory": "missing.tmx"},
    ],
)
def test_review_when_bad_flag_then_exit_2(catalog, tmp_path, endpoint, flags):
    call = lambda: editorial.review(  # noqa: E731
        catalog, "fr", tmp_path / "c.jsonl", model="m", endpoint="e", **flags
    )
    assert _exit_code(call) == 2, flags
    assert endpoint.calls == [], "nothing is sent on a usage error"


def test_review_when_api_key_unset_then_exit_2(catalog, tmp_path, monkeypatch, capsys):
    pytest.importorskip("openai")
    monkeypatch.delenv("EDITORIAL_TEST_KEY", raising=False)
    call = lambda: editorial.review(  # noqa: E731
        catalog,
        "fr",
        tmp_path / "c.jsonl",
        model="m",
        endpoint="http://localhost/v1",
        api_key_env="EDITORIAL_TEST_KEY",
    )
    assert _exit_code(call) == 2, "an unset key is a usage error"
    assert "EDITORIAL_TEST_KEY" in capsys.readouterr().err, "the variable is named"


def test_review_when_openai_missing_then_exit_3(catalog, tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", None)
    call = lambda: editorial.review(  # noqa: E731
        catalog, "fr", tmp_path / "c.jsonl", model="m", endpoint="http://localhost/v1"
    )
    assert _exit_code(call) == 3, "a missing extra is not a usage error"


def test_review_when_batch_fails_then_exit_1(catalog, tmp_path, monkeypatch):
    fake = FakeEndpoint(fail=99)
    monkeypatch.setattr(review_request, "endpoint_request", lambda *a, **k: fake)
    monkeypatch.setattr(review_request.time, "sleep", lambda _: None)
    call = lambda: editorial.review(  # noqa: E731
        catalog, "fr", tmp_path / "c.jsonl", model="m", endpoint="e"
    )
    assert _exit_code(call) == 1, "a failed batch is reported, re-run resumes"


def test_review_then_apply_when_accepted_then_catalog_and_ledger_written(
    catalog, tmp_path, endpoint
):
    candidates, ledger = tmp_path / "c.jsonl", tmp_path / "ledger.json"
    summary = editorial.review(
        catalog,
        "fr",
        candidates,
        model="m",
        endpoint="e",
        product="a professional font editor",
        glossary_memory=None,
    )
    assert summary["corrections"] == 1, summary
    assert "a professional font editor" in endpoint.calls[0][0], "product in prompt"
    result = editorial.apply(catalog, "fr", candidates, ledger)
    assert result["applied"] == 1, result
    assert units(catalog)["Main.open"].target == "Ouvrez", "correction written"
    change = json.loads(ledger.read_text("utf-8"))["changes"][0]
    assert (change["before"], change["after"], change["language"]) == (
        "Ouvrir",
        "Ouvrez",
        "fr",
    ), change


@pytest.mark.parametrize("flags", [{"severity": "major,typo"}, {"family": "colour"}])
def test_apply_when_unknown_filter_value_then_exit_2(catalog, tmp_path, flags):
    path = write_candidates(tmp_path / "c.jsonl", [])
    call = lambda: editorial.apply(catalog, "fr", path, tmp_path / "l.json", **flags)  # noqa: E731
    assert _exit_code(call) == 2, flags


def test_apply_when_reject_ids_given_then_those_left_unchanged(catalog, tmp_path):
    path = write_candidates(
        tmp_path / "c.jsonl", [candidate("Main.open", "Open", "Ouvrir", "Ouvrez")]
    )
    rejects = tmp_path / "rejects.txt"
    rejects.write_text("Main.open\n", encoding="utf-8")
    result = editorial.apply(
        catalog, "fr", path, tmp_path / "l.json", reject_ids=str(rejects)
    )
    assert result["applied"] == 0 and result["skipped"]["rejected"] == 1, result


def test_apply_when_duplicate_ids_then_exit_2_and_no_ledger(catalog, tmp_path):
    change = candidate("Main.open", "Open", "Ouvrir", "Ouvrez")
    path = write_candidates(tmp_path / "c.jsonl", [change], [change])
    ledger = tmp_path / "l.json"
    code = _exit_code(lambda: editorial.apply(catalog, "fr", path, ledger))
    assert code == 2, "duplicate ids are an input error"
    assert not ledger.exists(), "a refused run writes no ledger"


def test_apply_when_titles_refused_then_exit_2_and_no_ledger(tmp_path):
    en = write_json(tmp_path / "en.json", {"A": "a"})
    pl = write_json(tmp_path / "pl.json", {"PA": "pa", "PB": "pb"})
    path = write_candidates(
        tmp_path / "c.jsonl", [candidate("A", "A\n\na", "PA\n\npa", "PA2\n\npa")]
    )
    ledger = tmp_path / "ledger.json"
    call = lambda: editorial.apply(pl, "pl", path, ledger, source_json=str(en))  # noqa: E731
    assert _exit_code(call) == 2, "unpairable files are an input error"
    assert not ledger.exists(), "a refused run writes no ledger"


def test_editorial_commands_when_listed_then_review_and_apply():
    assert editorial.EDITORIAL_COMMANDS == {
        "review": editorial.review,
        "apply": editorial.apply,
    }, editorial.EDITORIAL_COMMANDS


BROKEN_TS = "<?xml version='1.0'?><TS><context><name>x</name><message>"


def test_apply_when_catalog_is_malformed_xml_then_exit_2(tmp_path, capsys):
    catalog = tmp_path / "broken.ts"
    catalog.write_text(BROKEN_TS, encoding="utf-8")
    path = write_candidates(tmp_path / "c.jsonl", [])
    call = lambda: editorial.apply(catalog, "fr", path, tmp_path / "l.json")  # noqa: E731
    assert _exit_code(call) == 2, "malformed XML is an input error"
    assert capsys.readouterr().err.startswith("error:"), "a message, not a traceback"


def test_review_when_catalog_is_malformed_xml_then_exit_2(tmp_path, endpoint):
    catalog = tmp_path / "broken.ts"
    catalog.write_text(BROKEN_TS, encoding="utf-8")
    call = lambda: editorial.review(  # noqa: E731
        catalog, "fr", tmp_path / "c.jsonl", model="m", endpoint="e"
    )
    assert _exit_code(call) == 2, "malformed XML is an input error"


@pytest.mark.parametrize(
    "severity", [("major", "minor"), ["major", "minor"], "major,minor"]
)
def test_apply_when_list_flags_are_tuples_or_lists_then_accepted(
    catalog, tmp_path, severity
):
    path = write_candidates(
        tmp_path / "c.jsonl", [candidate("Main.open", "Open", "Ouvrir", "Ouvrez")]
    )
    result = editorial.apply(
        catalog,
        "fr",
        path,
        tmp_path / "l.json",
        severity=severity,
        family=("accuracy", "style"),
        scope=("Review A", "B"),
    )
    assert result["applied"] == 1, result
    ledger = json.loads((tmp_path / "l.json").read_text("utf-8"))
    assert ledger["scope"] == "Review A, B", "free text split by Fire is rejoined"


def test_apply_when_ledger_exists_then_exit_2_unless_force(catalog, tmp_path):
    path = write_candidates(
        tmp_path / "c.jsonl", [candidate("Main.open", "Open", "Ouvrir", "Ouvrez")]
    )
    ledger = tmp_path / "l.json"
    editorial.apply(catalog, "fr", path, ledger)
    call = lambda: editorial.apply(catalog, "fr", path, ledger)  # noqa: E731
    assert _exit_code(call) == 2, "an existing ledger is refused"
    result = editorial.apply(catalog, "fr", path, ledger, force=True)
    assert result["skipped"]["already_applied"] == 1, result


def test_review_when_out_is_catalog_then_exit_2(catalog, endpoint):
    call = lambda: editorial.review(catalog, "fr", catalog, model="m", endpoint="e")  # noqa: E731
    assert _exit_code(call) == 2, "out == catalog is refused"
    assert endpoint.calls == [], "nothing sent"


def test_review_when_flags_named_like_translate_then_style_and_glossary_used(
    catalog, tmp_path, endpoint
):
    import inspect

    style = tmp_path / "fr.md"
    style.write_text("Use vous.", encoding="utf-8")
    editorial.review(
        catalog,
        "fr",
        tmp_path / "c.jsonl",
        model="m",
        endpoint="e",
        style_file=str(style),
    )
    assert endpoint.calls[0][0].endswith("Use vous."), "--style-file is the style sheet"
    parameters = inspect.signature(editorial.review).parameters
    assert "glossary_memory" in parameters, "--glossary-memory like translate"
    assert parameters["temperature"].default == 0.2, "same default as translate"


def test_review_when_glossary_status_names_proposed_then_proposed_terms_sent(
    catalog, tmp_path, endpoint
):
    memory = glossary(tmp_path / "fr.tmx", ("Open", "Ouvrir"), status="proposed")
    flags = {"model": "m", "endpoint": "e", "glossary_memory": str(memory)}
    editorial.review(catalog, "fr", tmp_path / "default.jsonl", **flags)
    assert '"Open": "Ouvrir"' not in endpoint.calls[0][1], "default leaves proposed out"
    editorial.review(
        catalog,
        "fr",
        tmp_path / "opted.jsonl",
        glossary_status=("approved", "proposed", "do-not-translate"),
        **flags,
    )
    assert '"Open": "Ouvrir"' in endpoint.calls[1][1], "a Fire tuple of statuses works"


def test_review_when_glossary_status_unknown_then_exit_2(catalog, tmp_path, endpoint):
    call = lambda: editorial.review(  # noqa: E731
        catalog,
        "fr",
        tmp_path / "c.jsonl",
        model="m",
        endpoint="e",
        glossary_status="approved,deprecated",
    )
    assert _exit_code(call) == 2, "an unknown status is a usage error"
    assert endpoint.calls == [], "nothing is sent on a usage error"


def test_review_when_signature_compared_then_glossary_status_matches_translate():
    import inspect

    from vexy_localizzy.cli.translate import translate

    ours = inspect.signature(editorial.review).parameters["glossary_status"]
    theirs = inspect.signature(translate).parameters["glossary_status"]
    assert ours.default == theirs.default == "approved,do-not-translate", (
        "same flag and default as localizzy translate"
    )
