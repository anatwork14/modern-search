# Modern Search — v1.0 Daily-Driver Finish Line

**Created:** 2026-10-17. **Owner:** human repository owner. **Execution lead:** coding agent.
**Status:** GOAL DEFINED; NOT YET RELEASE-ACCEPTED.
**Baseline:** `main` commit `17ae3641d2aa68c4f92645674d3090d90fb4379d` (PR #18).
**Single current mission:** take the already merged Fast Search MVP to a **trustworthy, enjoyable, self-contained macOS daily-driver v1.0**, then **stop**. This is not a mandate to implement every idea in docs/PRODUCT_SPEC.md.

## 0. Precise product promise

> From Finder or a global keyboard shortcut, the owner can open Modern Search, type a Vietnamese/English research-paper search or DOI, immediately see accurate and clearly qualified *local-catalog* results, inspect/copy/open the result, and dismiss the window — with no dev terminal or network needed during ordinary search.

The app must **not** pretend that source-reported bibliographic data, Q1/Q2 qualification, PDFs, abstracts, page citations, semantic retrieval or experimental performance have been verified when they have not.

### Already implemented, do not rebuild without evidence

- PR #17: floating Fast/Hybrid launcher, local persistent Python stdio RPC, prepared FTS cache, filters, provenance.
- PR #18: macOS hotkey, focus/lifecycle, dark styling, result navigation/copy actions, bulk SQLite export and 10-category benchmark.
- Repo-reported **warm backend RPC** p50 0.73 ms and highest measured per-query p95 5.99 ms for a 2,478-paper imported catalog. **Not UI end-to-end latency**; not verified semantic relevance.
- PR #16 (read-only Paper_ID bridge) remains a separate draft; **do not merge or modify it** without an explicit dependency review and approval.

## 1. Scope, priorities and non-goals

**P0 (required for completion):** safe real-data first-run path; correct local search; useful explicit discovery/verified modes; native-window/shortcut/lifecycle correctness; zero accidental network transfer; reproducible Mac app launched outside checkout; current-head passing CI; user-tested Mac acceptance.

**P1 (required if feasible with bounded complexity, otherwise document and obtain owner's acceptance):** no-terminal startup for ordinary use; clear offline/dense availability; keyboard and screen-reader accessibility; deterministic relevance evaluation and end-to-end latency evidence; recovery from worker failure and database refresh; small-screen and multi-monitor usability.

**P2 (not a finish blocker):** full PDF acquisition/OCR, scholarly cross-domain concept graph, annotations/reading lists, Zotero/Drive sync, autonomous paper download, agent-facing plugin API, notebook/LLM chat, cloud telemetry, paid model APIs, App Store distribution, Mac notarization. These need explicit new scope. Do not confuse the broad historical ResearchOS roadmap with the v1.0 Fast Search finish line.

**Privacy:** local by default; no telemetry; no posting queries, PDFs or credentials; optional model download is explicit; external source links open only on deliberate user action. No uploads or modifications to Google Drive or the user's real catalog without consent.

## 2. Finish-line gates (each needs evidence, not assertion)

### FL-00 — Reconcile reality and establish owner-visible baseline (P0)

- Read AGENTS.md, this file, README.md, progress.md, current code, CI and open PRs.
- Check main SHA, latest passing CI, clean local checkout, development and installed-app startup paths; identify machine architecture and toolchain.
- Run ./scripts/check.sh; record commands and their exact output in the final report or references.
- Separately measure Python-backend RPC and **user-perceived Enter-to-results** latency; do not equate the reported 0.73 ms warm worker result with full UI latency.
- Record available real local catalog and model assets; NEVER conclude files exist because README or Drive inventory names them.
- Determine if the host offers graphical macOS access, screen capture and a physical Mac. Mark unavailable checks BLOCKED rather than fabricated.

### FL-01 — Working daily-use window on macOS (P0)

- Test actual **built .app launched from Finder**, not just Vite browser and Tauri dev.
- Verify window transparency/rounded clipping/shadow, initial focus, drag target, hide/show, Dock reopen, Option+Space conflict/graceful fallback, Escape, Cmd+K, keyboard-only search and result actions.
- Exercise light/dark, Retina scaling, at least one smaller Mac display and multi-monitor/window-bounds behavior where devices are available.
- Preserve active search state sensibly; don't spawn redundant Python processes or leave zombie workers after quit.
- Fix bugs with regression tests and capture real screenshot or video evidence. CI success alone is **not** visual acceptance.
- Disable/move unsafe shortcuts when ordinary text input, selection, clipboard or other applications would break.

### FL-02 — Real catalog onboarding and coverage (P0)

- First-run states must explicitly distinguish **no DB**, **empty indexed DB**, **real candidate papers present**, **no locally verified eligible papers**, **offline dense unavailable**, **index stale** and **backend missing**.
- Implement the shortest safe import/onboarding route: a minimal local import flow, or clear one-time guided setup if a picker would cause unreasonable complexity. Existing CLI remains supported.
- Imported candidate papers are source asserted and initially `unknown`. The currently default `verified-qualified` scope can legitimately return zero. Provide **explicit discovery-mode opt-in**, visible persistent mode labeling and an easy way to return to qualified-only. Never silently widen strict filters.
- Index freshness must reflect external commits/atomic replacement; repeated imports must preserve stable Paper_ID and user verification metadata.
- Validate with both disposable fixture and — **only if the owner has supplied access** — real 2,478-paper catalog. Never copy private DB/PDF contents into commits, CI artifacts or issue bodies.
- If qualification remains unknown for the imported catalog, call it **candidate search**, not verified scholarly discovery; do not manufacture qualification.

### FL-03 — Search correctness + measured usefulness (P0)

- Verify exact DOI/arXiv lookup, paper-title lookup, Vietnamese terms, English terms, phrase matching, short/acronym queries, empty results, valid/invalid tag expressions, deterministic pagination and safe URL actions.
- Enforce ANY/ALL/NOT, exclusion filters and qualification constraints; impossible exact intersections stay empty.
- Maintain a versioned evaluation fixture: at least **30 hand-judged queries** (include 10 identities/titles, 10 domain-topic queries, 5 Vietnamese queries and 5 negative/filter cases). Expand to 60–100 before asserting general academic relevance. Record relevance grades, source/snapshot, judging limitations and top-k results.
- **Acceptance:** 100% known-existing DOI/arXiv fixture identities resolve to the intended paper; no false verification or hard-filter violations; no correctness regression vs main baseline. Report nDCG@10 / MRR@10 / Recall@k where judgments support them, even if relevance is unsatisfactory. Do not tune on the test set and call it generalization.
- Validate Fast lexical mode alone. Hybrid is truly semantic **only when the pinned model, dense index and compatible corpus are present and successfully used**. If missing, make lexical-only fallback explicit; do not claim Hybrid semantic success because the mode label exists.

### FL-04 — Speed and resilience on representative hardware (P0)

- Capture Mac chip, RAM, macOS, tool versions, paper/tag counts, corpus/index revision and query set.
- Measure **cold Finder launch → input usable**, first query, warm UI Enter → stable painted results, p50/p95 across >= 30 trials per relevant scenario, Python worker CPU/RSS, optional Hybrid warm-up.
- Reference target for 2.5k-paper Apple Silicon catalog: warm Fast **p95 ≤ 250 ms end-to-end UI** and launch-to-input **≤ 3 s** as *goals*, not pre-claimed results. Backend warm worker should not regress materially from the PR #18 measured baseline. If limits are missed, profile and optimize until reasonable or explain tradeoffs for owner approval.
- Test >= 100 back-to-back searches; rapid query replacement; worker kill/restart; stale response protection; 30-second timeout; DB changes while app is open; corrupt/missing/mismatched dense index; offline network blocking. No zombie workers, lost data or unbounded memory growth.
- No unnecessary polling, heavyweight model loading in Fast mode or hidden network downloads.

### FL-05 — Reliable local installation and Finder launch (P0)

- Produce a **reproducible macOS `.app`** using locked tooling, bundled backend source/migrations and deterministic resource resolution outside the source checkout.
- **Preferred v1:** bundle a compatible isolated Python runtime so first launch does not depend on Homebrew PATH. Audit license, size and code-signing implications; if not feasible in bounded time, demonstrate and document a tested one-time Python install with no terminal needed for everyday use, and flag owner acceptance required before declaring v1 complete.
- Validate with a clean macOS user profile or comparable fresh environment; include install/update/uninstall steps, app-data safety, recovery and migration compatibility. Never overwrite or delete the real user database during testing.
- Include visible diagnostics when runtime, permissions, local index or data are unavailable; privacy-safe error detail and recovery. Do not bury all failures behind a generic blank window.
- Distribution via public signed/notarized installer is NOT automatically in scope; do not claim the app is notarized/signed unless actually done.

### FL-06 — Evidence, CI, and release handoff (P0)

- Ensure GitHub Actions tests PRs **and current main pushes**; validate macOS build + backend resources with a reproducible smoke and appropriate offline contract checks. Running Cargo compile does not prove native GUI interactions.
- Document tested paths in README, add a succinct real local usage guide and troubleshooting; remove/mark stale "not implemented" statements only when truly superseded.
- Ship a `docs/release/FINAL_ACCEPTANCE.md` or equivalently concise evidence report: check ID, execution environment, observed result, artifact/screenshot/log hash or CI URL, reviewer/owner acceptance and open known issues. Keep private paths and data out of public artifacts.
- Final branch through current-head green CI → PR review → merge to `main` → verify merge SHA and files on `main`. Do not push directly to main or force-merge blocked checks. Scope only intended feature work; PR #16 remains separate.
- For a local personal v1, the human owner must confirm a **real Finder launch + actual search** at least once, or a delegated physical-Mac agent must supply trustworthy visible evidence. Without it label status **CODE COMPLETE / WAITING FOR REAL MAC ACCEPTANCE**, not FINISHED.
- Create version tag/release only after final acceptance and explicit owner authorization to publish downloadable binaries.

## 3. State machine and measurable stop condition

Each FL task has one of: TODO, IN_PROGRESS, BLOCKED, DONE.

A task is DONE only with: merged implementation if needed; tests passing; recorded environment; reproducible proof; zero known high-severity regression. Do not silently change acceptance criteria to make a task pass.

**FINISHED means ALL of:** FL-00 through FL-06 are DONE; no unresolved P0/P1 correctness or privacy bug; latest target-branch CI green; merge SHA verified; real native Mac/Finder + catalog smoke accepted; independent v1 usability demonstrated; private source content protected; final report linked. A P2 backlog can remain without blocking FINISHED.

**If an external prerequisite cannot be fulfilled:** implement everything independent of it, ask owner once for the exact access/action, mark blocked gate and stop claiming completion. Do not promise autonomous background execution without a scheduler.

## 4. Agent orchestration and bounded autonomy

### Lead / integrator (one owner)

- Owns GOAL.md interpretation, progress.md FL task ledger, backlog ordering, CI, protected dataset handling, PR merge and final report.
- Delegates non-overlapping worktrees when useful: (A) macOS native and launcher, (B) retrieval/correctness/benchmark, (C) installer/onboarding, (D) QA/review. No two agents edit the same files or progress.md at once.
- Before each block of work, inspect live branch/PR state; don't assume prior conversations are current.
- Execute one goal-focused issue/PR at a time and re-run cross-module tests after integration.
- Always prefer user-visible search usefulness over speculative infrastructure. If the owner asks for a different scope, amend GOAL.md through a reviewed change.

### Continuous execution loop

1. Inspect main, current source, CI and open PRs. Reconcile progress.md vs actual tested implementation.
2. Claim the highest-priority unfinished FL-* gate; record owner, branch, next action and validation.
3. Reproduce the gap with a test, benchmark or GUI observation.
4. Implement minimal reliable change; keep IPC filters and provenance intact.
5. Run targeted tests and full ./scripts/check.sh where applicable. Fix regressions.
6. Record before/after evidence; open focused PR; validate exact head SHA in CI.
7. Merge reviewed, verified code to main; verify main SHA; update progress.md once.
8. Continue to next FL gate. Stop only at FINISHED or a documented external blocker.

### Hard boundaries

Never fabricate screenshot evidence, latency, semantic retrieval, paper qualification, PDF provenance or hardware verification. Never auto-run content from PDFs/abstracts. Never silently enable online services, change credential permissions, mutate real Drive content or delete user data. Never merge unrelated PR #16 simply because it is open. Do not start broad ResearchOS EX-* features to delay finishing this small search product.

## 5. How to begin (copy to coding agent)

> Continue Modern Search from the latest main commit. Read AGENTS.md, GOAL.md, README.md, progress.md and docs/QUICK_SEARCH_UI.md. You are the lead integrator for the v1.0 finish line defined in GOAL.md. Run baseline checks, create FL-00..FL-06 status entries and start with the highest-priority objectively unverified gate. Implement, test, record measured proof, review and merge focused changes. Preserve the privacy/qualification invariants, keep PR #16 untouched, and do not claim native Mac acceptance if it cannot be observed. Continue autonomously until GOAL.md says FINISHED or a specific external blocker is recorded.
