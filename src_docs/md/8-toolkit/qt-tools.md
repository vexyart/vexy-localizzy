---
this_file: src_docs/md/8-toolkit/qt-tools.md
---
# Qt extraction, release and launch

Extraction uses Qt's own parser, never scraping of built artifacts, so the
catalog holds exactly what the running application will ask for. `localizzy qt`
wraps `lupdate` and `lrelease` with the options a version-controlled project
wants, and adds a launcher that opens a macOS Qt application in a chosen UI
language.

## Extract

```sh
localizzy qt extract src --out-dir i18n/fresh --prefix app --locales de,fr
localizzy qt extract app.pro --locales de
localizzy qt extract
```

The command writes `PREFIX_<code>.ts` for the source language and every
locale. Unset options come from [`localizzy.toml`](project.md): sources from
`[qt].sources`, the directory from `[qt].out_dir`, the prefix from
`[qt].prefix` (default `app`), the languages from `[source]`. The default
directory is `i18n/fresh`, never the reviewed catalogs. A relative
`--out-dir` is resolved against the working directory.

The `lupdate` call is fixed by policy:

- `-locations none` by default, so line-number churn never shows up in diffs.
  `--locations relative` or `absolute` restores them.
- Obsolete messages are kept: a string that left the source stays in the
  catalog as `vanished`, with its translation, in case it comes back.
  `--no-obsolete` drops them instead. [Upgrade](upgrade.md) ignores vanished
  messages either way and keeps its own retired file.
- `-extensions cpp,h,cc,cxx,ui`.
- A `.pro` file is passed through, so only files that the project compiles are
  read, and `lupdate` runs from its directory so that relative include paths
  work. A source directory with a `src` subdirectory adds it as `-I`.
- Existing catalogs are merged: finished translations stay, new strings arrive
  unfinished. `lupdate` works on hidden copies, and the real catalogs are
  replaced only after it succeeds.

Each locale catalog gets its `language` attribute set to its code. The command
prints one line per catalog with its message count and path. A missing
`lupdate` exits 3 with the install command. A missing source path, a failing
`lupdate`, or a source-language catalog with no live messages (usually a wrong
path) exits 2 with the reason, and no catalog is replaced. When `lupdate`
succeeds, its warnings are not shown. A class without `Q_OBJECT` is such a
warning, so run [`qt scan`](scanning.md) first.

## Release

```sh
localizzy qt release i18n/app_de.ts i18n/app_fr.ts
localizzy qt release i18n/app_de.ts --out-dir build/translations
```

Each catalog becomes `<stem>.qm` beside it, or in `--out-dir`; two catalogs
with the same stem cannot share an `--out-dir` and are refused. Commit the
`.ts` files and leave `.qm` to the build. No catalog is a usage error (exit 2);
a missing `lrelease` exits 3; a catalog that fails to compile stops the run
with exit 2 and `lrelease`'s own message.

## Launch a macOS application in another language

A Qt application that follows the system language list honours the launch
argument `-AppleLanguages "(code)"`, which overrides the saved preference for
that process only. Translations are usually compiled into the executable as
resources named `PREFIX_<code>.qm`.

```sh
localizzy qt applang list /Applications/MyApp.app myapp
localizzy qt applang run /Applications/MyApp.app de myapp --new
localizzy qt applang write_commands /Applications/MyApp.app myapp ~/Desktop/myapp-languages
```

`list` reads the executable and reports every `myapp_<code>.qm` resource name
it contains, plus the source language (`--source-lang`, default `en`),
which needs no catalog. Nothing is taken from a built-in table.

`run` launches the application in a language that `list` finds and refuses
any other. Without `--new`, a copy that is already running is only brought to
the front and keeps its language. With `--new`, a separate instance starts
with a private temporary directory; applications that allow a single instance
keep their lock there, and would otherwise quit at once.

`write_commands` writes one double-clickable `<name>-<code>.command` script
per language into the folder, each starting a new instance. `--name` sets the
script prefix; it defaults to a slug of the bundle name. These commands need
macOS.
