---
this_file: src_docs/md/8-toolkit/scanning.md
---
# Scanning Qt source

`lupdate` is a static analyser. It never runs the code, so it extracts only
what it can see: a literal inside `tr()`, filed under the class that `Q_OBJECT`
names. Code that breaks either rule still compiles and still shows English at
run time, with no error anywhere. `localizzy qt scan` reads the source the way
`lupdate` does and reports those places before you extract.

```sh
localizzy qt scan src
localizzy qt scan src --format sarif --out scan.sarif
localizzy qt scan src --format json --out scan.json --min-coverage 0.8
```

The scan never edits source. With no paths it reads `[qt].sources` from
[`localizzy.toml`](project.md). Paths may be directories or single files; a
directory is searched for `.cpp`, `.cc`, `.cxx`, `.h`, `.hpp`, `.hxx` and,
unless `--noui`, `.ui` files.

## Rules

| Rule | Severity | What it catches |
|---|---|---|
| `QT-CTX-001` | critical | A class derived from `QObject`, `QWidget`, `QDialog`, `QMainWindow`, `QFrame` or `QAbstractItemModel` calls `tr()` but lacks `Q_OBJECT` |
| `QT-TR-002` | critical | `tr()` or `translate()` with a non-literal first argument |
| `QT-HARD-003` | major | A string literal passed to `setText`, `setWindowTitle`, `setToolTip`, `setPlaceholderText`, `setStatusTip`, `setWhatsThis`, `addItem`, `setTitle` or `setLabel` without `tr()` |
| `QT-NS-004` | major | `Q_DECLARE_TR_FUNCTIONS` with a qualified name, or inside a named namespace |
| `QT-STATIC-005` | major | `tr()` in a `static` initializer |
| `QT-ARG-006` | minor | Chained `.arg(a).arg(b)` |
| `QT-CONCAT-007` | minor | A `tr()` result joined with `+` |
| `QT-NOOP-008` | minor | `QT_TR_NOOP` outside any class or struct body |
| `QT-UI-009` | major | A user-visible `.ui` property (text, title, tool tip, window title, status tip, placeholder, What's This) marked `notr="true"` |
| `QT-UTF8-010` | info | A source file that is not UTF-8 |
| `QT-TRUTF8-011` | minor | `trUtf8()`, removed in Qt 6 |
| `QT-CLANG-012` | major | The clang engine could not build a complete syntax tree for a file |

Why each one breaks translation:

- **Context drift (CTX-001).** Without `Q_OBJECT`, `tr()` uses the base
  class's context at run time, while `lupdate` files the string under the
  subclass. The lookup never matches, so the translation exists and is never
  shown.
- **Non-literal argument (TR-002).** `tr(name)` gives `lupdate` nothing to
  extract. Mark the literal where it is written (`QT_TR_NOOP`) and translate
  the variable later.
- **Hard-coded text (HARD-003).** The string never reaches a catalog.
- **Namespaces (NS-004).** The context the runtime asks for and the one
  `lupdate` records can differ when the name is qualified.
- **Static scope (STATIC-005).** The initializer runs before any translator is
  installed, so the value is fixed in the source language for the life of the
  process.
- **Chained `.arg()` (ARG-006).** If the first value contains `%1`, the second
  call substitutes into it. Use one multi-argument `.arg(a, b)`.
- **Concatenation (CONCAT-007).** Word order differs between languages; a
  translator cannot reorder two separate strings. Make it one string with
  placeholders.
- **Class-less `QT_TR_NOOP` (NOOP-008).** It has no context to file under. Use
  `QT_TRANSLATE_NOOP("Context", "text")`.
- **`notr` labels (UI-009).** `lupdate` skips them by design, so a visible
  label marked `notr` stays English. A form with embedded images also gets an
  info finding, as a reminder to check them for mirroring in right-to-left
  languages.

## Engines

`--engine heuristic`, the default, is a line and regular-expression pass with
brace matching for the class and namespace rules. It needs nothing installed
and runs every rule above. It knows nothing of macros, comments that span
lines or multi-line literals, so all its findings carry
`confidence: "heuristic"`.

`--engine clang` (the `clang` extra) parses each C++ file with libclang and
reports only `QT-TR-002` and `QT-CTX-001`, from the real syntax tree, with
`confidence: "exact"` and a `file:line:col` location. The other C++ rules are
not run for a file that parses cleanly; the `.ui` pass and the coverage counts
still are. A file that libclang cannot parse completely, usually because the
Qt headers were not found, would read as clean, so instead it gets one
`QT-CLANG-012` finding naming the first error and keeps its heuristic
findings.

Pass `--compile-commands build/compile_commands.json` (CMake writes it with
`-DCMAKE_EXPORT_COMPILE_COMMANDS=ON`) so that libclang sees the project's
include paths and defines; relative paths in its entries are resolved against
each entry's `directory`, as compilers do. Without it the arguments are
`-std=c++17 -DQT_CORE_LIB`, and in a Qt project nearly every file ends with
`QT-CLANG-012`. `--engine both` runs the heuristic pass everywhere and adds
the clang pass to files with a critical heuristic finding, so the same problem
can be reported twice, once by each engine.

## Coverage

For each C++ file the scan counts literal `tr()` calls (marked) and literals
in the UI setters above (hard-coded candidates). Coverage is marked divided by
marked plus candidates; a file with neither counts as fully covered. The table
output ends with the overall figure, the JSON output carries it per file.
`--min-coverage 0.8` makes the scan exit 1 below 80 per cent. Raise the
threshold as instrumentation proceeds rather than demanding everything on the
first day.

## Output and exit codes

`--format table` (default) prints one row per finding and a summary. `json`
writes the sources, engine, overall coverage, counts by severity, per-file
coverage and every finding. `sarif` writes SARIF 2.1.0 with one rule entry per
rule id: critical maps to `error`, major to `warning`, minor and info to
`note`. Code-scanning services read it directly; see
[continuous localization](ci.md).

| Exit | Meaning |
|---|---|
| 0 | No critical finding, coverage at or above `--min-coverage` |
| 1 | A critical finding, or coverage below the threshold |
| 2 | Unknown engine or format, a missing source path, no source paths given or configured, a missing `--out` directory, `--min-coverage` with no C++ files to measure, a missing or invalid `--compile-commands` file |
| 3 | `--engine clang` or `both` without the `clang` extra |
| 130 | Interrupted with Ctrl+C |

The report is written before the exit, so a failing run still leaves its
SARIF or JSON file behind.
