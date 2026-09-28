# this_file: tests/test_distillation.py
"""Selection requires explicit majority equivalence and protects rare locales."""

import json

import numpy as np
import pytest

from vexy_localizzy.distillation import DistillationEntry, decide, parse_selection


def reply(keep=(300,), drop=301, representative=300):
    return json.dumps(
        {
            "keep": list(keep),
            "drop": [
                {
                    "id": drop,
                    "representative": representative,
                    "equivalent": True,
                    "reason": "Same instruction",
                }
            ],
        }
    )


def entries(rare_on_source=False):
    return [
        DistillationEntry(
            id=11, source="Open", targets={"de": "Öffnen"}, criticality="A", quality=3
        ),
        DistillationEntry(
            id=22,
            source="Open it",
            targets={"de": "Öffnen", **({"is": "Opna"} if rare_on_source else {})},
            criticality="B",
            quality=1,
        ),
    ]


def test_selection_when_two_models_agree_then_drop_only_named_equivalent():
    responses = {
        "one": reply(),
        "two": reply(),
        "three": json.dumps({"keep": [300, 301], "drop": []}),
    }
    result = decide(
        entries(),
        np.array([[1, 0], [1, 0]], dtype=np.float32),
        responses,
        rare_locales={"is"},
    )
    assert result["kept"] == [11]
    assert result["dropped"] == [
        {
            "source_id": 22,
            "representative_id": 11,
            "similarity": 1.0,
            "models": ["one", "two"],
        }
    ]
    assert result["overrides"] == []
    assert result["votes"]["one"]["drop"][0]["reason"] == "Same instruction"


def test_selection_when_rare_target_missing_from_representative_then_keep():
    result = decide(
        entries(True),
        np.array([[1, 0], [1, 0]], dtype=np.float32),
        {m: reply() for m in ("one", "two", "three")},
        rare_locales={"is"},
    )
    assert result["kept"] == [11, 22] and result["dropped"] == []
    assert result["overrides"] == [{"source_id": 22, "reason": "rare_locale_coverage"}]


def test_selection_when_meanings_not_close_then_keep_despite_votes():
    result = decide(
        entries(),
        np.array([[1, 0], [0, 1]], dtype=np.float32),
        {m: reply() for m in ("one", "two", "three")},
        rare_locales=set(),
    )
    assert result["kept"] == [11, 22]
    assert result["overrides"] == [{"source_id": 22, "reason": "similarity"}]


def test_selection_when_drop_votes_disagree_on_equivalent_then_keep():
    items = entries() + [
        DistillationEntry(
            id=33,
            source="Launch",
            targets={"de": "Starten"},
            criticality="B",
            quality=1,
        )
    ]
    responses = {
        "one": reply((300, 302), 301, 300),
        "two": reply((300, 302), 301, 302),
        "three": json.dumps({"keep": [300, 301, 302], "drop": []}),
    }
    result = decide(
        items, np.tile([1, 0], (3, 1)).astype(np.float32), responses, rare_locales=set()
    )
    assert result["kept"] == [11, 22, 33]
    assert result["overrides"] == [
        {"source_id": 22, "reason": "no_majority_equivalence"}
    ]


@pytest.mark.parametrize(
    "response",
    [
        '{"keep":[300],"drop":[]}',
        '{"keep":[300,301,301],"drop":[]}',
        reply((300, 301)),
        reply((300,), 301, 399),
        reply((300,), 301, 301),
        reply().replace("true", "false"),
        reply().replace('"id": 301', '"id": "301"'),
        '{"keep":[300,301],"drop":[],"extra":true}',
        '{"keep":[300,301],"keep":[300,301],"drop":[]}',
        '```json\n{"keep":[300],"drop":[]}\n```',
    ],
)
def test_selection_when_incomplete_or_invalid_then_no_decision(response):
    with pytest.raises(ValueError):
        parse_selection(response, 2)


def test_selection_when_vote_missing_then_pending_not_approved():
    with pytest.raises(ValueError, match="three"):
        decide(
            entries(),
            np.array([[1, 0], [1, 0]], dtype=np.float32),
            {"one": reply(), "two": reply()},
            rare_locales=set(),
        )


def test_selection_when_rare_targets_shared_then_reduction_preserves_coverage():
    items = entries(True)
    items[0] = items[0].model_copy(update={"targets": {"de": "Öffnen", "is": "Opna"}})
    result = decide(
        items,
        np.array([[1, 0], [1, 0]], dtype=np.float32),
        {m: reply() for m in ("one", "two", "three")},
        rare_locales={"is"},
    )
    assert result["kept"] == [11]
    assert result["coverage_before"] == {"de": 2, "is": 2}
    assert result["coverage_after"] == {"de": 1, "is": 1}


@pytest.mark.parametrize("threshold", [-1, 1.1, float("nan")])
def test_selection_when_invalid_threshold_then_refuse(threshold):
    with pytest.raises(ValueError, match="threshold"):
        decide(
            entries(),
            np.array([[1, 0], [1, 0]], dtype=np.float32),
            {m: reply() for m in ("one", "two", "three")},
            rare_locales=set(),
            threshold=threshold,
        )
