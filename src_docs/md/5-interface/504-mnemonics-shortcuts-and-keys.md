---
this_file: src_docs/md/5-interface/504-mnemonics-shortcuts-and-keys.md
---

# 504. Mnemonics, shortcuts and key names: what the catalog may and may not change

A menu command carries more than its words. *&File* has a marked letter that the user presses with Alt to open the menu. *New...* may be followed by a tab and *Ctrl+N*, the key combination that runs the command without the menu. A tooltip may mention *Shift* or *Ctrl+Alt+drag*. Each of these belongs to a different owner. The mnemonic letter belongs to the translator, who must choose a letter that exists in the translation. The key binding belongs to engineering, because it is code. The key names belong to the platform, because users read them on their keyboards and in the operating system. This chapter sorts out who may change what.

## Three things a label can carry

Esselink (2000) shows all three in a single Windows menu resource of the time:

```text
POPUP "&File"
BEGIN
    MENUITEM "&New...\tCtrl+N",   57600
    MENUITEM "&Open...\tCtrl+O",  57601
    MENUITEM "Print Pre&view",    57608
END
```

The ampersand marks the mnemonic, which Esselink calls the hot key and which other sources call the accelerator or access key. The `\t` separates the label from a displayed shortcut. The number is the command identifier that the program's accelerator table binds to a key. Qt catalogs use the same ampersand convention, so a FontLab string such as *&Delete Node(s)* reaches the translator with its marker inside the text. Only the text before the tab is prose. The rest is a contract with the code.

In 1993 Uren, Howard and Perinotti asked that accelerator definitions be localizable without recoding the product for each language. That request has been met: in resource files and in Qt catalogs alike, the translator moves the marker by editing the string. The mnemonic is therefore squarely translation work, and so are its failures.

## Choosing a mnemonic letter

The rules have been stable since Esselink's guide, and the FontLab interface-strings page restates them for Qt.

- Keep exactly one ampersand per label. A literal ampersand in text is written `&&`, so *Save && Close* displays as *Save & Close*.
- Choose a letter that exists in the translation. *File* takes *D* in German *Datei*. The letter need not be the first.
- Keep the letter unique within its menu or dialog, counting items the program inserts at run time.
- Avoid letters with descenders (*g*, *j*, *p*, *q*, *y*), because the underline disappears into them.
- Avoid accented letters. Esselink's example is German *Öffnen*: a user without a German keyboard layout cannot type *Ö* with Alt.
- Follow the localized platform for standard commands. German *Öffnen* and *Speichern* keep *f* and *S*, as they do in every German Windows program.
- In Chinese, Japanese and Korean, keep the source letter in parentheses after the translation: *ファイル(F)*.

The rules conflict, and uniqueness wins. The top-level menu bar of FontLab 9 shows how each language resolved the conflicts. The English bar reads *File, Edit, Text, Font, Glyph, Element, Contour, Tools, Script, View, Window, Help*; the table lists the translated titles with their marked letters as they stood in the catalogs on 29 September 2026.

| English | German | Spanish | French | Polish |
|---|---|---|---|---|
| &File | &Datei | &Archivo | &Fichier | &Plik |
| &Edit | &Bearbeiten | &Editar | É&dition | &Edycja |
| Te&xt | &Text | Te&xto | Te&xte | Te&kst |
| &View | &Ansicht | &Vista | Affic&hage | &Widok |
| &Window | &Fenster | Ve&ntana | Fe&nêtre | &Okno |
| &Help | &Hilfe | A&yuda | &Aide | &Pomoc |

French *Affichage* cannot take *A* because *Aide* already has it, and *Édition* cannot take its accented capital, so they take *h* and *d*. Spanish *Ayuda* cannot take *A* because *Archivo* has it; the catalog uses *y*, a letter with a descender, following the Spanish guide's note that *Ayuda* takes *Y* on Windows. Platform convention outranks the descender rule. The language guides disagree with the catalogs in two places: the French guide lists *A* for *Affichage* and *E* for *Édition*, and the Spanish guide names the menus *Edición* and *Ver* where the catalog says *Editar* and *Vista*. When a guide and a catalog disagree about a platform convention, one of them is wrong. The reviewer settles which against the localized operating system and corrects the other.

The Polish column has two collisions. *&Plik* and *&Pomoc* both take *P*, and *Te&kst* and *&Kontur* both take *K*. The Polish guide notes that on Windows *Pomoc* conventionally takes *C*. The Polish catalog was a machine draft awaiting its native review when this table was made, and this is exactly what a structural check on one menu bar catches before a reviewer spends time on wording.

Collisions with items inserted at run time are harder. A menu defined in a form may be completed by the program: a *Show toolbar* entry that becomes *Hide toolbar*, a recent-files list, a context menu that adds *Delete*. Esselink's advice on a bare string such as *&Delete* in a string table still applies: before choosing its letter, find out where the program inserts it. A catalog check sees only the strings of one context; the collision appears in the running application ([510](510-review-in-the-running-app.md)).

## Shortcuts belong to engineering

A shortcut shown after a tab, or written into a tooltip, describes a binding that lives in code. Changing the displayed text without changing the binding produces a label that lies. Changing the binding is an engineering change.

The literature agrees on what should change and disagrees on who changes it. Esselink (2000) says combinations with function keys must never change, and that letter, digit or symbol combinations may be changed by the translator or localization engineer when the key cannot be typed on the local keyboard, though keeping the original is better. His list of troublesome characters is still the list: `@`, `$`, `{`, `}`, `[`, `]`, `\`, `~` and `|`. He notes that French keyboards type digits with Shift, so Ctrl plus a digit needs a test, and that a changed combination must change in both the menu text and the accelerator table. The FontLab principles take the same technical rules and move the decision: a changed shortcut is an engineering change, recorded as a source defect, in which the label and the binding move together. The difference reflects how products are built now. In 2000 the localization vendor often edited the resource file that held the binding; in a Qt application the binding is in source code, which the translator does not touch.

For a translator the rule is simple. Copy the shortcut exactly as it appears in the source. If it cannot work on the target layout, report it. The French guide adds the layout facts a reviewer needs: AZERTY moves *A*, *Q*, *Z*, *W* and *M*, and digits need Shift. The Polish guide warns that the Polish programmer's layout types *ą*, *ę* and the other diacritics with AltGr, so shortcuts built on AltGr combinations collide with typing.

## Key names in text

Key names are different. The keyboard itself is localized in many countries, and the operating system names keys in the user's language. Esselink's examples, *Umschalt* in German and *Maj* in French for Shift, are still the names users see. The rule is to take key names from the localized platform, never from memory, and to keep the combination's structure intact.

The FontLab catalogs show the result for one tooltip in four languages:

```text
en  Power nudge (Shift+C, temporarily: C+drag)
de  Power-Schub (Umschalt+C, vorübergehend: C+Ziehen)
es  Empuje fuerte (Mayús+C; temporal: C+arrastrar)
fr  Poussée forte (Maj+C, temporairement : C+glisser)
pl  Superholowanie (Shift+C, tymczasowo: C+przeciągnij)
```

German uses *Umschalt*, Spanish *Mayús*, French *Maj*, and Polish keeps *Shift*, because Polish Windows keeps the English key names. The companion string *Nudge (if off: Ctrl+Alt+drag)* shows the same split for Control: German *Strg+Alt+Ziehen*, while Spanish, French and Polish keep *Ctrl*. The letter *C* and the plus signs do not change in any language, and the French adds its no-break space before the colon ([509](509-language-portraits.md)). The key name is translated; the key is not.

The macOS side needs its own check. The German guide gives *Befehlstaste* or the symbol for Command; the Spanish and French guides give *Cmd*. A string shared between platforms should be written so that the platform-specific modifier can be substituted by the program, which is a source design question, not a translation.

## What the code must not assume

Mnemonics expose a class of defect that belongs to neither translator nor platform. The FontLab source review of September 2026 found a menu handler in the Glyph window that decided what to do by comparing the action's visible text, in lowercase, with the English word *unlink*. In any translated build the text is *Verknüpfung lösen* or its equivalent, the comparison is always false, and the command runs the wrong branch. The review classed it as a major, localization-breaking defect and recommended branching on data attached to the action instead of its text. The verdict rests on reading the code; the build was not run.

The general rule is that display text is for display. A mnemonic marker, a translated word or a reordered label must be free to change without changing behavior. When a translator notices behavior that depends on a label, the finding goes to engineering with the file and the reason, as described in [508](508-source-text-as-evidence.md).

**Checking.** Much of this chapter is mechanical, and a script should do the mechanical part.

- The FontLab quality specification checks the mnemonic count per label and duplicate mnemonic letters per context, and it compares non-translatable tokens between source and target.
- vexy-localizzy's default Qt policy treats ampersand mnemonics as part of the structural check: the marker may move to another letter, `&&` counts as a literal ampersand, and inside HTML an ampersand in an attribute or a character entity does not count as a mnemonic.
- A duplicate-letter check needs a notion of which strings share a menu. A context in a Qt catalog is usually a class, and one class can hold several menus, so treat each hit as a question.

A script cannot see letters in menus assembled at run time, cannot tell whether a shortcut is typable on a French keyboard, and cannot know which modifier the platform names. Those checks need the running application on a localized system, with the target keyboard layout active.

## Sources

- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (section 4.3.12)
- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 3: hot keys and control keys)
- `data-fontlab-cpp/i18n-repo/fontlab_de.ts`, `fontlab_es.ts`, `fontlab_fr.ts` and `fontlab_pl.ts` in the fl10n repository
- `data-fontlab-cpp/i18n/source-review/possible-bugs-2026-09-28.md` (B-002) in the fl10n repository
- `Proteus/workspace2/mainwindow.ui` (menu bar order) in the FontLab application source
- [localization/ui-strings](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/ui-strings/), [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/), [localization/de](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/de/), [localization/es](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/es/), [localization/fr](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/fr/) and [localization/pl](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/pl/) in the vexy-fontlab-writing-styleguide repository
- [docs/quality.md](../8-toolkit/quality.md) in the vexy-localizzy repository
