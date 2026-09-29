---
this_file: src_docs/md/2-engineering/208-mirroring-and-rtl.md
---

# 208. Mirroring and right-to-left interfaces: layout, icons and mixed direction

Arabic, Hebrew, Persian and Urdu are read from right to left, and users of those languages expect the interface to follow: controls ordered from the right, text aligned to the right edge, the scroll bar on the left, tree views and tables reversed. Translating the strings is not enough; the layout has to change direction, and some things in it must not. This chapter explains the mechanism, the rule for deciding what flips, and how to keep mixed-direction text readable. The script-level background, the Unicode bidirectional algorithm and text shaping, is in [108](../1-foundations/108-scripts-direction-and-fonts.md).

## From flipping to mirroring

Early attempts were literal. Dr International (2002) describes the Arabic and Hebrew editions of Windows 95, which "flipped" dialogs by repositioning their controls and left title bars, tree views and combo boxes unchanged. Windows 98 introduced mirroring: a change of coordinate system in which the origin moves to the upper-right corner and horizontal coordinates grow to the left. Every control drawn through that coordinate system appears reversed without being repositioned by hand. From Windows 2000, mirroring was available in every language version of Windows and was switched on per application. O'Donnell, writing in 1994, could only record that no standard existed for layout orientation; she noted that menus cascade from right to left in Hebrew and that vertical scripts may put a window title elsewhere.

Today every major toolkit mirrors, and the web has direction built into HTML and CSS. The engineering question has moved from "how" to "what": which parts of the interface follow the reading direction, and which have a direction of their own. Dr International's advice for the programmer still frames it best:

> "Instead of thinking in terms of the concrete notions of left and right, you should substitute the more abstract concepts of near and far." (Dr International 2002)

Code that says "near" and "far", or "start" and "end", mirrors correctly. Code that says "left" and "right" has to be found and fixed.

## Mirroring in Qt and on the web

In Qt, one call sets the direction for the whole application, and individual widgets can opt out:

```cpp
QGuiApplication::setLayoutDirection(Qt::RightToLeft);
codeEditor->setLayoutDirection(Qt::LeftToRight);   // a code editor stays left to right
```

The direction can travel with the translation. The Arabic or Hebrew catalog translates a special message, `QT_LAYOUT_DIRECTION` in the `QGuiApplication` context, as `RTL`. The program looks that message up with `QCoreApplication::translate()` after installing the translator and sets the layout direction from the answer, so the direction ships with the language. In QML, `LayoutMirroring.enabled` with `childrenInherit` mirrors a subtree. The research corpus lists the pitfalls: positions set with explicit `x` coordinates are not mirrored, so use layouts and anchors; `QComboBox` has mixed-direction quirks (QTBUG-46245); and icons with a direction need mirrored assets.

On the web, direction is a document property and a stylesheet habit. Set `dir="rtl"` on the `<html>` element, or `dir="auto"` on content whose direction you do not know, and write CSS with logical properties such as `margin-inline-start` and `text-align: start` instead of `margin-left` and `text-align: left`. Dr International's rules for HTML predate logical properties and point the same way: avoid alignment attributes that override the document direction, avoid absolute positioning, which fixes the order of controls and makes them overlap, and remember that the browser does not flip images, so a directional image has to be flipped deliberately. One 2025 TypeScript book implements right-to-left support by swapping margins and flex directions in JavaScript; the research corpus recommends logical properties instead, and that is the simpler design.

## What flips, and what keeps its direction

By default a mirrored window mirrors everything in it, bitmaps included. That is correct for layout and wrong for anything whose direction carries meaning of its own. Dr International names three kinds of graphic: direction-sensitive ones, such as a back arrow, which must point the other way to keep their meaning; logos and trademarks, which must never be reversed; and text inside graphics, which becomes unreadable when mirrored. The FontLab runtime review adds a fourth kind that matters in any tool that edits geometry: outline coordinates, coordinate signs and commands that move a point have fixed meanings, and a mirrored view must not silently describe a different operation.

Here is the worked example: the main window of a font editor, localized into Arabic.

| Element | Mirror it? | Reason |
|---|---|---|
| Toolbar order, panel docking, menu order, dialog button order | Yes | Layout follows reading order |
| Text alignment in labels, lists and property fields | Yes | Reading order |
| Back and forward arrows in a history or page navigator | Yes, by using a mirrored icon | The meaning is "earlier" and "later" in reading order |
| The product logo on the splash screen | No | A trademark has one form |
| Screenshots or icons that contain Latin text | No; replace or relocalize them | Mirrored text is unreadable |
| The glyph editing canvas | No | Outline coordinates are font data, measured in the font's own axes |
| A command or icon that moves the selected points toward negative x | No | It describes geometry, not reading order |
| The ruler and coordinate readouts on the canvas | Decide explicitly and document it | They describe the same geometry as the canvas |

The last rows are where generic mirroring advice fails a specialized tool. A glyph is drawn in the font's coordinate system whatever language the interface speaks, and a command's label and icon must continue to describe what it does to that geometry. The FontLab guide asks reviewers to record which arrangements follow reading order and which represent unchanged geometry, and to name controls in instructions rather than calling them "the button on the right", which becomes false after mirroring.

Dr International lists four ways to handle graphics that must not follow the mirrored coordinate system: switch mirroring off while drawing them, where the drawing code allows it; keep a second set of pre-flipped images for the direction-sensitive ones; let localizers flip images in the resource editor, if each language ships its own resources; or create a mirrored copy in code at run time. The toolkit calls have changed; the four choices have not.

## Text that runs both ways

A right-to-left interface is rarely right-to-left all the way through. A Hebrew message can contain a Latin font name, a file extension, a version number, an OpenType feature tag or a path. The Unicode bidirectional algorithm orders such text for display, and it is reliable for simple cases. Dr International summarizes its assumptions: runs of opposite direction follow the base direction of the paragraph, digits within a number always run left to right, and punctuation between runs of the same direction stays between them. The difficulties are at the edges, where neutral characters such as parentheses, slashes and full stops sit between runs of different direction.

Three rules keep mixed text readable. Store text in logical order, the order in which it is typed, and never reverse characters to make a screenshot look right. Isolate every inserted value whose direction may differ from the sentence around it: in HTML, wrap it in `<bdi>` or give it its own `dir`; in plain-text formats, use Unicode directional isolates and document that you do, so that the invisible characters are not later removed as noise. And do not infer direction from a language code, because a language may be written in more than one script and a short value may contain only neutral characters.

```html
<p lang="ar" dir="rtl">
  الملف: <bdi dir="ltr">Sample-2.otf</bdi>
</p>
```

The FontLab writing guide lists the cases worth checking in review: a file name that ends in a number or an extension and is followed by punctuation; a quoted product name inside an opposite-direction sentence; two adjacent names of different direction; parentheses, a minus sign, a currency amount and a version number; empty and unexpectedly long values; and copying and pasting, where the copied text must keep its logical order. That last case is easy to forget, because the screen can look right while the clipboard carries the characters in the wrong order.

## Testing direction before any translation exists

Right-to-left defects can be found long before an Arabic or Hebrew translation exists. Dr International recommends pseudo-mirroring, a test build that changes only the direction and mirroring properties of the interface and leaves the English text alone, so that misplaced controls, broken check boxes, wrong alignment and controls drawn in one place but active in another become visible. The book's quick method for Win32, adding two left-to-right marks in front of a version-stamp field to mirror a whole process, is historical. The idea is current: in Qt, set the layout direction in a debug build; on the web, set `dir="rtl"` on the root element of a test page. The fl10n pseudo-localizer has an `rtl` mode that wraps each string in directional marks for the same purpose; [210](210-testing-world-readiness.md) describes it and a disagreement in its documentation. Review in the running application with real translations remains necessary, because only real text shows how inserted values and punctuation behave ([510](../5-interface/510-review-in-the-running-app.md)).

## Sources

- Dr International, *Developing International Software*, second edition, 2002 (chapter 5, complex scripts and bidirectional text; chapter 8, mirroring; chapters 11 and 12, pseudo-mirroring)
- Sandra Martin O'Donnell, *Programming for the World: A Guide to Internationalization*, 1994 (chapter 7, layout orientation and mixed-direction text)
- Baldurs L., *TypeScript Internationalization (i18n) and Localization (L10n)*, 2025 (chapter 11, right-to-left support)
- `research/01-foundations-of-software-localization.md`, `research/02-localizing-qt-cpp-applications.md` and `research/03-localizing-web-javascript-applications.md` in the fl10n repository
- `src/fl10n/engines/pseudo.py` in the fl10n repository
- `src_docs/md/global/bidirectional-text.md` and `src_docs/md/localization/runtime-review.md` in the vexy-fontlab-writing-styleguide repository
