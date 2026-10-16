#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
MODERN_SEARCH_PYTHON="$(command -v python)"
export MODERN_SEARCH_PYTHON
for suite in contracts data embeddings retrieval security integration; do
  python -m unittest discover -s "tests/$suite" -v
done
(cd apps/desktop && npm test && npm run lint && npm run build)
qa_dir=$(mktemp -d)
trap 'rm -rf "$qa_dir"' EXIT HUP INT TERM
RESEARCHOS_DB_PATH="$qa_dir/empty.sqlite3"
export RESEARCHOS_DB_PATH
cargo test --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
cargo check --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
