# this_file: src/vexy_localizzy/experimental/classification_export.py
"""Complete A/B exports with checked classification and original-source lineage."""

import hashlib
import json
from contextlib import closing
from itertools import zip_longest
from pathlib import Path

from vexy_localizzy.experimental.classification_inputs import source_rows, stage_usable
from vexy_localizzy.experimental.classification_results import validated_results


def _bound_ids(corpus, results, inputs):
    """Check every frozen source text inside the exporter's corpus transaction."""
    digest = hashlib.sha256()
    stage_usable(corpus.db, exporting=True)
    with (
        closing(results.selected_ids()) as selected,
        inputs.open("rb") as stream,
        closing(source_rows(corpus.db, exporting=True)) as sources,
    ):
        next_id = next(selected, None)
        digest.update(stream.readline())
        for line, expected in zip_longest(stream, sources):
            if line is None or expected is None:
                raise ValueError(
                    "Classification does not cover the complete usable corpus"
                )
            digest.update(line)
            entry = json.loads(line)
            if entry != expected:
                raise ValueError(
                    "Classified source text, IDs or locales differ from the corpus"
                )
            if entry["id"] == next_id:
                yield next_id
                next_id = next(selected, None)
        if next_id is not None or digest.hexdigest() != results.report["input_sha256"]:
            raise ValueError("Classification input changed during export")


def export_ab(
    corpus,
    directory: str | Path,
    inputs: str | Path,
    output: str | Path,
    *,
    entry_map_sha256: str | None = None,
) -> dict:
    """Validate the entire run, export A/B winners, and return its provenance report.

    Persist the returned report beside the TMX and retain the run/input evidence.
    Legacy inputs without an entry-map digest need an independently audited binding.
    """
    directory, inputs, output = (
        Path(directory).resolve(),
        Path(inputs).resolve(),
        Path(output).absolute(),
    )
    if output.resolve() == inputs or output.resolve().is_relative_to(directory):
        raise ValueError("A/B output overlaps its classification evidence")
    with validated_results(directory, inputs) as results:
        mapping = results.metadata.entry_map_sha256
        if (
            mapping is not None
            and entry_map_sha256 is not None
            and mapping != entry_map_sha256
        ):
            raise ValueError("Conflicting classification entry map digests")
        mapping = mapping or entry_map_sha256
        if mapping is None:
            raise ValueError(
                "Legacy classification input requires an audited entry map digest"
            )
        with closing(_bound_ids(corpus, results, inputs)) as ids:
            units = corpus.export_tmx(
                output,
                entry_ids=ids,
                source_snapshot=results.metadata.source_snapshot,
                entry_map_sha256=mapping,
            )
        with output.open("rb") as stream:
            output_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        return {
            **results.report,
            "entry_map_sha256": mapping,
            "units": units,
            "output_sha256": output_hash,
        }
