# this_file: tests/test_xliff_states.py
"""Target removal must not silently downgrade a retained approval state."""

import pytest

from vexy_localizzy.formats import xliff


@pytest.mark.parametrize(
    "raw",
    [
        '<xliff xmlns="urn:oasis:names:tc:xliff:document:1.2" version="1.2"><file source-language="en" original="a"><body><trans-unit id="a"><source>Open</source><target state="final">Ouvrir</target></trans-unit></body></file></xliff>',
        '<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" version="2.0" srcLang="en" trgLang="fr"><file id="f"><unit id="u"><segment state="final"><source>Open</source><target>Ouvrir</target></segment></unit></file></xliff>',
    ],
)
def test_xliff_when_target_removed_then_state_must_also_be_reset(tmp_path, raw):
    source = tmp_path / "in.xlf"
    source.write_text(raw)
    catalog = xliff.load(source)
    units = [catalog.units[0].model_copy(update={"target": None})]
    output = tmp_path / "out.xlf"
    with pytest.raises(ValueError, match="state"):
        xliff.dump(catalog.model_copy(update={"units": units}), output)
    assert not output.exists()
    units[0] = units[0].model_copy(update={"state": "untranslated"})
    xliff.dump(catalog.model_copy(update={"units": units}), output)
    assert xliff.load(output).units[0].state == "untranslated"
    assert xliff.load(output).units[0].target is None
