---
this_file: docs/design/review-fidelity.md
---
# Reviewer visual verification

Reference: [review-concept.png](review-concept.png). Final primary render:
[review-desktop.png](review-desktop.png), 1536 × 1024 at device scale 1.
[Laptop](review-laptop.png): 1280 × 800. [Mobile](review-mobile.png): 390 × 844,
full-page capture. The in-app browser returned unavailable and the connected
browser inventory was empty. Verification used Playwright with installed Chrome.
The concept and the final desktop/mobile images were directly inspected with
`view_image` in the same QA pass.

| Comparison | Evidence and result |
|---|---|
| Layout | 74 px toolbar and 24.5/44/31.5% adjoining panels match the reference. The native 430 × 210 dialog is centered at y=417 in the desktop canvas. Fixed the renderer's original absolute positioning at the origin. |
| Copy | Primary headings, eight source labels, target text, context, suggestion provenance and action labels match. Approval count comes from saved data. Required additions are navigation/count and Fit controls. Dynamic QA/saved/conflict text reflects actual state. |
| Typography | Explicit system-sans sizes cover toolbar, headings, rows, inspector, controls and canvas. Corrected the renderer's default 11 px type to the concept's 16 px, while retaining explicit native widget styling. |
| Palette | White panels, cool gray toolbar/canvas, teal selection/action, amber unsaved and green approval are retained. No decorative gradients or image overlays. |
| Containers and spacing | Open adjacent panels, thin separators, small control radii and a single native dialog. Corrected sidebar start and fixed footer placement. No additional card grid. |
| Preview assets | Rendered from actual Qt XML using published quiht-core. Native input text is filled by the tested adapter. No screenshot is substituted for the UI. |
| Icons | Search, chevrons, navigation and quality marks use consistent outline/filled treatments. Dialog close chrome comes from quiht; it remains a preview control, not application execution. |
| Responsive | Corrected a squeezed mobile catalog selector and clipped native dialog. Fit scales the whole dialog, preserving native geometry; percentage views permit inspection at original size with pane scrolling. Both narrower viewports have no page-level horizontal overflow. |

The above-the-fold copy check found no unaccounted marketing or decorative copy.
Intentional functional deviations from the pictured state: navigation/count
footer, Fit selector, native textarea resize affordance, platform-native select
arrows, and actual saved/QA/error states. Mobile flows messages → editor → preview.
The desktop dialog chrome uses the published renderer with matching theme tokens.

Real browser checks covered preview selection, live translation, native input
text, original/localized tabs, modal focus and Escape, keyboard save, reload,
approval/advance, search/filter, plural forms, invalid edit rejection, stale
revision with preserved draft, discard/reload, TS download/native parse, RTL text,
literal malicious markup and responsive fit. An independent review found an
approval-reason race; a failing-before regression now verifies the field is
disabled throughout the save. Private UI/catalog screenshots remain private.

The implemented surface was faithfully checked against the concept with the
functional deviations above. No material layout or clipping issue remains in
the inspected viewports. This UI acceptance does not imply completion of the
full corpus/distillation/translation MVP.
