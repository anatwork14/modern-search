# ResearchOS desktop

Tauri 2 + React/TypeScript desktop shell for the local-first ResearchOS search service.

The shared header mark and browser favicon use `public/researchos-icon.svg`. The Tauri bundle icons are generated from that same vector source so platform assets stay aligned:

```sh
npm run tauri -- icon public/researchos-icon.svg --output src-tauri/icons
```

## Development

Use Node 22 and Python 3.11 or newer. From this directory:

```sh
npm ci
npm test
npm run build
```

The browser preview opens in an explicitly labeled **Demo mock** source. The fictional records are UI fixtures only. Select **Local library** only inside Tauri; a plain browser cannot access the local service.

To run the macOS shell from the repository root, set the local toolchain paths and start Tauri:

```sh
export PATH="/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:$PATH"
export MODERN_SEARCH_PYTHON="/opt/homebrew/bin/python3.11"
cd apps/desktop
npm run tauri dev
```

The Rust host launches `python3 -m backend.service` from the fixed repository root, using one JSON request and one JSON response over stdio. It does not use a shell or accept an executable, working directory, database path, or service path from the renderer. `MODERN_SEARCH_PYTHON` and `RESEARCHOS_DB_PATH` are host-process configuration only.

Release packaging is not qualified: the Python service and its resources must be explicitly bundled and tested before a packaged app can launch it.

## Native QA checkpoint

On 2026-10-15, the integrated macOS debug `.app` was built and launched from the source checkout with a host-selected Python runtime, local catalog, and matching local dense index. The native UI reported 2,478 indexed papers. The default **Verified qualified** search returned 0; opting into **Unknown** and running a broad `attention` search returned 2,478 candidates with both lexical and semantic match routes. A strict `field` facet using `ALL` with `field/federated-learning` and `field/large-language-models` returned 0. Result cards displayed venue, ranking vintage, and source URLs as source-reported evidence, with an explicit note that the evidence was not independently verified by this view. These checks verify native IPC and rendering, not search relevance quality.

Reproduce the debug bundle build from this directory with `npm run tauri build -- --debug --bundles app`. To launch it, configure `MODERN_SEARCH_PYTHON`, `RESEARCHOS_DB_PATH`, and (when using dense search) `RESEARCHOS_INDEX_PATH` in the host environment, then run `src-tauri/target/debug/bundle/macos/ResearchOS.app/Contents/MacOS/researchos-desktop`. The Rust host anchors the service to the source checkout; it does not bundle Python or the service in the app. A portable release bundle remains unqualified until those runtime resources are explicitly packaged and validated.

The Rust stdio smoke test invokes the real Python service for health, taxonomy, and search. Run it with a disposable empty database path so it verifies the child-process protocol without depending on the private catalog:

```sh
smoke_dir="$(mktemp -d)"
RESEARCHOS_DB_PATH="$smoke_dir/catalog.sqlite3" \
MODERN_SEARCH_PYTHON="/opt/homebrew/bin/python3.11" \
cargo test --manifest-path src-tauri/Cargo.toml
```
