#!/usr/bin/env bash
# this_file: src_docs/deploy.sh
#
# Publish the built book (docs/fl1992mk) to https://fontlab.dev/vexy-localizzy/fl1992mk/.
# fontlab.dev is served by GitHub Pages of the Fontlab organization, one repository per
# path, so the site lives in the docs-only repository Fontlab/vexy-localizzy (source of
# the book stays here, in vexyart/vexy-localizzy). Run src_docs/build.sh first.
set -euo pipefail
SRC="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )/docs/fl1992mk"
PAGES="${VEXY_LOCALIZZY_PAGES:-$( cd "$( dirname "${BASH_SOURCE[0]}" )/../../../github.fontlab/vexy-localizzy" && pwd )}"
[ -d "$SRC" ] || { echo "build the site first: src_docs/build.sh" >&2; exit 2; }
rsync -a --delete "$SRC/" "$PAGES/docs/fl1992mk/"
touch "$PAGES/docs/.nojekyll"
cd "$PAGES"
git add -A docs
if git diff --cached --quiet; then echo "pages repository already up to date"; exit 0; fi
git commit -q -m "Publish the localization book ($(date +%Y-%m-%d))"
git push
