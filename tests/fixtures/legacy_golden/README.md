---
this_file: tests/fixtures/legacy_golden/README.md
---
# Legacy converter goldens

These files are the outputs of the old fl10n scripts (`tools/ts2tmx.py`,
`po2tmx.py`, `lproj2tmx.py`, `adobe2tmx.py`, `oss2tmx.py`, `tmxnorm.py`) run on
synthetic inputs, captured on 2026-09-28. `tests/extract/test_legacy_parity.py`
runs the ported `vexy_localizzy.extract` modules on the same inputs. It compares
parsed records: header `srclang`, `tuid`, props, segments, languages and the
output filename set. It does not compare bytes.

No input is FontLab data:
- `inputs/ts`, `inputs/po` and `inputs/oss` are hand-written text files.
- The Adobe folder and the Apple bundle contain binary resources. These are PMST
  tables, a Pascal-string `.rsrc`, a Mach-O stub, a UTF-16 `.dat` and a binary
  `.loctable`. `tests/extract/legacy_builders.py` builds them at capture and at
  test time.
- `oss_registry.toml` is a synthetic app registry. Its repositories resolve to
  `inputs/oss/<repo>` in place of git clones.
- `legacy_apps.json` snapshots the fl10n `oss2tmx.APPS` table. The packaged
  `oss_apps.toml` must match it.

## Regenerate

Run the scripts with the fl10n virtual environment. Their `uv run -s` shebang
would fetch vexy-localizzy from PyPI instead of this tree.

```sh
FL10N=/path/to/fl10n
$FL10N/.venv/bin/python tests/fixtures/legacy_golden/capture.py $FL10N/tools
```

`capture.py` writes `commands.txt`. The recorded commands are these. `$TOOLS` is
the fl10n `tools/` folder, `$GOLDEN` is this folder and `$WORK` is a temporary
folder:

```text
python $TOOLS/ts2tmx.py --input $GOLDEN/inputs/ts --output $GOLDEN/ts2tmx/dir
python $TOOLS/ts2tmx.py --input $GOLDEN/inputs/ts/app_de.ts --output $GOLDEN/ts2tmx/single/app_de.tmx --src_lang en_GB
python $TOOLS/po2tmx.py --input $GOLDEN/inputs/po --output $GOLDEN/po2tmx/dir
python $TOOLS/po2tmx.py --input $GOLDEN/inputs/po --output $GOLDEN/po2tmx/fuzzy --fuzzy
python $TOOLS/lproj2tmx.py --app $WORK/Example.app --output $GOLDEN/lproj2tmx/default
python $TOOLS/lproj2tmx.py --app $WORK/Example.app --output $GOLDEN/lproj2tmx/options --dedupe=False --skip_identical --include_infoplist
python $TOOLS/adobe2tmx.py --input $WORK/Adobe Synthetic --output $GOLDEN/adobe2tmx/de --ui_lang de_DE
python $TOOLS/adobe2tmx.py --input $WORK/Adobe Synthetic --output $GOLDEN/adobe2tmx/auto --dedupe=False --skip_identical --include_infoplist
oss2tmx.main(output=$GOLDEN/oss2tmx, cache=<tmp>) with APPS from oss_registry.toml and fetch -> inputs/oss/<repo>
tmxnorm.normalize(<tmp>/tmxnorm-dry_run, dry_run=True)
tmxnorm.normalize(<tmp>/tmxnorm-apply, dry_run=False)
```

`oss2tmx` and `tmxnorm` are driven in-process. `oss2tmx` needs a swapped
registry and `fetch()`. For `tmxnorm`, the renamed count and the resulting file
list go into `tmxnorm/result.json`. Re-running the capture reproduces these
files byte for byte.
