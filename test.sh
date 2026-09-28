#!/usr/bin/env bash
# this_file: test.sh
set -euo pipefail
cd "$(dirname "$0")"
uv run --extra llm --extra sources --extra embeddings --extra clustering --extra translation --extra review ruff check src tests examples scripts
uv run --extra llm --extra sources --extra embeddings --extra clustering --extra translation --extra review ruff format --check src tests examples scripts
uv run --extra llm --extra sources --extra embeddings --extra clustering --extra translation --extra review pytest
npm --prefix icu test
npm --prefix review test
npm --prefix review run build
