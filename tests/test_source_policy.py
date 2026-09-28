# this_file: tests/test_source_policy.py
"""Product identities, aliases and policy revisions must not inflate votes."""

from pathlib import Path

from vexy_localizzy.corpus.store import Corpus


def test_alias_when_policy_revised_then_historical_policy_cannot_authorize_votes(
    tmp_path,
):
    import pytest

    path = tmp_path / "a.tmx"
    path.write_text(
        '<tmx><body><tu><tuv lang="en"><seg>Moon</seg></tuv><tuv lang="pl"><seg>A</seg></tuv></tu></body></tmx>'
    )
    alias = tmp_path / "alias.tmx"
    alias.symlink_to(path)
    with Corpus(tmp_path / "memory.sqlite") as corpus:
        corpus.import_tmx(path, family="alpha", weight=3)
        corpus.import_tmx(path, family="beta", weight=3)
        with pytest.raises(ValueError, match="family policy"):
            corpus.import_tmx(alias, family="alpha", weight=3)
        corpus.import_tmx(alias, family="beta", weight=3)
        assert corpus.winners()[0]["score"] == 3


def products(path: Path) -> Path:
    path.write_text(
        "<tmx><body>"
        + "".join(
            f'<tu><prop type="product">{product}</prop><tuv lang="en"><seg>Moon</seg></tuv><tuv lang="pl"><seg>Księżyc</seg></tuv></tu>'
            for product in ["Alpha 1", "Alpha 2", "Beta"]
        )
        + "</body></tmx>"
    )
    return path


def test_product_policy_when_versions_share_family_then_only_independent_products_vote(
    tmp_path,
):
    with Corpus(tmp_path / "corpus.sqlite") as corpus:
        corpus.import_tmx(
            products(tmp_path / "a.tmx"),
            family="collection",
            weight=3,
            family_property="product",
            family_map={"Alpha 1": "alpha", "Alpha 2": "alpha", "Beta": "beta"},
        )
        winner = corpus.winners()[0]
        assert winner["score"] == 6
        assert {p["family"] for p in corpus.provenance(winner["candidate_id"])} == {
            "alpha",
            "beta",
        }


def test_product_policy_when_mapping_changes_then_old_policy_is_replaced(tmp_path):
    with Corpus(tmp_path / "corpus.sqlite") as corpus:
        path = products(tmp_path / "a.tmx")
        corpus.import_tmx(path, family="collection", weight=3)
        assert corpus.winners()[0]["score"] == 3
        report = corpus.import_tmx(
            path,
            family="collection",
            weight=3,
            family_property="product",
            family_map={"Alpha 1": "alpha", "Alpha 2": "alpha", "Beta": "beta"},
        )
        assert not report["cached"] and corpus.winners()[0]["score"] == 6


def test_alias_when_same_family_then_preserves_both_paths_without_extra_weight(
    tmp_path,
):
    with Corpus(tmp_path / "corpus.sqlite") as corpus:
        original = products(tmp_path / "a.tmx")
        alias = tmp_path / "alias.tmx"
        alias.symlink_to(original)
        corpus.import_tmx(original, family="collection", weight=3)
        corpus.import_tmx(alias, family="collection", weight=3)
        winner = corpus.winners()[0]
        assert winner["score"] == 3
        assert {
            Path(p["path"]).name for p in corpus.provenance(winner["candidate_id"])
        } == {"a.tmx", "alias.tmx"}


def test_inline_when_imported_then_remains_distinct_and_recoverable(tmp_path):
    path = tmp_path / "inline.tmx"
    path.write_text(
        '<tmx><body><tu><tuv lang="en"><seg>A <bpt i="1">&lt;b&gt;</bpt>moon<ept i="1">&lt;/b&gt;</ept></seg></tuv><tuv lang="pl"><seg><bpt i="1">&lt;b&gt;</bpt>Księżyc<ept i="1">&lt;/b&gt;</ept></seg></tuv></tu></body></tmx>'
    )
    with Corpus(tmp_path / "corpus.sqlite") as corpus:
        result = corpus.import_tmx(path, family="alpha", weight=3)
        assert result["excluded"] == 0
        row = corpus.winners()[0]
        assert "<bpt" in row["source_xml"] and "<ept" in row["target_xml"]
