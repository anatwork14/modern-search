# Quick Search UI — Gemini-inspired compact desktop launcher

## What changed

This is a **search launcher**, not a chatbot. The macOS app opens as a small rounded, frameless search card, visually modeled on the supplied Gemini reference: large input, minimal action rail, one prominent blue submit button, and a Search/Filters segmented control. Search results and advanced filters expand in the same window. No fake microphone, screen-sharing, task execution, or remote AI controls.

- Search on Enter (or Command/Ctrl+Enter), focus/select input with Command/Ctrl+K.
- Fast = STRICT lexical-only (default); Hybrid = BROAD lexical + optional local semantic retrieval from the action rail; BOTH preserve the exact eligibility and taxonomy constraints.
- Arrow Down / Arrow Up navigates search results smoothly with visual selection and auto-scroll.
- Enter on a selected result opens its source URL or toggles evidence/tags.
- Copy actions on every card: "Copy citation", "Copy title", "Copy DOI" with instant feedback.
- Escape dismisses filters -> collapses expanded results -> hides floating window.
- Control + Command + Shift + M (`⌃⌘⇧M`) global shortcut summons or hides the floating launcher from any desktop application.
- Clicking the macOS Dock icon restores and focuses the search window via native `RunEvent::Reopen`.
- Native Light and Dark appearance support via `@media (prefers-color-scheme: dark)` adhering to macOS system theme.
- Fixed window positioning without jarring re-centering jumps on size changes.
- Search and records remain on-device in Tauri. Browser Vite preview uses fictional mock examples and cannot query the private index.

## Technical notes

Files: `apps/desktop/src/App.tsx`, `App.css`, `index.css`, `App.test.tsx`, `src-tauri/tauri.conf.json`, `src-tauri/src/lib.rs`, and `src-tauri/capabilities/default.json`. The public search RPC/schema remains unchanged.

Internally, relational exports (`export_papers`, `export_tags`) use bulk relational queries instead of N+1 loops, `_build_fts` uses transactional `executemany` batches, and session caches reuse prepared dictionaries.

Window management allows smooth expansion without recentering jarringly on each keystroke. The window can be hidden without exiting, keeping the persistent backend worker primed.

## Keyboard shortcuts

| Shortcut | Context | Action |
|---|---|---|
| `Enter` | Search input | Execute search query |
| `Enter` | Selected result | Open paper source link or toggle details |
| `⌘K` / `Ctrl+K` | Anywhere | Focus and select search input |
| `Arrow Down` | Results list | Select next paper result |
| `Arrow Up` | Results list | Select previous paper (or return to search input) |
| `Escape` | Active options | Close options panel |
| `Escape` | Active search | Dismiss expanded results, return to launcher |
| `Escape` | Idle launcher | Hide window (on macOS desktop) |
| `⌘C` / `Ctrl+C` | Selected result | Copy formatted bibliographic citation to clipboard |
| `Control + Command + Shift + M` | Global system | Toggle summon / hide Modern Search launcher |

## Acceptance gates

- Run `cd apps/desktop && npm ci && npm test && npm run lint && npm run build`.
- Run `./scripts/check.sh` from the repository root with the documented Python environment.
- On macOS, manually verify rounded transparency and native drag/close, expand/collapse, keyboard-only input, on-device real search, and usability on a small display.
- Measure search latency (including process startup) with `scripts/benchmark_search.py --suite` on a real imported catalog.

## Measured performance (2,478 papers on Apple Silicon)

| Query Category | Query String | Mode | Cold Spawn (p50) | Persistent (p50) | Persistent (p95) |
|---|---|---|---|---|---|
| Exact title | Attention Is All You Need | STRICT | 73.66 ms | 0.90 ms | 1.81 ms |
| DOI identifier | 10.18653/v1/2026.acl-long.930 | STRICT | 76.57 ms | 0.95 ms | 1.03 ms |
| arXiv identifier | 1706.03762 | STRICT | 81.70 ms | 5.83 ms | 5.99 ms |
| Short keyword | federated | STRICT | 68.20 ms | 3.27 ms | 3.38 ms |
| Multi-keyword | federated continual learning intrusion detection | STRICT | 67.67 ms | 0.53 ms | 0.56 ms |
| Vietnamese query | học máy phân tán | STRICT | 69.92 ms | 0.55 ms | 0.63 ms |
| Natural language | mitigate catastrophic forgetting in decentralized systems | STRICT | 70.56 ms | 0.55 ms | 0.60 ms |
| Empty match | xyznonexistentquery987654321 | STRICT | 71.11 ms | 0.51 ms | 0.54 ms |
| Broad semantic | transformer attention mechanisms | BROAD | 70.18 ms | 0.54 ms | 0.57 ms |
| Repeated | attention | STRICT | 69.67 ms | 3.28 ms | 3.34 ms |
| **Overall** | *Representative Taxonomy* | — | **70.56 ms** | **0.73 ms** | **5.99 ms** |


## Screen-safe integrated layout (2026-10-17)

The original screenshot showed three disconnected surfaces: a large search pill, separate floating tabs/status, and a filter panel clipped behind the Dock. The updated desktop uses **one unified rounded card** containing search input, compact tabs/status, and a flex-scrolling results or filter area. All content must remain inside the card, not transparent window space.

The Tauri window is 780 × 270 logical pixels when compact. Results/filters expand up to 680 logical pixels **bounded by the active monitor work area** (excluding menu bar/Dock), and the window moves up before growing if needed. Filters and results scroll *inside* the rounded card; action/footer controls stay visible. Switching Search ↔ Filters, Enter, Esc, Cmd+K, copy actions and hard eligibility filtering remain functional.

**Acceptance is not just CI:** on the owner's Mac, verify the compact and expanded states while the Dock is visible, external monitor placement, small screens, light/dark modes, keyboard-only interactions and pointer interactions. Record screenshots from a real WindowServer session. Automated UI tests prove DOM containment but cannot confirm native macOS geometry.

## Real paper discovery UX (2026-10-17)

Backend health now returns exact per-eligibility counts so an imported-but-unreviewed catalog does not appear broken. If zero records are verified-qualified and unknown imported candidates exist, the initial client scope is clearly **Unverified papers** (the owner may switch back to Verified only at any time). This is a visible scope choice; requests still send exactly one eligibility filter without automatically widening a submitted query. Result badges distinguish scholarly **eligibility** from separate review state.

Idle local search provides **Browse library** (empty-query search). A no-match screen provides an explicit candidate-scope switch when appropriate, browse in the selected scope, filter review and single-keyword links; users must choose any widening. A no-index Hybrid mode must disclose lexical-only fallback rather than imply semantic recall.

For multiword zero-results, **Try broader keywords** explicitly switches to BROAD, which relaxes lexical query term conjunction to an OR group but retains any exact quoted phrase constraints, DOI/arXiv lookup and all hard filters. This is not an automatic filter relaxation; source eligibility and tag rules remain exact. Missing dense embeddings are reported as lexical fallback.
