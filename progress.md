# progress.md — ResearchOS execution ledger

**Last reviewed:** 2026-10-15 (Asia/Ho_Chi_Minh). **Status:** development search MVP DONE; portable release and relevance qualification remain TODO.
**Repository at audit:** only README.md and LICENSE on main (commit bd4bc6d53a827bada6c5b5b3e418ad14e157004d).  
**This specification branch:** docs/researchos-spec-and-progress.  
**Status authority:** validated code/test results; update this file with each implementation PR (see AGENTS.md).

## Snapshot

Implementation is based on specification commit `e85962c`, because PR #1 remains unmerged. `main` has not been merged or released. Five actual GPT-6 Luna High sessions ran in separate worktrees; runtime capacity permitted three active workers alongside the lead, so later workers started when slots became available. Only validated changes enter `integration/researchos-mvp`.

| Workstream | Status | Implemented evidence / remaining gate |
|---|---|---|
| A — source audit, import, SQLite/provenance | DONE (workbook slice) | PR #10, `d2832c5`; 15 data tests and independent security regressions PASS; imported 1,616 tags, 2,478 papers, 3,197 assertions, 7,291 source records; idempotent reimport, integrity/FKs PASS |
| B — Tauri/React desktop and stdio bridge | DONE (development app) | Merged PR #9, `c83d3db`; frontend 3 tests/build/lint and Rust smoke PASS; native qualified 0, unknown/attention lexical 102, BROAD dense ready and strict ALL 0 verified |
| C — embedding adapter and versioned title/abstract index | DONE (compatibility/runtime slice) | Merged PR #7, `04bcdaa`; 10 tests PASS; pinned offline EmbeddingGemma 2 works on MPS and CPU; actual 2,478 title vectors built; final catalog index rebuild PASS (2,478 vectors, 40,410,426 bytes) |
| D — lexical, strict filters, AST, RRF | DONE (MVP component) | Merged PR #8, `5eb789d`; 17 retrieval tests plus independent negative regressions PASS; strict zero remains zero |
| E — CI, security and benchmark infrastructure | DONE | Merged PR #11, `80edc3d`; contracts 3/security 18 PASS; hosted Python and desktop jobs PASS; independent A/B/C/D review approved |
| Lead — stdio service, import CLI and integration | DONE (development slice) | Real offline service and native app verified; reproducible setup and scripts/check.sh; all five reviewed worker PRs merged into integration |
| Qualification and source completeness | BLOCKED | All 2,478 candidates unknown eligibility/discovered, no source abstracts, 898 remote PDF links, 0 verified local PDFs; supplementary ZIP contents unavailable |
| Signed, portable macOS release | TODO | Debug app remains checkout/Python dependent; release resources/signing/notarization unqualified |
| Relevance gold set / comparative ablation | TODO | Compatibility and mechanical tests are not relevance judgments; no nDCG/Recall quality claim |

## Owners, branches and next actions

| Session / issue | Branch / PR | Execution state | Next action |
|---|---|---|---|
| `/root/worker_a_data`, #2 | `feat/p0-data`, #10 merged | Completed | Preserve review decisions on future revisions; ZIP contents remain blocked |
| `/root/worker_b_desktop`, #3 | `feat/p0-desktop`, #9 merged | Completed | Portable resource packaging remains TODO |
| `/root/worker_c_embeddings`, #4 | `feat/p0-embedding`, #7 merged | Completed | Relevance benchmark deferred; model jobs serialized |
| `/root/worker_d_retrieval`, #5 | `feat/p0-retrieval`, #8 merged | Completed | Support final integration regressions if needed |
| `/root/worker_e_quality`, #6 | `feat/p0-quality`, #11 merged | Completed | Judged relevance evaluation remains TODO |
| `/root` | `integration/researchos-mvp` | Completed development slice | Review MVP PR; release resources/qualification remain separate gates |

Git push transport fails on this host. Exact unsigned Git objects are published through the GitHub Git Database API with SHA equality checks and non-forced reference updates. This does not relax review gates.

### Executed acceptance evidence (2026-10-15)

- Python 3.11: `python -m unittest discover -s tests/{contracts,data,embeddings,retrieval,security,integration} -v` executed separately: 3/15/10/17/18/2 PASS in candidate integration (65 total).
- Desktop: `npm test` (3 PASS), `npm run lint`, `npm run build`; `cargo test --locked` (1 real Python stdio smoke PASS), `cargo check --locked` PASS. Disposable empty DB and explicit Python executable used for Rust smoke.
- Import: fresh final private DB contains the counts above; same-revision import adds 0 tags/papers/assertions, SQLite `integrity_check` is `ok`, foreign-key violations 0. Private catalog/DB/index excluded from Git.
- Embeddings: official pinned revision `914f7f89142e33e77833254d9c9b90c3cef7303b`, 768 dimensions and unit normalization. MPS warm query median 0.030455 s / peak RSS 1,088,438,272 B; CPU 0.042150 s / 1,252,376,576 B (3-sample smoke, not production p95). Reports in `docs/benchmarks/`.
- Actual service with socket connections blocked and offline cache flags: explicit unknown eligibility `attention` STRICT returns 102; BROAD semantic routes/dense ready; impossible field ALL intersection returns 0. No abstracts/pages fabricated.
- Native debug app: actual catalog health 2,478; qualified-only empty state 0; explicit unknown attention returns 102. Final native BROAD dense-ready and strict impossible ALL 0 PASS. Lead independently observed native default 0 and explicit unknown BROAD completion with dense ready.
- Hosted Actions: PASS on quality head `80edc3d`, [run 38690936686](https://github.com/anatwork14/modern-search/actions/runs/38690936686): Python suites and desktop frontend/Rust gates. Integration commit `93a49ee` includes all reviewed workers; later ledger-only commits do not alter runtime. Signed distribution: NOT RUN. Relevance gold-set evaluation: NOT RUN. ZIP content audit: BLOCKED.
- Final private dense index corpus revision `cafe81c40b5662d48a902294d00a442eccba730d999f93b7a8b85866b3b36b94`, file SHA-256 `ede335592f80217636c2872b2f5ff2bf4415ff18c6feaebedc340c1f83805123`; actual source abstracts absent, so current vectors are title-only.

## Prioritized backlog

Order is dependency-aware. Priority P0 = unblock MVP; P1 = improve correctness; P2 = advanced discovery.

### Stage 0 — trusted data foundations (P0)

- [ ] **P0-01 Drive catalog audit & snapshot.** Read workbook and archive metadata, record actual counts, sheets, duplicate IDs, missing fields, PDF states, rank-evidence coverage and tag QA distribution. Deliver audit report and sanitized fixtures. **Gate:** deterministic counts, no invented downloads or eligibility. Depend: none.
- [x] **P0-02 Project scaffold.** Bootstrap Tauri 2 + React/TS and Python worker with reproducible macOS instructions, pinned deps, lightweight smoke test, lint/typecheck/CI and .gitignore. **Gate:** empty app starts and health IPC works on a target Mac. Depend: agreed interfaces; may parallel P0-01.
- [x] **P0-03 SQLite schema & migrations.** Convert spec/schema.sql into versioned migrations; add foreign keys, uniqueness, integrity checks, FTS, transaction-safe import and backup tests. **Gate:** fresh and upgraded databases migrate cleanly. Depend: P0-01.
- [x] **P0-04 Workbook taxonomy importer.** Parse 1,616 canonical tags and aliases; preserve namespace, group, active state and stable IDs. **Gate:** repeat import idempotent; invalid aliases/duplicate tags reported, not silently dropped. Depend: P0-01, P0-03.
- [x] **P0-05 Paper import, provenance & dedupe.** Preserve original Paper_ID, source rows, DOI/arXiv/title identity, venue ranking year/source and candidate-versus-verified semantics. **Gate:** repeat import creates no duplicate paper IDs or paper-tag edges; can export reconciliation report. Depend: P0-03/04.
- [x] **P0-06 Lexical search baseline.** SQLite FTS5 or LanceDB FTS on title, abstract, tags, indexed sections; literal phrases and named method searches. **Gate:** fixture queries return expected papers deterministically and work offline. Depend: P0-05.
- [x] **P0-07 Strict multi-facet filter engine.** ANY/ALL per facet, AND across facets, explicit NOT, venue eligibility and review evidence status. **Gate:** exhaustive truth-table tests incl. zero strict matches; never silently widen. Depend: P0-05.
- [x] **P0-08 EmbeddingGemma 2 compatibility spike.** Test text-only 270M on target Mac (Apple Silicon MPS; CPU fallback), query vs titled document prompts, 768d dimensions, normalization, model caching and zero-network inference after install. **Gate:** measured correct embeddings + regression test; do not invent performance. Depend: P0-02.
- [x] **P0-09 Versioned dense chunk index — DONE for available title/source-abstract units.** Section/title/abstract units, index manifest, reproducible reindex, drift detection and safe atomic swap. **Gate:** model/prompt/dimension mismatch blocks mixed-index search. Depend: P0-05/08.
- [x] **P0-10 Hybrid search MVP.** BM25+dense candidates, RRF fusion, paper-level dedupe, search modes strict/broad, pagination and match-route explanations. **Gate:** offline sample queries work end to end, no page/evidence fabrication. Depend: P0-06/07/09.
- [ ] **P0-11 Desktop result experience — working MVP slice DONE; saved queries/groupings/count facets TODO.** Search box, filter panes with counts, research groupings, paper list, source links, annotation statuses, empty state and saved query. **Gate:** end-to-end query from desktop; keyboard navigation; no misleading verified badge. Depend: P0-02/10.

### Stage 1 — source-grounded full-text research (P1)

- [ ] **P1-01 PDF acquisition/verification.** Optional user-selected download; validate content-type, PDF magic signature, rights, hash and parse status. **Gate:** imported vs linked remote distinguished.
- [ ] **P1-02 PDF extraction and chunk evidence.** PyMuPDF fast path; Docling fallback; sections and page spans; keep parse failures visible. **Gate:** inspected page references match PDF, no invented citations.
- [ ] **P1-03 Typed tags and relationship review.** Primary/supporting/mention/survey/negative use, confidence, evidence and human verification. **Gate:** no unsupported USES_METHOD edge accepted.
- [ ] **P1-04 Candidate reranker.** Evaluate BGE-reranker-v2-m3 or alternative, latency vs nDCG and recall. **Gate:** benchmarked benefit warrants default enablement.
- [ ] **P1-05 Gold benchmark.** 60–100 queries including Vietnamese, bridge queries and negative cases; independent relevance judgments. **Gate:** baseline comparison results reproducible and hardware specified.
- [ ] **P1-06 Backup/recovery and stable incremental index updates.** Crash/resume, deletion propagation, corrupted checkpoint handling. **Gate:** repeatable recovery tests.

### Stage 2 — scholarly discovery (P2)

- [ ] **P2-01 Citation and concept relation graph** with provenance and explicit inference labels.
- [ ] **P2-02 OpenAlex/Semantic Scholar/Crossref opt-in enrichment** with rate limiting, error recovery and local cache.
- [ ] **P2-03 Bridge-query concept clustering** distinguishing FL attention aggregation, IDS attention encoders and LLM KV attention.
- [ ] **P2-04 Comparisons and research-gap workspace**: pinned seeds, pros/cons with source evidence, contradictions, reading queue and export.
- [ ] **P2-05 Zotero local API integration** with read-only discovery first; no direct Zotero DB writes.
- [ ] **P2-06 Google Drive incremental read-only sync**, eventual reconciliation; never mutate original workbook by default.
- [ ] **P2-07 Multimodal EmbeddingGemma 2** (text+vision 440M), figure captions, crops, diagram/figure retrieval after measured ablations.
- [ ] **P2-08 macOS app packaging, sandbox, signing/notarization/release** with Apple Silicon and Intel compatibility policy.
- [ ] **P2-09 Performance/memory tuning** based on measured p50/p95 search latency, throughput and index size, not guesses.

## Cross-cutting acceptance gates

1. Same Paper_ID and canonical tags after repeated imports. Source-of-truth row provenance preserved.
2. The default qualified filter requires publication evidence + venue rank (Q1/Q2 journal via SCImago/SJR or A/A* conference via CORE/ICORE), with ranking year/source visible. Exploratory preprints remain separate.
3. Strict tag+metadata filters are exactly correct in tests (target 100% on fixtures); zero-result strict queries are not softened without consent.
4. Search supports exact names, English/Vietnamese paraphrase, broad attention inference, FL attention, and combined IoT IDS queries.
5. Citation/section snippets show true source text and page or clearly say unavailable; externally linked PDFs never appear as local files.
6. Quantitative model/algorithm decisions require BM25-only, Gemma-only, hybrid, hybrid+reranker and Qwen3-Embedding-0.6B comparisons on the same gold set.
7. Report Recall@20/100, nDCG@10, MRR@10, p50/p95 by hardware, index sizes, parser failure rate and false-positive evidence rates. Never invent measurement.
8. Offline search works without an open cloud service after model/data preparation. Opt-in network routes are clearly marked.
9. No injected PDF text can change agent/runtime behavior or access credentials.

## Next integration action

Review the development MVP pull request. Source qualification, archive content audit, saved queries/groupings, full-text evidence, judged relevance benchmarking, and self-contained signed release packaging remain separate work. Do not treat broad candidate counts or source-reported venue ranks as quality certification.

## Changelog

- **2026-10-15 — Specification setup:** repo baseline audited; README, AGENTS.md, planning specs, schema draft, query fixtures, and this ledger prepared. No runtime implementation, local indexing or retrieval benchmarks claimed.

## Platform-expansion research — completed design, NOT completed features

The following deliverables are **DONE as research/specification only** on this documentation branch:
- Opportunity and competitive-capability analysis: docs/PLATFORM_EXPANSION_RESEARCH.md
- Optional modules and agent plugin contract: docs/EXTENSIBILITY_AND_PLUGIN_API.md
- Application profiles: docs/APPLICATION_PROFILES.md
- Research evidence / cross-domain / reproducibility workflows: docs/RESEARCH_WORKFLOWS.md
- Draft extension manifest schema: spec/extension_manifest.schema.json

**Implementation for ALL features below remains TODO.** Do not use 'DONE' for an integration because a reference or manifest file exists. Do not start platform expansion before P0-01/P0-02 and a functioning search vertical slice.

### Extension backlog — dependency aware, non-blocking to P0

- [ ] **EX-01 [P1] Claim and evidence layer.** Add extraction of role-aware claims, limitations, assumptions, exact source passages/page spans and reviewer QA. **Gate:** evaluated precision and zero invented locators on labeled PDFs. **Depends:** P1-02, P1-03.
- [ ] **EX-02 [P1] Research workspace / comparisons / citation export.** Saved research projects, matrices, reading queue and source-backed Markdown/CSV/BibTeX/CSL exports. **Gate:** every populated evidence cell has a traceable source; unknown stays unknown. **Depends:** P0-10, P1-02.
- [ ] **EX-03 [P1→P2] Paper-code-experiment links.** Add GitHub repo + commit SHA, dataset/split hash, MLflow run references, publication-vs-reproduction status. **Gate:** no untested experiment tagged reproduced; independent metrics carry context. **Depends:** P0-05, EX-01.
- [ ] **EX-04 [P2] Cross-domain mechanism bridge cards.** Dual-basket search, mechanism ontology, disanalogies, testable hypotheses, falsification experiments; verified bridge ≠ semantic analogy. **Gate:** human-labeled bridge relevancy and false-equivalence study. **Depends:** P0-10, P1-05, EX-01.
- [ ] **EX-05 [P2] Citation genealogy + temporal topic discovery.** Source-backed backward/forward reference graph and timeline. **Gate:** citation edges have originating evidence; no fabricated chronology. **Depends:** P2-01, P2-02.
- [ ] **EX-06 [P1 after API] Safe agent interface.** Read-only CLI/MCP adapter for Codex/Claude/Hermes to search and fetch citations, with explicit source scopes. **Gate:** UI/API filter equivalence, negative authorization tests, no unrestricted file access. **Depends:** P0-10, docs/EXTENSIBILITY_AND_PLUGIN_API.md.
- [ ] **EX-07 [P1 interfaces, P2 profiles] Pluggable parsers/sources/profiles.** Versioned typed extension manifests, local GitHub/Markdown importer and separate application profile. **Gate:** contract tests, no mixed ACL/corpus leakage; disabled plugins offline. **Depends:** P0-03, P0-05, P1-02.
- [ ] **EX-08 [P2 experimental] Novelty/contradiction suggestion queue.** Auditable, explicitly hypothetical findings and contradiction candidates; human approval. **Gate:** source-specific contradictions, comparable metrics, zero unsupported novelty certification. **Depends:** EX-01, EX-04.
- [ ] **EX-09 [P1] Citation/research report export.** Use metadata-preserving structured citations/CSL/BibTeX/Markdown. **Gate:** round-trip with test DOIs and no invented citations. **Depends:** P0-05.
- [ ] **EX-10 [P2] Opt-in literature subscriptions.** Differential OpenAlex/Semantic Scholar changes with dedupe + user quality filters. **Gate:** new results only, strict source permission, rate limit and offline behavior. **Depends:** P2-02, P2-06.
- [ ] **EX-11 [P2] Image/equation/table retrieval.** Evaluate multimodal Gemma and specialized PDF parsers. **Gate:** separate figure retrieval gold set and measured macOS costs. **Depends:** P1-02, P1-05, P2-07.
- [ ] **EX-12 [P2] Research knowledge map.** Provenance-backed clusters/edges and source navigation, not decoration. **Gate:** graph edge precision and usefulness study. **Depends:** EX-05.
- [ ] **EX-13 [DEFER] Team/server/ACL collaboration.** Do not add required cloud/multiuser services before research users demonstrate need and security model is approved.
- [ ] **EX-14 [DEFER] Autonomous paper-code execution/GPU orchestration.** Explicit permission, sandboxed execution and strict resource limits required; not an automatic import feature.
- [ ] **EX-15 [DO NOT CLAIM] Definitive novelty certification, scientific correctness, self-directed publication.** Never market or mark as reliable without independent expert validation.

### Next implementation rule

Work **P0-01** first; optional EX-* proposals cannot supersede P0 correctness, provenance and offline search. Agent owners can separately research interfaces but should not implement competing services, generic chat frameworks, or unreviewed extension loaders. When an extension actually ships, update this ledger with its code path, tests, measurements, commit and PR.

## Parallel execution record

Actual sessions and isolated branches are listed above. A/B/C launched first; D and E launched as slots became available. No shared migrations, interfaces or progress edits occurred concurrently. Lead resolves integration and owns this ledger; workers supply code/test evidence. All worker PRs target `integration/researchos-mvp`.

## Drive paper transfer and SVG identity follow-up — 2026-10-15 checkpoint

This is an additive Drive transfer and an independently audited icon implementation; it does not modify the application database, catalog, qualification metadata or index. The user authorized following catalog links and adding verified PDFs to the same folder while preserving existing files.

| Session / branch | State at this checkpoint | Evidence and remaining gate |
|---|---|---|
| `/root/icon_implementation` — `feat/researchos-icon` | DONE; PR #13 merged at `3cbda695` (source change `5fd0e726`) | The SVG identity supplied the desktop icon; app build/launch and UI checks passed in that PR. The local SVG was uploaded as `researchos-icon.svg`, Drive ID `1UkjXHBdFR1rA4ymw3qc9f3Fh0xkOFAgk`, and read back at 1,214 bytes. |
| `/root/paper_acquisition` — `feat/paper-acquisition` | IN PROGRESS; PR #14 merged at integration commit `0f8e3f4` | Validator SHA-256 `caa99d9c0173d816e224cb7c556abbc2dc251a875710dfb340862ef3f20d00d1`; independent 11/11 identity fixture, 32 acquisition tests, and 15 core data tests passed. At this checkpoint 1,088/2,478 records were parsed (897 ready, 131 unavailable at attempted endpoints, 60 failure); campaign still running. |
| `/root/paper_upload_quality` — `chore/paper-upload-audit` | IN PROGRESS; 157 PDFs uploaded and independently reconciled | Local hashes, sizes, PDF signatures, page counts and first-page title headers passed 157/157; Drive receipts reconciled with observed names, IDs, sizes and MIME types. Successful per-file metadata readback confirmed the destination parent. Remote PDF checksums are not exposed. Acquisition CI, docs and four independent network-boundary tests are included in this follow-up branch. |
| `/root` — `integration/researchos-mvp` | IN PROGRESS | PR #12 remains a draft to `main`; lead tracks integration and campaign completion. The final all-paper manifest awaits terminal acquisition reconciliation. |

Campaign totals are not final. The read-only catalog snapshot contains 2,478 candidates, 1,580 with no direct PDF URL, and 184 JMLR masthead-prefix titles (151 without a catalog article-title tail). At the checkpoint, 35 uploaded PDFs are JMLR papers; 23 masthead-repair titles were verified against official JMLR landing pages and exact PDF links. Source qualification (SJR Q1/Q2 or CORE A/A*) remains a separate, unvalidated filter. The ZIP contained no full-text PDF set. The external uploads do not change the app's local-PDF or qualification status, and source catalog/database state remains unchanged. `unavailable` describes attempted endpoint responses, not proof a paper is globally unavailable.

## UI-QUICK-SEARCH — Gemini-inspired launcher (2026-10-16)

- **Status: IN_PROGRESS** — owner: ChatGPT implementation; branch `feat/gemini-inspired-quick-search`; PR [#17](https://github.com/anatwork14/modern-search/pull/17); started 2026-10-16 12:13 UTC.
- **Implemented candidate:** compact rounded Tauri launcher and native window resizing, keyboard search, progressive-disclosure filters, concise research result cards. Paths: `apps/desktop/src/{App.tsx,App.css,index.css,App.test.tsx}`, `apps/desktop/src-tauri/{tauri.conf.json,capabilities/default.json}`, `docs/QUICK_SEARCH_UI.md`.
- **CI observed:** frontend Vitest/typecheck/lint/build PASS and Python contracts/acquisition PASS on [run 38900132723](https://github.com/anatwork14/modern-search/actions/runs/38900132723). Rust compile/test still running at observation time; do not assume success.
- **NEXT GATE:** macOS Tauri smoke on target machine: transparent rounded corners, drag, close, compact-to-results resize, real local search, source toggle, keyboard access, small display. Attach screenshots to PR; reconcile any CI failures. No measured retrieval speed improvement is claimed.
