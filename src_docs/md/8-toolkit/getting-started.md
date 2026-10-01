---
this_file: src_docs/md/8-toolkit/getting-started.md
---
# Getting started

This page takes a small Qt project from English-only source to a compiled
pseudo-locale and a translated catalog. Every command below runs against the
current CLI; the [command-line reference](cli.md) lists every flag.

## Install

The package needs Python 3.12 or later. The core install reads and writes
catalogs, scans source, pseudo-localizes and runs the deterministic QA checks.
Heavier capabilities sit behind extras, so a scan never pulls in a model SDK:

| Extra | Adds | Needed for |
|---|---|---|
| `translation` | abersetz and the OpenAI SDK | the engine in `translate`, `upgrade` and `project` |
| `llm` | the OpenAI SDK | `qa --layers judge` |
| `review` | FastAPI, uvicorn | `review` |
| `sources` | Fluent, properties, plist and CLDR data readers | `tm extract` on those formats, `tm oss2tmx`, `tm norm` |
| `clang` | libclang | `qt scan --engine clang` |
| `pofilter` | Translate Toolkit | `qa --layers pofilter` |

```sh
uv tool install 'vexy-localizzy[translation,review]'
```

A tool install has one set of extras. To change it, reinstall with every
extra you want, because `--force` replaces the set:
`uv tool install --force 'vexy-localizzy[translation,review,clang]'`. The
`uv pip install` hints that `doctor` prints apply to a virtual environment
instead. COMET quality estimation (`qa --layers qe`) has no extra; add it with
`--with unbabel-comet`. Qt Linguist's `lupdate`, `lrelease`
and `lconvert` are not bundled either. Install them from your Qt distribution:
`brew install qt` on macOS, `apt-get install qttools5-dev-tools` on Debian or
Ubuntu.

## Check the environment

```sh
localizzy doctor
```

`doctor` prints the platform, the Python version, each external tool with its
version or `MISSING`, and each extra as installed or not. Every gap comes with
the command that closes it. It installs nothing and changes no file.

## A first run

The example project has its C++ under `src/` and one Designer form. Start with
a project file, so later commands need fewer arguments:

```sh
localizzy init
```

`init` writes `localizzy.toml` with commented defaults and refuses to replace
an existing one unless you pass `--force`. Edit `[source].locales` to the
languages you ship. Extraction goes to `i18n/fresh/`, apart from the reviewed
catalogs in `i18n/`; the [project page](project.md) explains why.

Audit the source before extracting anything:

```sh
localizzy qt scan src
```

The scan lists strings that Qt will not translate: a class without `Q_OBJECT`,
`tr()` called on a variable, a literal handed straight to `setToolTip()`. It
exits 1 while a critical finding remains. [Scanning Qt source](scanning.md)
explains each rule.

Extract the marked strings with Qt's own parser:

```sh
localizzy qt extract
```

With no arguments the command reads `[qt].sources`, `[qt].out_dir`,
`[qt].prefix` and `[source].locales`, and writes `app_en.ts`, `app_de.ts` and
so on. Run it again after the code changes: existing catalogs are merged, not
replaced.

Make a pseudo-locale and compile it, to see clipped and hard-coded text in the
running application before any translator is involved:

```sh
localizzy pseudo i18n/fresh/app_en.ts i18n/fresh/app_xx.ts
localizzy qt release i18n/fresh/app_xx.ts
```

Start the first reviewed catalog of a language from memories, then from a
model, and check the result:

```sh
localizzy translate i18n/fresh/app_de.ts de --out i18n/app_de.ts \
    --endpoint https://api.openai.com/v1 --model MODEL
localizzy qa i18n/app_de.ts --plural-forms auto --format table
```

`translate` takes one target language per call, writes a report beside its
output (`app_de.ts.localizzy.json`) and leaves engine output unfinished for
review. Add `--memory-only` and drop the engine flags to see what memories
alone can fill. `qa` exits 1 when a finding at or above `--fail-on` (default
`major`) remains. A freshly extracted catalog fails it on purpose: every empty
target is a critical finding. People then [review](review.md) the catalog in a
browser. This first `translate` is the only time a draft goes straight to the
reviewed catalog's path; from then on, [`project upgrade`](project.md) carries
the reviewed translations onto each new extraction and writes its drafts
beside it for review.

## Where next

- [Project configuration](project.md) for weekly runs by language code.
- [Translating with memories](memories.md) for what `translate` decides and why.
- [Continuous localization](ci.md) for the same steps on GitHub Actions.
- [Troubleshooting](troubleshooting.md) when an exit code is not what you expected.
