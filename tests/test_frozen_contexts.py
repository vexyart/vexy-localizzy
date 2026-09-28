# this_file: tests/test_frozen_contexts.py
"""Prepared contexts cross environments without losing exact request identities."""

import json

import pytest
from catalog_translation_fixtures import cache, response, template

from vexy_localizzy.catalog_translation import translate_catalog
from vexy_localizzy.catalog_translation_types import PromptContext
from vexy_localizzy.frozen_contexts import FrozenContexts, prepare_contexts
from vexy_localizzy.translation_store import digest

OPTIONS = {
    "plural_forms": {"0": "one", "1": "few", "2": "many"},
    "batch_size": 3,
    "max_batch_bytes": 1400,
}


def context(items):
    return PromptContext(
        style="Brief labels. " * len(items) * 30, glossary={"width": "szerokość"}
    )


def test_archive_when_loaded_then_exact_batches_and_zero_call_resume(tmp_path):
    artifact = prepare_contexts(
        template(), context, evidence=lambda: {"source": "digest"}, **OPTIONS
    )
    path = tmp_path / "contexts.json"
    artifact.write(path)
    loaded = FrozenContexts.load(path)
    calls = []

    def request(model, batch):
        calls.append(digest(batch.model_dump()))
        return response(model, batch)

    with cache(tmp_path / "cache.sqlite", request) as saved:
        first = translate_catalog(template(), saved, context=loaded, **OPTIONS)
        second = translate_catalog(template(), saved, context=loaded, **OPTIONS)
    assert first == second and first.pending_messages == 0
    assert calls == artifact.batch_digests, (
        "The consumer must request exactly the prepared batches once"
    )
    assert len(calls) > 3, "Exercise recursive byte-budget splits"
    copy = loaded.evidence
    copy.clear()
    assert loaded.evidence == {"source": "digest"}, "Archive evidence must be immutable"


@pytest.mark.parametrize(
    "change",
    ["locale", "source", "notes", "batch_size", "max_batch_bytes", "plural_forms"],
)
def test_archive_when_consumer_differs_then_fail_before_provider(tmp_path, change):
    artifact = prepare_contexts(template(), context, **OPTIONS)
    value, options = template(), dict(OPTIONS)
    if change == "locale":
        value = value.model_copy(update={"target_lang": "ru"})
    elif change in ("source", "notes"):
        value.units[0] = value.units[0].model_copy(
            update={change: "Different" if change == "source" else ["Different"]}
        )
    elif change == "plural_forms":
        options[change] = {"0": "singular", "1": "few", "2": "many"}
    else:
        options[change] += 1
    with cache(
        tmp_path / "cache.sqlite",
        lambda *_: pytest.fail("Mismatched context reached provider"),
    ) as saved:
        with pytest.raises(ValueError, match="context|Context"):
            translate_catalog(value, saved, context=artifact, **options)


def test_archive_when_context_removed_with_valid_seal_then_preflight_all_batches(
    tmp_path,
):
    artifact = prepare_contexts(template(), context, **OPTIONS)
    path = tmp_path / "contexts.json"
    artifact.write(path)
    data = json.loads(path.read_text())
    data["payload"]["contexts"].pop(next(reversed(data["payload"]["contexts"])))
    data["checksum"] = digest(data["payload"])
    path.write_text(json.dumps(data))
    loaded = FrozenContexts.load(path)
    with cache(
        tmp_path / "cache.sqlite",
        lambda *_: pytest.fail("Partial archive reached provider"),
    ) as saved:
        with pytest.raises(ValueError, match="context|Context"):
            translate_catalog(template(), saved, context=loaded, **OPTIONS)


def test_archive_when_corrupt_or_duplicate_json_then_reject(tmp_path):
    artifact = prepare_contexts(template(), context, **OPTIONS)
    path = tmp_path / "contexts.json"
    artifact.write(path)
    original = path.read_text()
    path.write_text(original.replace("Brief labels.", "Changed labels.", 1))
    with pytest.raises(ValueError, match="checksum"):
        FrozenContexts.load(path)
    path.write_text('{"checksum":"x",' + original[1:])
    with pytest.raises(ValueError, match="Duplicate"):
        FrozenContexts.load(path)


def test_archive_when_retrieval_mutates_inputs_then_reject(tmp_path):
    def bad(items):
        items[0].notes.append("mutation")
        return PromptContext()

    with pytest.raises(ValueError, match="must not change"):
        prepare_contexts(template(), bad, **OPTIONS)


def test_archive_when_context_return_mutated_then_subsequent_reads_unchanged():
    artifact = prepare_contexts(template(), context, **OPTIONS)
    from vexy_localizzy.catalog_translation_inputs import prepare_units
    from vexy_localizzy.qa import TextPolicy

    items = prepare_units(template(), None, {}, OPTIONS["plural_forms"], TextPolicy())[
        2
    ][:3]
    artifact(items).glossary.clear()
    assert artifact(items).glossary == {"width": "szerokość"}


def test_archive_when_glossary_order_changes_then_prepared_bytes_stay_identical(
    tmp_path,
):
    from vexy_localizzy.catalog_translation_inputs import prepare_units
    from vexy_localizzy.qa import TextPolicy

    artifact = prepare_contexts(
        template(),
        lambda _: PromptContext(glossary={"zebra": "zebra", "apple": "jabłko"}),
        **OPTIONS,
    )
    items = prepare_units(template(), None, {}, OPTIONS["plural_forms"], TextPolicy())[
        2
    ][:3]
    path = tmp_path / "contexts.json"
    artifact.write(path)
    loaded = FrozenContexts.load(path)
    assert artifact(items).model_dump_json() == loaded(items).model_dump_json(), (
        "Prepared context bytes must survive writing and loading"
    )
