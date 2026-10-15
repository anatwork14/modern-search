# ResearchOS desktop

Tauri 2 + React/TypeScript desktop shell for the local-first ResearchOS search service.

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
