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
