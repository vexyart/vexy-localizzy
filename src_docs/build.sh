#!/usr/bin/env bash
# this_file: src_docs/build.sh
#
# Build or serve the vexy-localizzy book (ProperDocs + MaterialX over MkDocs).
#
# Usage:
#   src_docs/build.sh          # strict build into docs/fl1992mk
#   src_docs/build.sh serve    # local preview on :8000
#   src_docs/build.sh check    # markdown checks only (no dashes, banned words, headers)

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

COMMAND="${1:-build}"

run_uv() {
  uv run --project tooling/python --locked "$@"
}

check_markdown() {
  run_uv python3 - <<'PY'
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
    run_uv properdocs build --strict -f mkdocs.yml
    ;;
  serve)
    run_uv properdocs serve -f mkdocs.yml
    ;;
  check)
    check_markdown
    ;;
  *)
    echo "usage: $0 [build|serve|check]" >&2
    exit 2
    ;;
esac
