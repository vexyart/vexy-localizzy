---
this_file: src_docs/md/8-toolkit/ci.md
---
# Continuous localization

The aim is to replace the string freeze with checks that run on every pull
request. A change that hides a string from `lupdate` fails the build the day
it is written, a layout that cannot grow shows up in a pseudo-locale, and a
broken placeholder never reaches a release. Only the deterministic steps
gate; the model-based ones run on a schedule and inform people.

The workflow below assumes the layout from [project configuration](project.md):
`localizzy.toml` at the repository root, sources in `src/`, extraction into
`i18n/fresh/` and reviewed catalogs `i18n/app_<code>.ts`.

## The pull-request gate

```yaml
# .github/workflows/localization.yml
name: Localization
on:
  pull_request:
    paths: ["src/**", "i18n/**", "localizzy.toml"]

permissions:
  contents: read
  security-events: write

jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Qt Linguist tools
        run: sudo apt-get update && sudo apt-get install -y qttools5-dev-tools
      - uses: astral-sh/setup-uv@v5
      - name: Install localizzy
        run: uv tool install vexy-localizzy
      - run: localizzy doctor

      - name: Scan the source
        run: localizzy qt scan src --min-coverage 0.8 --format sarif --out scan.sarif
      - name: Upload scan results
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: scan.sarif

      - name: Extract
        run: localizzy qt extract
      - name: Pseudo-locale
        run: |
          localizzy pseudo i18n/fresh/app_en.ts i18n/fresh/app_xx.ts
          localizzy qt release i18n/fresh/app_xx.ts
      - name: Check the reviewed catalogs
        run: |
          status=0
          for code in de fr; do
            localizzy qa "i18n/app_${code}.ts" --plural-forms auto \
              --format sarif --out "qa-${code}.sarif" || status=1
          done
          exit $status
      - name: Upload QA results (de)
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: qa-de.sarif
          category: qa-de
      - name: Upload QA results (fr)
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: qa-fr.sarif
          category: qa-fr
```

Install Qt explicitly: `localizzy doctor` reports what is missing and installs
nothing. The scan step exits 1 on any critical finding, as well as below the
coverage threshold, so the upload runs under `if: always()` and the findings
still appear as code-scanning alerts on the pull request. Pass the source
directory as a relative path, as here, so the alerts point at repository
paths. Code scanning on a private repository needs GitHub Advanced Security;
without it, drop the upload and keep `scan.sarif` as an artifact.

`qa` runs only on the reviewed catalogs. The freshly extracted ones fail by
design until every message has a target, and the pseudo catalog proves
nothing about language. Each QA result points at its catalog file, since a
message has no source line. Give every uploaded SARIF file its own
`category`, so the languages do not replace each other's alerts.

`qt extract` leaves the fresh catalogs in the working tree. Whether a job
commits them back, or a person runs [`project upgrade`](project.md) and
review locally, is a choice for each team; the gate itself writes nothing to
the repository.

## Drafts for review

With an engine key in the repository secrets, a job can prepare the next
upgrade for reviewers. One language per call; each call writes NEW, RETIRED
and a report, all unfinished where a model filled them:

```yaml
      - name: Upgrade drafts
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          uv tool install --force 'vexy-localizzy[translation]'
          for code in de fr; do
            localizzy project upgrade "$code" --model MODEL || [ $? -eq 1 ]
          done
      - uses: actions/upload-artifact@v4
        with:
          name: upgrade-drafts
          path: |
            i18n/*.new.ts
            i18n/upgrade/
            i18n/retired/
```

Exit 1 means some messages are still pending, which is expected for drafts;
the files are written either way. The engine settings come from `[translate]`
in `localizzy.toml`. The drafts
go to people through the [review](review.md) workspace, never straight to the
reviewed catalogs.

## The nightly judge

```yaml
on:
  schedule:
    - cron: "0 3 * * *"
  workflow_dispatch:

jobs:
  judge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv tool install 'vexy-localizzy[llm]'
      - name: MQM sample
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          for code in de fr; do
            localizzy qa "i18n/app_${code}.ts" --plural-forms auto --layers judge \
              --endpoint https://api.openai.com/v1 --model MODEL \
              --judge-sample 0.1 --fail-on critical \
              --format json --out "judge-${code}.json" || true
          done
      - uses: actions/upload-artifact@v4
        with:
          name: judge-reports
          path: judge-*.json
```

The judge never gates. `|| true` keeps one language's low scores from hiding
the others; the reports are for a person to read in the morning. The same job
is the place for a [golden-set comparison](vocabulary.md) when the model or
the prompt changes, and for an [editorial review](editorial.md) of a finished
catalog: its candidates file is an artifact for a person to read, and `apply`
stays a local step.

## What stays out of CI

Compiling `.qm` files for a release belongs to the build that packages the
application: commit `.ts`, ignore `.qm`. Approval belongs to people. No step
here marks a message approved.
