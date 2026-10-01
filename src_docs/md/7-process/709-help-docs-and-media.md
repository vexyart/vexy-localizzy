---
this_file: src_docs/md/7-process/709-help-docs-and-media.md
---

# 709. Help, documentation, graphics and media: the content beyond the catalog

The interface catalog is the part of localization that tools understand best, and it is often the smaller part. Esselink (2000) called online help "typically the largest component" of a localization project, and his book spends more pages on help, documentation, desktop publishing and graphics than on software. Most of that content does something the catalog does not: it quotes the interface. Every help topic that says "choose **Tools > Add Guide**" depends on catalog entries being translated, stable, and still in that menu. This chapter covers the content outside the catalog and the process that keeps it in step with the catalog it describes. Part 5 discusses how the register changes from labels to help and manuals in [507. Registers of the interface](../5-interface/507-registers-of-the-interface.md).

## Content that quotes the interface

Esselink's scheduling chapter lists the dependency plainly. Help and documentation that refer to the software cannot be finished until the software is translated and tested; screen captures cannot be made until the localized software is engineered and tested; desktop publishing cannot be completed until the graphics are localized. His typical sequence therefore runs from terminology to software translation, then help and documentation, then software engineering and testing, screen captures, help engineering, desktop publishing, and final quality assurance.

When the schedule forces help translation to start before the software is finished, he gives a workaround that is still useful: have the help translators translate every software reference they meet and record those translations in a glossary, which is then used to translate the software itself. Either way, the interface terms are decided once and the documents follow them. The reverse, translating the software first and then letting help translators choose their own wording for the same labels, produces instructions that name controls the user cannot find.

In a continuous process the dependency does not disappear; it becomes a check. The FontLab writing guide lists, among the checks a script runs, "labels quoted in the Help Panel and the manual that do not match the catalog". The same guide warns that a source revision can invalidate an unchanged sentence: a changed screen, operation or link target makes a correct translation wrong without touching its text. Compare meaning as well as text when a new source arrives, record which translations and media are affected, and then read the whole revised procedure.

## Help and documents as engineering

Esselink treats help as an engineering job as much as a translation job. Before translation, check the kit: are all expected files there, are there extra or duplicate files, are the instructions complete? Then test-compile the source help. Missing files, broken links and configuration problems found now are fixed once; found after translation, they are fixed in every language. His word-counting advice for HTML names text that counters routinely miss: meta keywords, image placeholder text, button and form text, and text inside scripts.

For desktop publishing he adds a rule about tools. Work in the same operating-system version and the same application version that produced the source files, because a different printer driver, font or application version reflows text and forces rework. Do not convert documents into another format for translation unless a translation tool requires it. These specifics belong to an era of FrameMaker and PostScript, but the principle survives in 2026 as reproducible builds: record the tool versions, fonts and style sheets that produce each output, and check a sample at its real output size before recreating a whole set.

The FontLab writing guide adds two checks that Esselink's tools could not make.

**Segmentation.** Translation tools divide text into segments, and abbreviations, product-name punctuation, lists and inline markup can split a condition from the action it governs. The guide's example is a sentence that says to check the selected instance if the preview differs from the export. If the tool presents that as two segments, the condition must stay visible to the person translating the action, or the translated help turns a conditional check into an instruction for every export. Inspect how the actual tool segments a representative passage before assigning work.

**Reuse in new surroundings.** A memory match or reused topic is only correct where its assumptions hold. The same paragraph can be right in a tutorial and misleading as an isolated search result that hides the preceding step. Read across the boundaries between contributors and reused passages: terms must refer to the same concepts, steps must share the same starting state, and warnings must stay with the actions they qualify.

Finally, follow the reader's route. Start where the reader starts, at a control, an error message, a search query or a shared link, and follow it to the translated topic and its related material. Test the search index that ships, not the one in a developer's cache, and try both the professional term and the ordinary words a reader might type. A notification that all segments are translated describes a workflow state; the guide is explicit that acceptance depends on the documented review of the assembled result.

## Graphics and screenshots

Esselink divides the images in help and manuals into three kinds, each with its own cost:

| Kind | What it is | How it is localized |
|---|---|---|
| Generic graphics | Bitmaps with text on a background | Edited by hand in an image editor |
| Screen captures | Pictures of the interface | Recaptured from the localized product |
| Illustrations | Line art with text as objects | Text edited on its own layer |

Screen captures are the cheapest to redo and the easiest to get wrong. His checklist asks whether captures must be made on a localized operating system, which settings the original shows, whether the source contains sample content that the localized product will not display by itself, whether the source image was manually edited or even faked, and whether a cursor appears in it. He recommends capture scripts that record how to reach each dialog and in what state, written after the first language so that later languages go faster. Compare image settings and file sizes with the originals; a large difference suggests the wrong compression or resolution. For illustrations, keep text as text. Text converted to outlines cannot be edited and has to be redrawn.

Dr International (2002) applies pseudo-localization to media as well: overlay each graphic with its file name, or extend an audio file with its name, so that a pseudo build shows which media are in the localization scope and which were missed.

The FontLab guide adds a rule that matters when the product itself is not localized. If the interface stays in English, translated instructions quote its English labels, and translators must not paint translated controls into an image as if the product supplied them. Keep essential steps in text rather than only in images, translate meaningful image descriptions and callouts, and check what each arrow or highlight points to after the localized layout changes. An image description written for the old graphic may be wrong for the new one.

## Audio and video

For tutorials, the same guide asks reviewers to check captions and narration while watching the actions, not from a script alone. Target-language clauses may need different cue boundaries and timing, and a shortened caption must keep its facts and conditions. Translating the dialogue does not by itself cover captions, audio description and transcripts; each is a separate deliverable with its own review.

## A worked example: help that names a menu path

FontLab ships two kinds of help outside its Qt catalog: the Help Panel, 115 articles in a JSON file per language, and 51 welcome tips, each a title and a body. For the Polish edition, both were translated separately from the catalog by a script that resumes by English key, checks markup, placeholders, Markdown links and code spans in every item, rejects a batch with major or critical findings, and writes the target only when every item is complete.

The German welcome-tip review records one change that shows the dependency on the interface. The tip explains how to add a guide through two nodes. The record, with the unchanged title omitted, reads:

```json
{
  "ordinal": 1,
  "english_title": "Add a guide that goes through two nodes",
  "before": {"body": "Wählen Sie zwei Knoten und dann **Werkzeuge > Hilfslinie hinzufügen**, um eine Glyphenhilfslinie durch diese Knoten anzulegen."},
  "after":  {"body": "Wählen Sie zwei Knoten und dann **Werkzeuge > Hilfslinien > Hilfslinie hinzufügen**, um eine Glyphenhilfslinie durch diese Knoten anzulegen."},
  "why": "Aktueller Pfad: menuTools > menuGuides > actionAdd_Guide."
}
```

The German was fluent before and after. What changed was a fact: the command sits in a *Guides* submenu, and the reason cites the menu objects in the application source as evidence. The English tip still says **Tools > Add Guide**, so the translation was not wrong against its source; the source was wrong against the product. No linguistic review of the tip alone would have found this. It needed someone to follow the path in the product, and it leaves a source defect to report to the owner of the English help. Part 5 treats this situation in [508. Source text as evidence](../5-interface/508-source-text-as-evidence.md).

The same review recorded a side effect worth knowing about before renaming anything. The welcome tips use their display titles as history keys, so renaming a German title changes the key, and a user who has already dismissed that tip may see it again. The review README states this plainly rather than hiding it. Content outside the catalog often has identities of its own, and a translator who changes a title may be changing a key.

The German Help Panel review covered all 115 articles and changed 114, while keeping every lookup key and the title-semicolon-body format intact. Spanish and French help review remained pending when the record was written, which is exactly the kind of statement a release note for the help should carry: which outputs were reviewed, which were not, and in which build.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 7: help evaluation and test-compiling; chapter 9: desktop publishing preparation; chapter 10: graphics and screen captures; chapter 13: word counts for HTML; chapter 14: dependencies and sequence)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 12: pseudo-localization of graphics, audio and content)
- [localization/content-workflow](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/content-workflow/) and [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/) in the vexy-fontlab-writing-styleguide repository
- The German welcome tips review ledger (28 September 2026) and the review ledger directory README of the FontLab localization project
- The changelog of the FontLab localization project (the Polish localization entry, the JSON help translation script)
