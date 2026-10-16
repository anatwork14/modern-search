# Quick Search UI — Gemini-inspired compact desktop launcher

## What changed

This is a **search launcher**, not a chatbot. The macOS app opens as a small rounded, frameless search card, visually modeled on the supplied Gemini reference: large input, minimal action rail, one prominent blue submit button, and a Search/Filters segmented control. Search results and advanced filters expand in the same window. No fake microphone, screen-sharing, task execution, or remote AI controls.

- Search on Enter (or Command/Ctrl+Enter), focus/select input with Command/Ctrl+K.
- Fast = STRICT lexical-only (default); Hybrid = BROAD lexical + optional local semantic retrieval from the action rail; BOTH preserve the exact eligibility and taxonomy constraints.
- Use + or Filters for source, eligibility, and repeatable ANY/ALL/NOT facets. Default eligibility remains **verified-qualified**. The imported source's unknown papers require explicit opt-in.
- Search results expose match routes, tag review states, source links, venue evidence, and PDF availability. Dense fallback warnings and fictional browser-preview labels remain visible.
- Escape closes filters; results can be collapsed. Native window grows only for results/options and recenters.
- Search and records remain on-device in Tauri. Browser Vite preview uses fictional mock examples and cannot query the private index.

## Technical notes

Files: `apps/desktop/src/App.tsx`, `App.css`, `index.css`, `App.test.tsx`, `src-tauri/tauri.conf.json`, and `src-tauri/capabilities/default.json`. No retrieval contract, schema, or backend behavior changed.

Native window requires Tauri window permissions for set-size, center, close and drag. The transparent, undecorated window uses an explicit draggable strip and Close button; because the app has no global shortcut yet, users reopen it via the Dock/launcher.

## Acceptance gates

- Run `cd apps/desktop && npm ci && npm test && npm run lint && npm run build`.
- Run `./scripts/check.sh` from the repository root with the documented Python environment.
- On macOS, manually verify rounded transparency and native drag/close, expand/collapse, keyboard-only input, on-device real search, and usability on a small display.
- Measure search latency (including process startup) **separately**. This PR reduces visual friction; it does not claim measured retrieval speed gains. The Python worker is still launched per RPC.

## Follow-up

A global reveal shortcut (e.g. Option+Space), tray/menu bar control, and a resident search service are separate design/performance tasks requiring independent platform and latency testing.

## Release and performance notes (2026-10-16)

The Tauri .app bundles the Python backend **source and SQLite migrations**, allowing the Rust bridge to locate it without a source checkout. This is **not yet a self-contained Python runtime**: Python 3.11+ must be installed on the Mac. Finder-launched apps try common Homebrew Python paths; `MODERN_SEARCH_PYTHON` remains the explicit override when launching from a terminal. Optional dense retrieval has its own local ML dependencies and cached model weights; without them Fast mode remains available. Signing/notarization is still outside this development PR. True transparent macOS windows use Tauri's `macos-private-api` feature (unsuitable for the Mac App Store).

Persistent stdio worker and in-memory FTS catalog are reused across requests. External SQLite imports invalidate the snapshot via `PRAGMA data_version`; atomic DB replacement is detected via filesystem identity. Rust bounds request and response frames and resets a failed/timed-out worker. No HTTP service or user data upload is introduced.

Measure actual latency on your imported corpus (do not infer performance from a UI redesign):

```sh
python scripts/benchmark_search.py --db "$HOME/Library/Application Support/ResearchOS/catalog.sqlite3" --mode STRICT --query "attention" --iterations 20
```

Results report measured cold and warm p50/p95 milliseconds plus sample count. The global system-wide hotkey and signed independent Python runtime remain separate future tasks; only in-window Command-K is implemented in this PR.
