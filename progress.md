# progress.md — ResearchOS execution ledger

**Last reviewed:** 2026-10-15 (Asia/Ho_Chi_Minh). **Status:** requirements documented, implementation not started.  
**Repository at audit:** only README.md and LICENSE on main (commit bd4bc6d53a827bada6c5b5b3e418ad14e157004d).  
**This specification branch:** docs/researchos-spec-and-progress.  
**Status authority:** validated code/test results; update this file with each implementation PR (see AGENTS.md).

## Snapshot

| Workstream | Status | Evidence / caveat |
|---|---|---|
| Problem framing and cross-domain queries | DONE (research/design) | docs/PRODUCT_SPEC.md and docs/RETRIEVAL_SPEC.md |
| 1,616-tag taxonomy authoring | DONE (external source) | linked Drive workbook; import and QA NOT done |
| Paper candidate discovery | DONE (external inventory only) | Drive reports 2,478 candidate records and 3,197 candidate paper–tag links; most not validated |
| Primary venue quality policy | DONE (external policy) | Drive QUALITY_POLICY.md; machine enforcement NOT done |
| App architecture and schema draft | DONE (design) | docs/ARCHITECTURE.md; spec/schema.sql; not migrated |
| EmbeddingGemma 2 model selection | DONE (baseline choice) | docs/REFERENCES_AND_DECISIONS.md; runtime compatibility NOT tested |
| Repo application scaffold | TODO | No Tauri, Python, SQLite DB, tests or executable app at audit |
| Actual PDF imports, vector index, retrieval, reranker | TODO | External notes state zero PDFs downloaded |
| Mac packaging, signed app, release | TODO | No build or verification |

**Never reclassify external workbook numbers as installed or verified local indexes.**

## In progress

No implementation tasks have been started or assigned as of this review. Agents must register work below before changes.

| ID | Owner / agent | Branch | Started (UTC) | Next check | Status |
|---|---|---|---|---|---|
| — | Unassigned | — | — | Begin P0-01 | — |

## Prioritized backlog

Order is dependency-aware. Priority P0 = unblock MVP; P1 = improve correctness; P2 = advanced discovery.

### Stage 0 — trusted data foundations (P0)

- [ ] **P0-01 Drive catalog audit & snapshot.** Read workbook and archive metadata, record actual counts, sheets, duplicate IDs, missing fields, PDF states, rank-evidence coverage and tag QA distribution. Deliver audit report and sanitized fixtures. **Gate:** deterministic counts, no invented downloads or eligibility. Depend: none.
- [ ] **P0-02 Project scaffold.** Bootstrap Tauri 2 + React/TS and Python worker with reproducible macOS instructions, pinned deps, lightweight smoke test, lint/typecheck/CI and .gitignore. **Gate:** empty app starts and health IPC works on a target Mac. Depend: agreed interfaces; may parallel P0-01.
- [ ] **P0-03 SQLite schema & migrations.** Convert spec/schema.sql into versioned migrations; add foreign keys, uniqueness, integrity checks, FTS, transaction-safe import and backup tests. **Gate:** fresh and upgraded databases migrate cleanly. Depend: P0-01.
- [ ] **P0-04 Workbook taxonomy importer.** Parse 1,616 canonical tags and aliases; preserve namespace, group, active state and stable IDs. **Gate:** repeat import idempotent; invalid aliases/duplicate tags reported, not silently dropped. Depend: P0-01, P0-03.
- [ ] **P0-05 Paper import, provenance & dedupe.** Preserve original Paper_ID, source rows, DOI/arXiv/title identity, venue ranking year/source and candidate-versus-verified semantics. **Gate:** repeat import creates no duplicate paper IDs or paper-tag edges; can export reconciliation report. Depend: P0-03/04.
- [ ] **P0-06 Lexical search baseline.** SQLite FTS5 or LanceDB FTS on title, abstract, tags, indexed sections; literal phrases and named method searches. **Gate:** fixture queries return expected papers deterministically and work offline. Depend: P0-05.
- [ ] **P0-07 Strict multi-facet filter engine.** ANY/ALL per facet, AND across facets, explicit NOT, venue eligibility and review evidence status. **Gate:** exhaustive truth-table tests incl. zero strict matches; never silently widen. Depend: P0-05.
- [ ] **P0-08 EmbeddingGemma 2 compatibility spike.** Test text-only 270M on target Mac (Apple Silicon MPS; CPU fallback), query vs titled document prompts, 768d dimensions, normalization, model caching and zero-network inference after install. **Gate:** measured correct embeddings + regression test; do not invent performance. Depend: P0-02.
- [ ] **P0-09 Versioned dense chunk index.** Section/title/abstract units, index manifest, reproducible reindex, drift detection and safe atomic swap. **Gate:** model/prompt/dimension mismatch blocks mixed-index search. Depend: P0-05/08.
- [ ] **P0-10 Hybrid search MVP.** BM25+dense candidates, RRF fusion, paper-level dedupe, search modes strict/broad, pagination and match-route explanations. **Gate:** offline sample queries work end to end, no page/evidence fabrication. Depend: P0-06/07/09.
- [ ] **P0-11 Desktop result experience.** Search box, filter panes with counts, research groupings, paper list, source links, annotation statuses, empty state and saved query. **Gate:** end-to-end query from desktop; keyboard navigation; no misleading verified badge. Depend: P0-02/10.

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

## Next action for the first implementation agent

**Start with P0-01**. Verify live Drive workbook/archive metadata and inspect source contents; document missingness and candidate-vs-verified distribution. Produce deterministic import fixture/report, then implement P0-03/P0-04. A separate agent can open P0-02 in parallel after agreeing on IPC contracts. Do not begin speculative graph/agent frameworks before the first vertical slice passes.

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
