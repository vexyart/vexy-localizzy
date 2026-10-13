#!/usr/bin/env bash
# this_file: src_docs/build.sh
#
# Build or serve the vexy-localizzy book (ProperDocs + MaterialX over MkDocs).
#
# Usage:
#   src_docs/build.sh          # markdown checks, then strict build into ../docs
#   src_docs/build.sh serve    # local preview on :8000
#   src_docs/build.sh check    # markdown checks only (no dashes, banned words, headers)
#   src_docs/build.sh --docs [properdocs build options]   # plain build, no checks
#
# Needs only uv (uvx): every tool runs from pinned packages, so the same command
# works locally and in .github/workflows/docs.yml.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

COMMAND="${1:-build}"

# Run a command inside the pinned ProperDocs + MaterialX tool environment.
docs_uvx() {
  uvx --python 3.13 --from properdocs==1.6.7 \
    --with mkdocs==1.6.1 \
    --with mkdocs-materialx==10.1.8 \
    --with mkdocs-glightbox==0.5.2 \
    --with vexy-mkdocs-strip-number-prefix==1.0.12 \
    --with mkdocs-awesome-nav==3.3.0 \
    --with pymdown-extensions==11.0.1 \
    --with Markdown==3.10.2 \
    --with mkdocs-material-extensions==1.3.1 \
    "$@"
}

check_markdown() {
  docs_uvx python - <<'PY'
import re, sys
from pathlib import Path
banned = ("delve", "leverage", "seamless", "robust", "pivotal", "crucial", "comprehensive",
          "transformative", "game-changing", "cutting-edge", "meticulous", "vibrant", "intricate",
          "nuanced", "holistic", "ever-evolving", "tapestry", "landscape", "realm", "journey",
          "ecosystem", "synergy", "interplay", "elevate", "unlock", "unleash", "harness", "empower",
          "foster", "underscore", "showcase", "garner", "bolster")
banned_re = re.compile(r"\b(" + "|".join(map(re.escape, banned)) + r")(s|es|d|ed|ing)?\b", re.I)
problems = 0
files = sorted(Path("md").rglob("*.md"))
for path in files:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\nthis_file: "):
        print(f"FAIL {path}: missing this_file frontmatter"); problems += 1
    for n, line in enumerate(text.splitlines(), 1):
        if "—" in line or "–" in line:
            print(f"FAIL {path}:{n}: dash"); problems += 1
        m = banned_re.search(line)
        if m and not line.startswith("    ") and not line.startswith("```"):
            print(f"FAIL {path}:{n}: banned word {m.group(0)!r}"); problems += 1
print(f"{len(files)} files checked, {problems} problem(s)")
sys.exit(1 if problems else 0)
PY
}

case "${COMMAND}" in
  build)
    check_markdown
    docs_uvx properdocs build --strict -f mkdocs.yml
    touch ../docs/.nojekyll
    ;;
  --docs)
    shift
    export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
    docs_uvx properdocs build --config-file mkdocs.yml "$@"
    touch ../docs/.nojekyll
    ;;
  serve)
    shift
    docs_uvx properdocs serve -f mkdocs.yml "$@"
    ;;
  check)
    check_markdown
    ;;
  *)
    echo "usage: $0 [build|serve|check|--docs ...]" >&2
    exit 2
    ;;
esac
