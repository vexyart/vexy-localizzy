---
this_file: src_docs/md/8-toolkit/project.md
---
# Project configuration

The general commands take every path as an argument. A project that runs them
every week writes its layout once, in `localizzy.toml`, and then names a
language code:

```sh
localizzy project upgrade de
localizzy project translate de
localizzy project build_ui de
```

## The file

`localizzy init --root .` writes a commented starter file. The file is found
from the working directory upward, or named with `--config`. It is parsed once
into frozen records: an unknown key is an error, not a silent default, and
relative paths are resolved against the directory that holds the file. Command
flags override it; built-in defaults fill whatever it leaves out.

```toml
[source]
language = "en"
locales = ["de", "fr", "es"]

[qt]
sources = ["src"]          # directories or .pro files
out_dir = "i18n/fresh"     # where qt extract writes
prefix = "app"             # app_de.ts, app_de.qm

[catalogs]
dir = "i18n"
pattern = "app_{code}.ts"
fresh_dir = "i18n/fresh"
retired_dir = "i18n/retired"
report_dir = "i18n/upgrade"

[memories]
dir = "i18n/memories"
direct = ["{code}-ui.tmx"]
glossary = ["{code}-core.tmx"]
glossary_statuses = ["approved", "do-not-translate"]

[languages.es]
catalog = "es_MX"
memory = "es-419"

[translate]
endpoint = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
cache_path = ".localizzy/translation-cache.sqlite"
fallback_models = ["MODEL"]
temperature = 0.2
timeout = 300
style_file = "style.md"    # optional guidance passed to the engine
```

`[qt]` serves `qt scan` and `qt extract` when they get no paths. The rest
serves the `project` commands.

## Fresh and approved catalogs

Keep two sets of catalogs apart. `qt extract` writes the FRESH catalogs:
whatever `lupdate` finds in today's code. The APPROVED catalogs under
`[catalogs].dir` hold reviewed translations. `[qt].out_dir` defaults to
`i18n/fresh`, the same directory as `[catalogs].fresh_dir`, so `qt extract`
never writes into the approved catalogs; the [upgrade](upgrade.md) does the
merge, with a retired file and a report. Keep the two pointing at the same
place if you change either. Setting `[qt].out_dir` to `[catalogs].dir` would
make `qt extract` merge straight into the approved catalogs the way plain
`lupdate` does.

## How a code becomes paths and tags

For `localizzy project upgrade es` with the file above:

| Item | Resolved to |
|---|---|
| APPROVED | `i18n/app_es.ts` |
| FRESH | `i18n/fresh/app_es.ts` (or `--fresh`) |
| NEW | `i18n/app_es.new.ts` (or `--out`) |
| RETIRED | `i18n/retired/app_es-<fresh>-<approved>.ts` |
| Report | `i18n/upgrade/app_es.json` |
| Direct memories | `i18n/memories/es-ui.tmx` |
| Glossary memories | `i18n/memories/es-core.tmx` plus any `--glossary` |
| Catalog language | `es_MX` |
| Memory language | `es-419` |

A code absent from `[languages]` uses the code for both tags. A configured
memory that does not exist is reported on stderr and skipped, except by
`build_ui`, which refuses to run without its glossary memories: their terms
would otherwise enter the project memory.

The two `<...>` parts of the RETIRED name are the first eight hex digits of
the SHA-256 of the FRESH and APPROVED files. The same pair of inputs therefore
always names the same file. Running the same upgrade again is allowed when it
retires exactly the same messages; if an existing retired file of that name
differs, the command stops with exit 2 rather than overwrite it.

## The commands

`project upgrade CODE` ports APPROVED onto FRESH and writes NEW, RETIRED and
the report, as [upgrade](upgrade.md) describes. `--no-engine` leaves new
strings pending. `--in-place` replaces APPROVED with NEW only when nothing is
left pending or untranslated. Otherwise NEW stays beside it for review and the
command exits 1 after writing NEW, RETIRED and the report. Usage errors exit 2.

`project translate CODE` fills APPROVED from its memories, then the engine,
and writes it back in place unless `--out` is given. `--memory-only` needs no
endpoint. `--source-catalog i18n/fresh/app_en.ts` starts a new language from
the source-language catalog; that keeps no existing translation, so it is
refused when the catalog of CODE already exists and `--out` is absent.

`project build_ui CODE` rebuilds the first `[memories].direct` file from the
approved catalog, leaving out pairs that the glossary memories already serve.

The engine model comes from `--model`, else the first `fallback_models`
entry; the rest of that list are the fallbacks. Without either, a command that
needs the engine stops with `No model: pass --model or list fallback_models
under [translate]`. `[translate].style_file` is resolved against the directory
of `localizzy.toml`.

The general commands (`upgrade`, `translate`, `tm build_ui`) still take
explicit paths and ignore `localizzy.toml`. Use them in scripts that own their
own layout.
