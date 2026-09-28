---
this_file: docs/design/review.md
---
# Review design contract

Reference: `review-concept.png`, 1536 × 1024. This is a working editor, with
code-native controls and the published quiht renderer for the central preview.
The concept is not used as a page background or a replacement for controls.

The 74 px toolbar contains Localizzy, Translation review, a catalog selector and
Export TS. Below it are three full-height adjacent panels, separated by 1 px
borders: messages (24.5%), preview (44%) and editor (31.5%). Panel contents scroll
independently; editor actions stay visible. At narrower widths the layout flows
into two columns and then one column, preserving editing and preview access.

Palette: white panels, cool gray toolbar (#f7f9fb), preview canvas (#edf2f5), dark
text (#101b30), muted text (#596981), border (#d9e0e7), teal accent (#008899), pale
teal selection (#e3f3f5), green approval (#168b49), amber unsaved (#f5a623).
There are no gradients, photography, raster UI assets or decorative overlays.
Use system sans throughout: 24 px wordmark; 22 px panel headings; 20 px section
headings; 16 px body, controls and rows; 14 px statuses/captions. Controls have
6 px corners, 1 px borders and clear focus rings. Main gutters are 20–26 px.

Allowed visible primary copy: Localizzy, Translation review, Sample · Polish,
Export TS, Messages, Search source or translation, Unreviewed only, 2 of 8
approved, UI preview, sample.ui, Original, Localized, Preview updates as you type.,
FileDialog, SOURCE · ENGLISH, TRANSLATION · POLISH, Open file, Otwórz plik,
Unsaved changes, Quality checks, No structural issues, Context, Button label in
the file dialog., Suggestions, Open → Otwórz, Memory · sample:1, Save draft,
Approve & next, Previous / next. Other message rows and their contexts/states
come from the sample catalog. Runtime text changes reflect actual saved data.

Icons: lucide search/chevron/arrows, 16–20 px, thin outline, muted color;
approval uses a white tick on green; state dots are solid circles. Wordmark is
plain text. The preview dialog is rendered from real synthetic Qt XML.

Component ownership: App composes toolbar and panels; Messages searches and
filters; Preview renders isolated UI; Editor handles target slots, QA and
suggestions; useReview handles revision-aware requests, navigation and unsaved
state; useQuality fetches validation and suggestions. Shared CSS owns tokens.

Required functional additions to the pictured state: discard confirmation,
save/reload errors, readonly/excluded messages, multi-form editors, empty states,
export failures, keyboard navigation buttons and list count. These use the same
type, spacing and palette. They appear only when the workflow requires them.
Export requires saving pending edits first so the downloaded TS is unambiguous.
Fit/percentage preview scaling is also required for real dialogs larger than a
pane and for mobile; its selector sits in the existing preview footer.

Verification must compare the reference and the rendered primary state at
1536 × 1024 when the browser allows it, plus its current viewport and a mobile
viewport. Record copy, layout, type, palette, spacing, preview and responsive
comparisons in the final fidelity ledger. Private screenshots stay private.
