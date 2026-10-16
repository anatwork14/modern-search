# ResearchOS / modern-search

A local macOS research catalog with a Tauri 2 desktop interface, SQLite provenance, offline lexical search, strict taxonomy filters, and optional EmbeddingGemma 2 hybrid retrieval.

**Development MVP, 2026-10-15.** The canonical source was imported locally: 1,616 tags, 2,478 papers and 3,197 paper/tag assertions. These are discovery candidates: every imported paper remains `unknown` eligibility, and no PDF has been verified locally. The default qualified-only search therefore returns zero until a separate review establishes qualification. Select unknown/exploratory explicitly to browse the imported candidates. See [progress.md](progress.md) for executed gates and remaining work.

## Run on macOS

Requires Python 3.11+, Node 22, Rust stable and Apple's Command Line Tools. Run commands from the repository root. Source documents, SQLite files and model weights are private local inputs and are not included in Git.

```sh
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install jsonschema==4.26.0
cd apps/desktop
npm ci
cd ../..
```

Import a local copy of the canonical XLSX workbook, or a catalog JSON snapshot conforming to the importer fixtures:

```sh
python -m backend.cli /absolute/path/catalog.xlsx \
  --source-id 'drive:1aFPn80GxpTaapzMnIc6dJlE1esn0W9Lk'
```

The default database is `~/Library/Application Support/ResearchOS/catalog.sqlite3`. `--source-revision` defaults to the input SHA-256; repeat imports preserve identity, row provenance and stronger local review decisions. An unavailable supplementary archive does not block workbook ingestion. Imports never download PDFs or promote source assertions into verified evidence.

Launch the native development app from the same activated shell:

```sh
export MODERN_SEARCH_PYTHON="$(command -v python)"
# Optional host-only overrides: RESEARCHOS_DB_PATH and RESEARCHOS_INDEX_PATH.
cd apps/desktop
npm run tauri dev
```

The Rust bridge starts an anchored Python stdio service for each request. There is no listening backend port. Browser-only `npm run dev` uses an explicitly labeled fictional demo; use Tauri for the real local catalog. Search supports literal terms, phrases, DOI/arXiv identity, and ANY/ALL/NOT tags with AND across facets. STRICT uses lexical retrieval; BROAD fuses lexical and available dense ranks using RRF. Missing or stale dense indexes preserve lexical search with a visible warning. Metadata remains source asserted; abstracts, PDF pages and evidence are shown as unavailable when absent.

## Optional semantic search

Model installation requires a deliberate network download. Runtime encoding is cache-only. Install the tested optional runtime into the active Python environment and cache the complete pinned checkpoint:

```sh
python -m pip install -r backend/embeddings/requirements.txt
python -c "from huggingface_hub import snapshot_download; snapshot_download('google/embeddinggemma-2', revision='914f7f89142e33e77833254d9c9b90c3cef7303b')"
python -m backend.cli /absolute/path/catalog.xlsx \
  --source-id 'drive:1aFPn80GxpTaapzMnIc6dJlE1esn0W9Lk' --build-index
```

The index is atomically written beside the database with suffix `.dense.json`. Rebuild after corpus changes; manifest/corpus mismatch blocks dense use. Run only one model build/probe at a time on a memory-constrained Mac. This source has no abstracts: its current embeddings represent titles only. MPS and CPU compatibility were measured on Apple Silicon with 16 GiB RAM; these smoke measurements do not establish retrieval relevance. See [embedding measurements](docs/benchmarks/embeddinggemma2-compatibility.md).

## Verify

```sh
. .venv/bin/activate
./scripts/check.sh
```

The script runs Python contracts/data/embedding/retrieval/security/stdio tests, frontend tests/lint/build, and a Rust bridge test against a disposable empty database. Unit tests do not download model weights. GitHub Actions repeats these checks on macOS.

A debug app can be built with `npm run tauri build -- --debug --bundles app` from `apps/desktop`. It remains a checkout-dependent development artifact. A self-contained signed/notarized release, PDF extraction, relevance gold-set comparison and advanced research extensions remain unqualified or deferred.

## Project references

- [Agent instructions](AGENTS.md), [parallel setup](START_HERE.md), [integration contracts](docs/contracts/MVP_V1.md)
- [Product](docs/PRODUCT_SPEC.md), [architecture](docs/ARCHITECTURE.md), [data](docs/DATA_AND_TAXONOMY.md), [retrieval](docs/RETRIEVAL_SPEC.md)
- [Privacy](docs/SECURITY_PRIVACY.md), [evaluation](docs/EVALUATION_AND_TESTS.md), [source audit](docs/audits/)
- [Canonical workbook](https://docs.google.com/spreadsheets/d/1aFPn80GxpTaapzMnIc6dJlE1esn0W9Lk/edit), [source folder](https://drive.google.com/drive/folders/1tUj_kTXYSAuBCXlnGNK-HpUQBfn5r7R1)

## Research workspace precise Paper_ID lookup (optional branch feature)

The companion [research workspace PR #3](https://github.com/anatwork14/research/pull/3) can call a new `get_paper` local JSON-stdio command (implemented by [PR #16](https://github.com/anatwork14/modern-search/pull/16), not available on older main builds):

```json
{"version":1,"id":"paper-1","command":"get_paper","payload":{"paper_id":"P-original-1"}}
```

It performs a parameterized lookup on SQLite primary-key Paper_ID, returns the existing catalog record (or found:false), and flags `catalog-metadata-only`. It **does not** return PDF page evidence, verify Q1 venue, or perform any catalog mutation. See `docs/contracts/RESEARCH_WORKSPACE_READONLY_V1.md` and contract/integration tests.
