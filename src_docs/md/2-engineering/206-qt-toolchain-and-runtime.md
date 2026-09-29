---
this_file: src_docs/md/2-engineering/206-qt-toolchain-and-runtime.md
---

# 206. The Qt toolchain and runtime: lupdate, lrelease, lconvert, QTranslator, language switching

Marking strings is half of Qt localization. The other half is the chain of tools that turns marked source into catalogs a translator can edit, compiles them into files the program can load, and the runtime code that loads the right file, in the right order, and redraws the interface when the language changes. Each link has a failure that looks like a translation problem and is really an engineering one. This chapter follows the chain from `lupdate` to a running language switch, with a worked example of bundled and user-supplied translations.

## The pipeline and what to commit

The Qt pipeline has four steps:

1. `lupdate` scans the sources and forms and creates or updates one `.ts` XML catalog per language, keeping existing translations.
2. Translators edit the `.ts` files, in Qt Linguist or through another tool after conversion.
3. `lrelease` compiles each `.ts` into a binary `.qm` file with fast lookup.
4. The program loads the `.qm` files with `QTranslator` and installs them.

`lconvert` sits beside the chain and converts between `.ts`, `.po`, XLIFF and `.qm`, or merges several `.qm` files into one ([308](../3-formats/308-conversion-tools.md)). The research corpus recommends one division of labor: commit the `.ts` files, because they hold human work; treat `.qm` files as build artifacts; run `lupdate` in continuous integration with `-no-obsolete` and `-locations none` or `relative`, so that line numbers do not churn the diff; and run `lrelease` in packaging rather than in every developer build.

A typical application keeps one `.ts` per language for the whole program. Lupdate already groups messages by context inside the file, so there is no need for one file per window. Very large applications with independent libraries or plugins may keep one file per language per module, so that each module ships and updates its own translations.

| `lupdate` option | Effect |
|---|---|
| `-no-obsolete` | Drop messages no longer in the source |
| `-locations none` or `relative` | Keep `<location>` data out of version-control noise |
| `-I <path>` | Resolve namespaced classes; see [205](205-qt-instrumentation.md) |
| `-pluralonly` | Write only plural messages, for a source-language plurals catalog |
| `-warnings-are-errors` | Fail continuous integration on extraction problems |

| `lrelease` option | Effect |
|---|---|
| `-nounfinished` | Leave out translations not marked finished |
| `-fail-on-unfinished` | Fail the build if any are present |
| `-fail-on-invalid` | Fail on accelerator, whitespace, punctuation or place-marker mismatches |
| `-removeidentical` | Drop entries whose translation equals the source |
| `-markuntranslated <prefix>` | Prefix untranslated text, useful in test builds |

The sources disagree on one point that matters for release gating. The research corpus, following one of its drafts, says that `lrelease` includes only translations marked finished. The help text of `lrelease` 6.11.2 lists `-nounfinished` as "Do not include unfinished translations", which implies the opposite default, and a test run for this chapter confirms it: a two-message catalog with one finished and one unfinished translation compiled with plain `lrelease` reported "1 finished and 1 unfinished", and converting the `.qm` back with `lconvert` showed both translations present. With `-nounfinished`, only the finished one remained. So pass `-nounfinished` or `-fail-on-unfinished` explicitly when the build must not ship unreviewed text. The same help text marks `-idbased` as deprecated and no longer required.

## Wire it into the build without losing work

Build integration is where translation work has actually been destroyed. In Qt 5 CMake projects, `qt5_create_translation` runs `lupdate` and `lrelease` together and registers the `.ts` files as generated outputs, so `make clean` deletes the version-controlled catalogs (QTBUG-41736). The research corpus records a disagreement: some of its sources present the macro as the convenient standard, others advise against it. The safe consensus is to separate extraction from compilation, using `qt5_add_translation` for `.qm` files and a separate, non-default target that runs `lupdate`.

Qt 6 made this easier. `qt_add_translations`, available since Qt 6.2, creates separate update and release targets and can embed the compiled files as resources. Since Qt 6.7, `qt_standard_project_setup` accepts the source and target languages. The lower-level `qt_add_lupdate` accepts a `PLURALS_TS_FILE`, a plurals-only catalog for the source language, so that an English "%n file(s)" does not print the literal "file(s)". The option names still drift between minor versions (`TS_FILE_DIR` became `TS_OUTPUT_DIRECTORY` in Qt 6.9), so pin continuous integration to one Qt minor version. In qmake, `CONFIG += lrelease embed_translations` compiles the catalogs and embeds them under `:/i18n/`.

## Load the right file

A program has to find the file that matches what the user reads, which is not always the formatting locale. KDAB documented a widely copied mistake in 2020: building the file name from `QLocale::system().name()`. That returns the formatting locale, for example `pl_PL`, even when the user's interface language list starts with German. The `QTranslator::load()` overload that takes a `QLocale` walks `QLocale::uiLanguages()` and tries each candidate from specific to general:

```cpp
// Antipattern: the formatting locale, not the interface language list.
translator.load("myapp_" + QLocale::system().name(), ":/i18n");

// Correct: tries myapp_de_DE.qm, then myapp_de.qm, then myapp.qm, for each UI language.
if (translator.load(QLocale(), "myapp", "_", ":/i18n"))
    QCoreApplication::installTranslator(&translator);
```

The research corpus notes that the search order of this overload was buggy in Qt 5 up to 5.15.2 (QTBUG-86179) and fixed in Qt 5.15.3 and 6.0.1. Two more facts decide whether the load works in practice. Qt's own dialogs and buttons are translated by Qt's catalogs, such as `qtbase_de.qm`, which the application must load too; the FontLab guide describes the symptom of forgetting them as an English *Cancel* beside a German *Öffnen*. And `QCoreApplication` does not take ownership of an installed translator: a `QTranslator` on the stack of a function is destroyed when the function returns, leaving a dangling pointer. Make it a member of a long-lived object, give it `qApp` as parent, or use static storage.

Installed translators are searched in reverse order of installation, and the first non-empty result wins. That rule gives layering for free. Here is the worked example, from the research notes on shipping FontLab's translations: canonical `.qm` files inside the signed application bundle, plus a writable folder where a user can add a language or override single strings.

```cpp
auto *bundled = new QTranslator(qApp);
if (bundled->load(QLocale(), "myapp", "_", bundledDir))
    qApp->installTranslator(bundled);             // installed first: lower priority

auto *user = new QTranslator(qApp);
const QString userDir = QStandardPaths::writableLocation(
    QStandardPaths::AppDataLocation) + "/translations";
if (user->load(QLocale(), "myapp", "_", userDir))
    qApp->installTranslator(user);                // installed last: wins where it has a string
```

On macOS, files inside a signed bundle are sealed by the bundle's signature, so anything the user changes must live outside it. An override replaces a string only under the same context, source and disambiguation. If users are to edit plain text rather than compiled files, the notes describe two routes: a custom `QTranslator` that parses `.ts` XML itself, or `lrelease` run on the user's machine. They add that Qt's tools are licensed differently from its libraries, as commercial or GPLv3 with the Qt exception, so shipping `lrelease` inside a proprietary product needs a license check before it needs code.

## Switch languages while the program runs

`installTranslator()` and `removeTranslator()` send a `QEvent::LanguageChange` to the application, which passes it to every top-level widget. A widget reacts in `changeEvent()`:

```cpp
void MainWindow::changeEvent(QEvent *event) {
    if (event->type() == QEvent::LanguageChange) {
        ui.retranslateUi(this);      // Designer form
        retranslateNonDesigner();    // widgets created in code
    }
    QMainWindow::changeEvent(event); // always chain to the base class
}
```

Four details make the difference between a switch that works and one that half works. Widgets created in code are not covered by `retranslateUi()`; reset their texts by hand, and block signals while repopulating a combo box so the switch does not trigger itself. Objects that are not widgets, such as models and controllers, never receive the event automatically; override `event()` or install an event filter on the application, and have models emit `headerDataChanged`. Strings cached as translated `QString`s keep the old language; cache the marked `const char*` and translate on each use ([205](205-qt-instrumentation.md)). And the base-class call matters, because `changeEvent` also carries style, font and palette changes.

Threads are where the research corpus found its sharpest disagreement. Of its four Qt drafts, one says installing and removing translators are the only thread-safe operations in the translation API, one says only `translate()` is documented as thread-safe, one says `QTranslator` is not thread-safe at all, and one says installation is documented as thread-safe but posts events that assert when sent from the wrong thread (QTBUG-17017). The Qt 6 documentation of `QObject::tr()`, quoted in the corpus, resolves the practical question:

> "This method is reentrant only if all translators are installed before calling this method. Installing or removing translators while performing translations is not supported."

So treat lookups as safe once the translator set is stable, and change the set only on the main thread, marshalling requests from workers with `QMetaObject::invokeMethod(..., Qt::QueuedConnection)`.

A custom translator, for example one that reads a database, overrides `translate(const char *context, const char *sourceText, const char *disambiguation = nullptr, int n = -1) const`. The `int n` parameter was added in Qt 5; an override without it is never called. Return an empty string to pass the lookup to the next translator. The lookup runs on the main thread many times per repaint, so load the data into memory at construction and never query a database or a network inside `translate()`.

## Updating catalogs when the code changes

Each run of `lupdate` merges the fresh extraction into the existing catalog in place. It keeps translations whose context and source are unchanged, marks messages that disappeared as vanished, and applies similarity heuristics that can be switched off. Vanished entries stay in the file until `-no-obsolete` removes them. What the in-place merge does not give you is an account of what happened: it writes no separate file of retired messages and no report, and it cannot draw on translation memories for messages that moved or changed. Localizzy's `upgrade` command takes the other approach. It reads a fresh `lupdate` catalog and the approved catalog separately, classifies every fresh message into one tier (exact, relocated, fuzzy, memory, engine or pending), writes the approved messages that nothing used into a separate RETIRED catalog, and records one outcome per message in a report. It refuses to write anything unless every fresh message is classified and every approved message is either used or retired. The details are in [310](../3-formats/310-identity-and-upgrade.md).

## Sources

- `research/02-localizing-qt-cpp-applications.md`, `research/05-format-conversion-cicd-and-continuous-localization.md` and `research/06-tldr.md` in the fl10n repository
- `research2/01-gpt.md`, `research2/03-gemi.md`, `research2/04-cla.md`, `research2/05-cla.md` and `research2/06-cla.md` in the fl10n repository
- `research-draft/313-gpt.md` and `research-draft/315-cla.md` in the fl10n repository
- `lrelease -help` output and a test compilation with `lrelease` and `lconvert`, Qt Linguist tools 6.11.2
- `src_docs/md/localization/ui-strings.md` in the vexy-fontlab-writing-styleguide repository
- `README.md` and `docs/upgrade.md` in the vexy-localizzy repository
