#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -z "${MODERN_SEARCH_PYTHON:-}" ]; then
  if [ -x ".venv/bin/python" ]; then
    MODERN_SEARCH_PYTHON="$(pwd)/.venv/bin/python"
  elif command -v python3.11 >/dev/null 2>&1; then
    MODERN_SEARCH_PYTHON="$(command -v python3.11)"
  else
    MODERN_SEARCH_PYTHON="$(command -v python)"
  fi
fi
export MODERN_SEARCH_PYTHON
"$MODERN_SEARCH_PYTHON" -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
for suite in contracts data embeddings retrieval security integration; do
  "$MODERN_SEARCH_PYTHON" -m unittest discover -s "tests/$suite" -v
done

(cd apps/desktop && npm test && npm run lint && npm run build)
qa_dir=$(mktemp -d)
trap 'rm -rf "$qa_dir"' EXIT HUP INT TERM
RESEARCHOS_DB_PATH="$qa_dir/empty.sqlite3"
export RESEARCHOS_DB_PATH
cargo test --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
cargo check --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
