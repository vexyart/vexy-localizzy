---
this_file: src_docs/md/7-process/703-branches-and-merges.md
---

# 703. Branches, merges and conflicts: keeping git the source of truth

Translation files are the worst-behaved files in a repository. They are large, machine-written, touched by people who do not write code, and changed in bulk by tools that sort, reflow or re-escape whatever they touch. Put two such writers on two branches and the merge conflict is not a question of if. This chapter is about arranging branches, writers and checks so that conflicts are rare, small and resolved by someone who can see what each side meant.

## Where the truth lives

A localization project has at least three places that can claim to hold the current translation: the repository, a translation management system, and whatever the running product downloads. Research/05 assigns them roles: git is the source of truth for code, the TMS is the source of truth for translations. The same document then advises keeping a git-stored canonical copy of every catalog even behind a TMS or an over-the-air delivery network, so that the project is never locked into one vendor's database. The fl10n specification resolves the tension in favor of git. The canonical catalogs are versioned in the repository, and a TMS, if one is adopted, is a sync target that reads from and writes back to them.

The argument for git is not taste. A catalog in git has history, blame, review and a place in the same pull request as the code change that caused it. A catalog that lives only in a hosted service has whatever history the service keeps. Uren, Howard and Perinotti (1993) already asked for "a method of software configuration control" for localized releases sent to translation sites overseas, when several localized versions were in progress at once. The tool changed from shipped disks to branches; the requirement did not.

Git as the source of truth has one consequence that teams sometimes resist: every writer of a catalog, human or machine, must end in a commit. A reviewer who fixes a term in a web tool, an engine that fills unfinished messages, a developer who translates a new string while adding it: all three are writers, and all three must land in the same history.

## The localization branch pattern

Research/05 describes the arrangement most continuous projects converge on:

1. Developers work on feature branches and merge to `main`.
2. A merge to `main` uploads new source strings to the translation side.
3. Translations come back on one long-lived branch, named for the tool (`l10n_crowdin`, `lokalise-sync`, `weblate-translations` in the examples it cites).
4. A bot opens or updates a single pull request from that branch into `main`, which is squash-merged.
5. Bot commits carry a skip marker such as `[ci skip]` so that they do not trigger the pipeline that produced them.
6. The sync runs every 6 to 24 hours, with an immediate sync when a webhook reports a file as fully translated.

The same source suggests a threshold for outgrowing this pattern: if more than about ten percent of pull requests need conflict resolution, move to a per-feature-branch model, where each feature's strings travel with the feature. The fl10n specification uses the single-branch form, with one branch named `l10n_fl10n` and one squash-merged pull request.

The pattern works because it gives each catalog one writer at a time. Developers change source files and the extracted source catalog; the localization branch changes targets. Conflicts arise when that division breaks, and it breaks in predictable ways.

## Why translation files conflict

**Two writers change the same message.** A developer fixes a typo in a translation directly in `main` while the localization branch holds a reviewed version of the same message. Git sees two edits to one line and stops. Nothing in the file says which edit is the reviewed one.

**A tool rewrites bytes it did not need to touch.** An XML serializer that reorders attributes, changes quote style or re-escapes apostrophes turns a one-message change into a thousand-line diff. Any concurrent change anywhere in the file now conflicts. Part 3 treats this in [309. Byte-preserving edits](../3-formats/309-byte-preserving-edits.md). The vexy-localizzy upgrade is built on the same principle: its output starts from the fresh catalog's bytes and re-renders only messages whose content changed, so upgrading a file against itself returns identical bytes.

**The file format interleaves languages.** Research/05 prefers monolingual key files over bilingual XLIFF for fewer line-level conflicts, because a bilingual file places source and target side by side and a source change touches every language's copy. One catalog per locale, as Qt and gettext already use, keeps a German change out of the French file.

**A long-running branch outlives the source.** A translation branch that has been open for a week may carry translations of source strings that `main` has since changed. Git merges them cleanly, because the lines do not overlap, and the result is a correct translation of the wrong source. This is the dangerous case, because no conflict is reported.

The last case needs a check, not a merge tool. Research/05 recommends storing, for each machine-translated target, a hash of the source text together with the model and prompt version that produced it, and retranslating when any of them changes. Qt catalogs carry an equivalent signal in their own structure: an upgrade that matches a message by identity but finds its source changed does not treat the match as exact. It marks the message unfinished and keeps the previous source in an `<oldsource>` element, so a reviewer sees both versions side by side.

Research/04 records how serious this problem is in volunteer projects: KDE declined to replace its SVN workflow with Weblate out of concern about merge conflicts at high translator volume. The lesson for smaller teams is that conflict handling is not an edge case to be solved later. It decides which tools a project can adopt.

## A worked example: two copies of one catalog

In September 2026 the FontLab catalogs existed in two places. The approved catalogs, reviewed under issues 132, 133 and 145, lived in the fl10n project. The application repository held its own copy, where developers added strings and, for new messages, wrote translations themselves. When the application's copy was pulled, it held changes from a writer the review had never seen.

The first step was a report, not a merge. A small script compared the approved catalog with the application's catalog, pairing messages by the same identity the upgrade uses (context, source and disambiguating comment) and sorting every difference into four sections:

| Section | German count | Meaning |
|---|---|---|
| New, untranslated | 0 | Only in the application's catalog, with no target |
| New, translated | 73 | Only in the application's catalog, translated there |
| Changed | 2 | Same message in both, different target |
| Removed | 63 | Only in the approved catalog |

The approved catalog had 10,474 messages; the application's had 10,484. The 73 new translated messages were the ones to review, because nobody on the localization side had read them. The founder's review in issue 146 listed 35 corrections across the four languages, each stated as the current target and the target it should have.

One of those corrections shows how a message moves through branches. In the approved German catalog, the source "Descender to UPM" had a history of its own: the incoming translation *Unterlänge bis UPM*, an issue 132 correction to *Geviert ab Unterlänge*, and an issue 133 correction to *Unterlänge bis Gevierthöhe*. Meanwhile, in the application repository, a developer rewrote the English source as "UPM height from descender" and translated it as *UPM-Höhe ab Unterlänge*, which kept the loan *UPM* where issue 133 had chosen *Geviert* wording for German labels. By identity, this was a new message, and the old one had no match. A naive merge would have kept both catalogs' versions of different messages and reported no conflict at all.

The report made the situation visible, and the tools made it safe to act on:

- Each correction was checked against the exact prior target before it was applied. The review tooling of issue 145 goes a step further: when the live text no longer matches what the reviewer saw, it lists the correction as stale instead of overwriting the newer text.
- The corrected application catalogs became the new approved catalogs, and the 63 messages per language that no longer existed in the code were written to a retired file, named from the hashes of the two catalogs and never overwritten.
- The German result, *Gevierthöhe ab Unterlänge*, went into the review ledger with its prior text, so the next report can show where it came from. Ledgers are the subject of [410](../4-terminology/410-ledgers-and-decisions.md).

The retired German file still contains "Descender to UPM" with its reviewed translation. If the source ever returns, the translation can be harvested back into a memory rather than redone.

## Rules that keep conflicts small

- **One writer per file per branch.** If developers must write translations, route their changes through the same report and review as any other writer.
- **Compare before you merge.** A four-way report (new untranslated, new translated, changed, removed) tells you what a merge will do before git does it.
- **Guard every automated edit with its precondition.** Apply a change only while the text it replaces is still the text the reviewer saw.
- **Never delete a reviewed translation silently.** Retire it to a file that can be harvested later.
- **Record source identity with machine output.** A source hash, model and prompt version make stale translations detectable even when git reports no conflict.
- **Lock before release.** Research/05 suggests locking translation files during a release freeze through branch protection, so that the release branch receives only reviewed changes.

## Sources

- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (chapter 8: geography, configuration control)
- `research/05-format-conversion-cicd-and-continuous-localization.md` in the fl10n repository (sections 5.4.1, 5.4.4 and 5.4.5)
- `research/04-ai-driven-translation-and-quality-assurance.md` in the fl10n repository (section 4.9, KDE and GNOME)
- `spec/07.md` in the fl10n repository (sections 7.5 and 7.6)
- `docs/upgrade.md` in the vexy-localizzy repository
- `issues/146.md`, `CHANGELOG.md`, `WORK.md` and `scripts/diff_ts.py` in the fl10n repository
- `data-fontlab-cpp/i18n/review/README.md`, `2026-09-28-de-consistency.json` and `2026-09-29-issue-146.json` in the fl10n repository
- `.fl10n/diff/de.json` and `data-fontlab-cpp/i18n/retired/` in the fl10n repository
