---
this_file: DEPENDENCIES.md
---
# Dependencies

| Package | Role |
|---|---|
| lxml 6.1.x | Streaming XML parsing, preservation of inline XML, no external entity expansion |
| langcodes 3.5.x | BCP 47 canonicalization without inventing locale mappings |
| fluent.syntax 0.19.0 (`sources` extra) | Published Fluent AST/parser/serializer for bounded legacy message, term, attribute and selector projections |
| moz.l10n 0.14.2 (`sources` extra) | Published Mozilla properties/DTD parsing with explicit entity-reference and include handling |
| javaproperties 0.8.2 (`sources` extra) | Java properties escapes, surrogate pairs, continued lines and ordered duplicate keys |
| openstep-plist 0.5.2 (`sources` extra) | Published OpenStep parser for ordered Apple .strings extraction; binary/XML resources use stdlib plistlib |
| language-data 1.x (`sources` extra) | Published CLDR population data for the optional legacy filename policy; resolved at 1.4.0 with marisa-trie 1.4.1 |
| uubed 1.0.6 + NumPy 2.x (`embeddings` extra) | Published model inference/space identity and bounded float32 vector operations |
| scikit-learn 1.9.x + threadpoolctl 3.x (`clustering` extra) | MiniBatchKMeans, bounded initialization sampling and reproducible single-thread numerical work |
| pydantic 2.x | Versioned catalog boundaries, strict fields and original-document checksums |
| polib 1.2.x | Published gettext parser and serializer, including legacy encodings and obsolete records |
| Existing ElementTree/polib parsers | Explicit legacy Qt/gettext pair projections; no additional runtime dependency |
| tree-sitter 0.26.x + tree-sitter-json 0.24.x | Published JSON syntax tree with byte spans for scoped, formatting-preserving resource edits |
| filelock 3.x (`llm`/`review` extras) | Cross-platform exclusion of simultaneous classification and catalog-review writers |
| openai 2.54+ (`llm` extra) | Optional bounded transport; preserves provider retry timing for fallbacks |
| fire 0.7.x | CLI argument parsing and help |
| loguru 0.7.x | Optional verbose diagnostics |
| hatchling + hatch-vcs | Build wheel/sdist and derive versions from Git |
| pytest + pytest-cov + ruff | Behavior tests, coverage and static checks |

SQLite, gzip and atomic file operations use Python's standard library.
Selected exports use SQLite's documented [attached databases](https://www.sqlite.org/lang_attach.html)
for explicit disk staging and window functions for the existing winner policy;
caller TEMP-table settings are preserved. Classification handoff follows SQLite
[read-snapshot isolation](https://www.sqlite.org/isolation.html) and Python
[read-only URI connections](https://docs.python.org/3.12/library/sqlite3.html#how-to-work-with-sqlite-uris),
with existing Pydantic models for evidence boundaries. The handoff itself needs no additional package. The producer uses the documented
[filelock context manager](https://py-filelock.readthedocs.io/en/latest/) with a
zero acquisition timeout; an isolated lock/reacquisition check passed on macOS.
Catalog compatibility types and key/placeholder helpers are adapted from
MIT-licensed fl10n; attribution and license text are included in `NOTICE`.
Legacy filename planning is also adapted from that project. It uses
[langcodes](https://github.com/rspeer/langcodes) and its published
[language_data supplement](https://github.com/rspeer/language_data); input locale
identity remains separate from population-based filename shortening.
Format preservation and provider routing are original implementations;
public tests and examples contain synthetic data.

Published integration APIs have been exercised for abersetz 1.0.28,
uubed 1.0.6 and quiht-tools 1.0.8; the registry also offers quiht-core 1.0.8.
The uubed adapter is an optional component. Its CPU integration check uses
sentence-transformers 5.7.0 and transformers 4.57.6 with the revision-pinned
MiniLM model from uubed's registry. These inference dependencies are not core
requirements. The abersetz and quiht adapters are integrated and tested below.

The installed uubed 1.0.6 `Embedder` implementation was inspected for normalized
float32 output, model revision, prompt, token limit and cache identity semantics.
Its existing TMX index builder publishes atomically but starts over on interrupted
inference. Localizzy adds resumable per-source vector storage for classification
and distillation, retaining checksums, source IDs and explicit engine identity.

Clustering follows the published [MiniBatchKMeans API](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.MiniBatchKMeans.html)
and reservoir sampling API; the installed `partial_fit` implementation was checked
before integration. Strict subset responses use the existing Pydantic dependency.
Subset selection shares classification's cache, retry and identity machinery.

Parser behavior follows the [lxml streaming documentation](https://lxml.de/parsing.html).
Qt metadata handling follows the [TS format specification](https://doc.qt.io/qt-6/linguist-ts-file-format.html).
The existing Translate Toolkit TS adapter documents incomplete byte/length-variant
coverage, so the TS preservation layer uses lxml and retains the original bytes.
The optional transport follows the [OpenAI SDK error API](https://github.com/openai/openai-python#handling-errors).
PO parsing follows [polib's API](https://polib.readthedocs.io/en/latest/api.html)
and [GNU gettext entry syntax](https://www.gnu.org/software/gettext/manual/html_node/PO-File-Entries.html).
The Python standard library's gettext expression parser checks explicit plural
rule syntax; category ordering is supplied by the caller. Original bytes remain
the authority for unchanged documents.

XLIFF handling follows the OASIS [1.2 specification](https://docs.oasis-open.org/xliff/v1.2/os/xliff-core.html),
[2.1 core](https://docs.oasis-open.org/xliff/xliff-core/v2.1/os/xliff-core-v2.1-os.html)
and [2.2 core](https://docs.oasis-open.org/xliff/xliff-core/v2.2/xliff-core-v2.2-part1.pdf).
The lxml preservation layer retains original documents and module data; generated
and edited examples are checked against official core XSDs in integration audits.
This is not a claim of complete module/Schematron conformance.

Android resource handling follows the official [string-resource specification](https://developer.android.com/guide/topics/resources/string-resource)
and AOSP AAPT2 string parsing. The published Translate Toolkit adapter was tested
but drops unknown backslash escapes that AAPT2 retains, so the preservation layer
uses lxml with Android text decoding. Integration checks compile and link synthetic
resources with Google's [AAPT2](https://developer.android.com/tools/aapt2), comparing
the resulting values with independently authored fixtures. AAPT2 is an audit tool,
not a runtime dependency; these checks do not claim full Android conformance.

i18next follows the official [v4 resource format](https://www.i18next.com/misc/json-format)
and [plural behavior](https://www.i18next.com/translation-function/plurals).
Python's JSON decoder validates strict syntax and duplicate keys; the published
[Tree-sitter bindings](https://github.com/tree-sitter/py-tree-sitter) and JSON grammar
locate original value bytes. Both use MIT licenses. Translate Toolkit's i18next
adapter targets v3 plural suffixes. A JSON source-map candidate also failed escaped
key identity checks; neither is used. Native integration checks use published
i18next 26.3.6 as an audit dependency, not a Python runtime dependency.

Catalog TMX uses the existing lxml dependency and follows the
[TMX 1.4b specification](https://www.ttt.org/oscarStandards/tmx/tmx14b.html).
Original multilingual XML is retained; catalog-only metadata uses documented
extension properties. Integration checks validate fresh output against a bundled
TMX 1.4 DTD and independently compare scoped edits in native catalog samples.
This is not a claim of complete TMX Level-2 conformance.

The reviewer uses FastAPI and Uvicorn for a loopback HTTP API over the filesystem
store, without an application database. Its bundled React/Vite/TypeScript client
uses published quiht-core 1.0.8 to render Qt UI XML, DOMPurify for sanitization and
lucide-react for UI icons. Exact frontend versions are in `review/package-lock.json`;
bundled license texts are in `review/public/THIRD_PARTY_LICENSES.txt`. Vitest and
Testing Library exercise state changes; browser acceptance uses Playwright with
installed Chrome when the in-app browser is unavailable. Playwright is an audit
dependency, not a runtime dependency. The iframe permits same-origin DOM access
but no scripts; native `notr` strings remain unchanged. A small adapter populates
line-edit/plain-text values omitted by quiht-core 1.0.8.

The optional `translation` extra pins [abersetz 1.0.28](https://pypi.org/project/abersetz/1.0.28/)
for published glossary/example prompt construction and output extraction, together
with OpenAI's SDK. Installed-source and real-HTTP-mock tests verify the pinned
engine's single-attempt implementation beneath its Tenacity wrapper; Localizzy
owns fallback/cooldown policy. No translation engine implementation is vendored.

Content QA reuses Python `string.Formatter` and `html.parser`, plus the existing
polib dependency. Explicit C printf checks require the external GNU gettext
`msgfmt` executable; no copied C-format parser or new Python package is added.
Qt-only QA stays in-process. Native acceptance additionally uses Qt `lconvert`
and `lrelease`; these are validation tools, not bundled runtime dependencies.
The adapter records actual response models and rejects ambiguous JSON fields.

The optional Node ICU checker pins `@messageformat/parser` 5.1.1 (MIT) with its
Moo lexer dependency in `icu/package-lock.json`. It uses the published AST and
retained parser context, not a replacement ICU grammar. Node `Intl.PluralRules`
supplies locale categories; installations must pin Node/ICU as well as the npm
artifact. Python's subprocess bridge adds no Python dependency. The checker is
packaged separately and must be explicitly installed and configured by consumers.

Apple text extraction uses [fonttools/openstep-plist](https://github.com/fonttools/openstep-plist)
(MIT), a focused parser based on CoreFoundation. Its published `loads(dict_type=...)`
API was inspected and exercised in isolation before use. A collector preserves
repeated keys; a dictionary wrapper enforces complete parsing. This avoids copying
a grammar or stripping comments from inside values. Translate Toolkit was also
inspected; its generic properties reader has different line-oriented semantics.
Apple input contracts follow [String Resources](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/LoadingResources/Strings/Strings.html)
and Python's [plistlib API](https://docs.python.org/3/library/plistlib.html).

Fluent projection reuses [fluent.syntax 0.19.0](https://projectfluent.org/python-fluent/fluent.syntax/stable/).
The published parser, AST shape and serializer helper implementations were
inspected and exercised before integration. Syntax junk is rejected before
emitting resource entries; selector expansion is capped before allocating each
Cartesian product. Existing term/attribute/suffix and whitespace rules remain an
explicit extraction projection, not a Fluent runtime or native editor.

Properties extraction uses [javaproperties 0.8.2](https://javaproperties.readthedocs.io/en/stable/plain.html)
(MIT). The published `loads(object_pairs_hook=list)` and unescape implementation
were inspected and exercised before adoption. Decoded values are independently
compared with Java [Properties.load(Reader)](https://docs.oracle.com/en/java/javase/11/docs/api/java.base/java/util/Properties.html#load(java.io.Reader)).
Java is a verification tool, not a runtime requirement.

Mozilla resource extraction uses [moz.l10n 0.14.2](https://github.com/mozilla/moz-l10n)
(Apache-2.0). Its published `parse_resource`, `Format`, `Entry` and `PatternMessage`
contracts and parser implementations were inspected and exercised before adoption.
DTD include declarations become metadata rather than translatable entries and are
never resolved by this projection. The sources extra additionally resolves
gitignorant 0.3.1 and iniparse 0.5; existing Fluent/polib dependencies are reused.
