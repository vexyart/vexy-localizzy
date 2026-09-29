---
this_file: src_docs/md/5-interface/507-registers-of-the-interface.md
---

# 507. Registers of the interface: labels, tooltips, help, manuals and store copy

One product speaks in several voices. A menu command names an action in two words. A tooltip explains it in a sentence. A help article teaches a task. A manual describes a whole subsystem. A store page tries to persuade someone who has not bought yet. All five mention the same features, and a user moves between them within minutes. A translation that renders each correctly in isolation can still fail if the voices disagree about what a feature is called, or if each uses the conventions of another.

This chapter is about choosing the register for each kind of text and keeping the vocabulary identical across them.

## One product, several kinds of writing

Jiménez-Crespo (2024) describes software, websites and apps as digital genres: conventionalized forms whose readers carry expectations about structure, register and language, formed by repeated encounters. A genre breaks down into sections with their own conventions. Some call for a direct approach to translation, such as interface text and legal terms; others allow a more creative one, such as marketing copy. For languages with formal and informal address, the genre and the locale together decide which one a text uses.

Roturier (2015) shows how companies write these decisions into translation guidelines. Twitter's Spanish guidelines, as he quotes them, ask for *tú* and an informal tone without regional slang. Microsoft's German guidelines for its phone platform ask for *Sie*, because the audience prefers a formal, professional address. Mozilla's French support documentation uses the imperative in lists of steps and the infinitive in headings. These choices differ between companies, and that is the point: register is a product decision recorded per language, not a property of the language.

The FontLab language guides recorded their own decisions, shown here with the catalog's rendering of *Remove pair*:

| Kind of text | German | Spanish (Latin American) | French |
|---|---|---|---|
| Menu commands, buttons | infinitive (*Paar entfernen*) | infinitive (*Eliminar par*) | infinitive (*Supprimer la paire*) |
| Longer instructions, help | *Sie* form | *tú* form, *ustedes* for several people | imperative, *vous* |

Inside one catalog, two voices mix. The interface-strings page separates the product, which speaks to the user (*Cannot open %1*), from the company, which speaks as itself (*Thank you for trying FontLab*). Product messages drop the first person and do not copy exclamation marks by reflex. Esselink (2000) gave the same advice: no first person in messages, the imperative for commands, and no automatic exclamation marks, since many languages use them less. He added an example of register adaptation that still applies: an English *Congratulations, you have successfully installed this application* may need to lose the *Congratulations* in a more formal target language.

The FontLab catalogs contain a third voice that the older books did not anticipate: an assistant chat. The German review notes that the automatically inserted question *Wer bist du?* (Who are you?, informal) is addressed by the user to the assistant, so it takes *du*, while the application addresses the user with *Sie*. A tool response reporting that the user declined an action stays in the third person, because the text is passed on and *Sie* could name the wrong recipient. Identify who is speaking to whom before choosing the form of address.

## Labels, tooltips and hidden strings

A label and its tooltip are two registers of one control. The label is compressed ([502](502-headline-style.md)); the tooltip is a sentence and keeps its grammar. Esselink's Windows example shows them in a single resource string, *Changes page layout settings\nPage Setup*, where the text before `\n` went to the status bar and the text after it to the tooltip. Qt keeps them in separate properties, but the relationship is the same: the tooltip explains the label, so the two must name the same thing in the same words.

Tooltips, status tips, *What's This* text and accessible names share one weakness: a reviewer looking at the screen does not see them. They must still be translated, and they must agree with the visible label. The FontLab source review of September 2026 found how often such strings drift even in English. A stroke thickness field carried the tooltip *Y coordinate*; a Gallery button that replaces the current element was described as adding a reference; two buttons in a font-collection dialog had tooltips copied from an audit tool. Each was found by reading code against the catalog, not by looking at the application, and a user meets each one only when hovering over the control or listening to a screen reader. The quality specification makes accessibility its own review pass for this reason: screen-reader names and descriptions translated and matching the visible labels.

The command and the dialog it opens are one text. Esselink's Swedish example, *Spara som* for both the *Save As...* command and the dialog title, is the rule; the FontLab interface-strings page repeats it and adds that repeated controls give a product its coherence through repetition and should be rendered identically everywhere.

## Help and manuals quote the interface

Help text has its own register, closer to technical prose, and one strict dependency: every interface label it mentions must be the label in the catalog. Esselink (2000) made this an ordering rule. Translate and review the software first, then the help, because help contains many references to the interface, and never translate a software reference without checking it against the running localized software. When help must be translated first, translate its references into a glossary that the software translators then use. Dr International (2002) adds that the help system is itself software, with scripts and templates that must work in every locale.

The German FontLab welcome tips show the ordering rule enforced against the English. Some English tips named menu paths older than the current main window form. The German review rewrote them from the menu definitions, as *Datei > Exportprofile* and *Ansicht > Ebenen & Glyphen > Cousins*, and recorded that a visual check of the running application was not thereby claimed. Correct help can be more current than its English source when the reviewer reads the interface rather than the source text.

**Worked example: a term that drifted between registers.** In fl10n issue 133, the founder decided that German *Nudge* is *Schub* and *Power Nudge* is *Power-Schub*. The catalog applied it: the node widget's tooltip now reads *Power-Schub (Umschalt+C, vorübergehend: C+Ziehen)*. A search of the German Help Panel file on 29 September 2026 found *Power-Schub* twice and, in one article, a bold label **Power-Verschiebung**, the earlier rendering, describing the same mode. A reader who looks for *Power-Verschiebung* in the interface will not find it. The German language guide itself lists *Power-Verschiebung* among the welcome-tip terms that match the catalog decisions, and its help section still names *Kegelauflösung* for units per em, which the principles replaced with *Geviertauflösung*; the shipped help data no longer contains *Kegelauflösung*. The guide and the help were each correct when written and each fell behind a later decision.

Two checks would have caught it. The quality specification lists a script check for labels quoted in the Help Panel and the manual that do not match the catalog, and the principles require a decision to be recorded in the core memory, from which the help can be checked. Neither helps unless it runs after every terminology change, not only after the first translation.

## Store copy and claims

Store pages, marketing email and the About box are the company's voice, and they are written for a reader who has not decided yet. They allow the most freedom of wording and the least freedom of fact. The writing guide's content workflow draws the line: a translator may adapt how a benefit is expressed, but a different price, support contact, supported feature or comparison needs a decision from the owner. A translated store page must describe the language support the delivered product actually has, including the language in which help is available.

Legal and market requirements sit here too. Roturier quotes Microsoft's French style guide: absolute expressions such as *fully secure* are a serious legal risk in the French, Canadian and Belgian markets. The FontLab French guide asks reviewers to flag such a claim against its source rather than soften it silently. The older books add the practical cases: Uren (1993) on American toll-free numbers that cannot be dialed abroad, Esselink (2000) on support phone numbers in strings, which publishers usually replace with a reference to the local office.

Humor is where sources disagree. Uren (1993) and Dr International (2002) tell writers to avoid humor because it is culture-specific. FontLab deliberately chose a slightly humorous word for its *Smart* features: German *schlau*, Spanish *astuto*, French *futé*, Polish *sprytny*, clever with a hint of cunning, in part because *intelligent* now reads as a claim about AI. The positions differ in scope. The older advice concerns jokes in source text that a translator must carry across cultures. The FontLab choice is a term selected per language by native reviewers, whose meaning survives if the joke is missed. House voice across languages is the subject of [407](../4-terminology/407-house-voice-across-languages.md).

## Keeping registers consistent over time

Registers drift apart because they are translated at different times. The catalog is reviewed in one month, the help in the next, the store page by someone else in a third. Each pass is internally consistent; the drift appears between them. The principle of one meaning, one translation ([402](../4-terminology/402-terminology-work.md)) therefore extends across registers: a term decision applies to the catalog, the help, the welcome tips, the manual and the marketing pages at once, and the review is not complete until all of them agree.

In practice that means three habits. Record every term decision in the core memory, not only in the catalog. After a decision, search every register for the retired form, as the German help example shows. And keep a ledger entry for each change so that a later reviewer can see which register changed when. The register may differ from text to text; the name of a thing may not.

## Sources

- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (section 4.4.3)
- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 3: language guidelines and control codes; chapter 6: translation guidelines)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 9)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (sections 4.2.2 and 4.3.5)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 7)
- `issues/133.md` in the fl10n repository
- `data-fontlab-cpp/i18n-repo/fontlab_de.ts`, `help/helppanel.json` and `help/helppanel_de.json` in the fl10n repository
- `data-fontlab-cpp/i18n/source-review/possible-bugs-2026-09-28.md` (B-015, B-021, B-023) in the fl10n repository
- `src_docs/md/localization/ui-strings.md`, `content-workflow.md`, `quality.md`, `principles.md`, `de.md`, `es.md` and `fr.md` in the vexy-fontlab-writing-styleguide repository
