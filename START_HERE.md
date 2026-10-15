# START_HERE — ResearchOS parallel implementation kickoff

**Date:** 2026-10-15. **Status:** Operational instructions, NOT proof that any agent has started or that software is implemented.  
**Source of truth:** [AGENTS.md](AGENTS.md), [progress.md](progress.md), [docs/](docs/).  
**Repo:** https://github.com/anatwork14/modern-search  
**Spec branch:** docs/researchos-spec-and-progress (PR #1, initially unmerged).  
**Immediate priority:** working *local-first academic paper search vertical slice*, not extension ecosystem.

## Mission for the lead / orchestrator agent

> **ACT NOW**: Spawn 5 independently running worker agents in parallel, each with its own isolated git worktree and scoped task contract below. Coordinate interface agreements first. Do not merely write an architecture plan and stop. If your runtime lacks subagent/spawn capabilities, explicitly report the limitation; prepare the 5 worktrees and independent task tickets so humans or other agent runtimes can start the workers. Never assert a worker was launched unless its process/session/PR is observed.
>
> Read README.md, AGENTS.md, progress.md, docs/PRODUCT_SPEC.md, docs/ARCHITECTURE.md, docs/RETRIEVAL_SPEC.md, docs/DATA_AND_TAXONOMY.md, docs/SECURITY_PRIVACY.md and docs/EVALUATION_AND_TESTS.md. Confirm Git remote/default branch/PR status. **PR #1 is not merged as of kickoff.** No source code existed in main at audit. Choose the reviewed specification branch as integration base until PR #1 is safely merged; do NOT have workers start from old main.
>
> Record only verified events in progress.md. Start working on executable code and tests, not another rewrite of specifications.

## Step 0 — repository and worktree preparation (lead only)

Execute on the machine where agents can access the repository, not blindly through the GitHub API. The lead must run these commands serially to avoid worktree race conditions.

~~~bash
git clone https://github.com/anatwork14/modern-search.git
cd modern-search
git fetch --all --prune
git status --short
git log --oneline -5 origin/docs/researchos-spec-and-progress

# If PR #1 is still unmerged, create an implementation integration branch
# based on the full specs. If already merged, base on updated origin/main instead.
git switch -c integration/researchos-mvp origin/docs/researchos-spec-and-progress
git push -u origin integration/researchos-mvp

# Create each worktree BEFORE giving the path to a separate worker.
git worktree add -b feat/p0-data ../modern-search-data integration/researchos-mvp
git worktree add -b feat/p0-desktop ../modern-search-desktop integration/researchos-mvp
git worktree add -b feat/p0-embedding ../modern-search-embedding integration/researchos-mvp
git worktree add -b feat/p0-retrieval ../modern-search-retrieval integration/researchos-mvp
git worktree add -b feat/p0-quality ../modern-search-quality integration/researchos-mvp
git worktree list
~~~

If a clone/worktree/branch exists, inspect it and reuse/reconcile it rather than blindly overwriting or creating duplicates. Never delete a dirty worktree. Do not force-push. Workers create PRs **into integration/researchos-mvp**, not old main, until the lead changes the integration policy. Lead merges small PRs into integration after checks. Final merge into main requires PR #1 ancestry/merge to be correct and all release gates passing.

## Freeze minimal interface contracts before asynchronous work

Lead drafts a 1-page interface agreement in a PR or issue and all workers ACK it. Suggested ownership:

- **SQLite authority**: Worker A owns migrations/persistence and paper/tag/review schema. No other agent edits migrations.
- **Service/IPC**: Worker B owns Tauri commands, frontend and sidecar lifecycle. Agree on a typed JSON request/response envelope with Worker D/C; do not bind public network interfaces.
- **Embeddings**: Worker C implements isolated encode_query / encode_titled_documents / model_manifest adapter; offline failure returns typed unavailable error, never breaks lexical search.
- **Retrieval**: Worker D implements query AST validation, strict facet evaluator and pure retrieval/RRF logic against mock repositories; integrate SQLite after Worker A contract freezes.
- **CI/test policy**: Worker E owns .github/workflows, cross-cutting fixtures, security/lint checks and independent acceptance. Each worker retains tests colocated with owned code.

Contracts MUST agree on Paper_ID, canonical tag IDs, revision/QA status, empty-result policy, query mode, error envelope, pagination and index version. Store contract fixtures or typed schemas in the repo; protocol may evolve by coordinated PR, not silently.

## Five worker contracts — spawn simultaneously

### Worker A — DATA & PROVENANCE (worktree ../modern-search-data)
**Tasks:** P0-01 immediately, then P0-03/P0-04/P0-05 when audit and schema review pass.  
**Owned paths:** backend persistence/migrations, data adapters/import scripts, integration tests for idempotence, an audit report under docs/audits/. Do not edit UI or embedding adapter.  
**Day-one output:** Drive catalog audit of the canonical workbook and ZIP, source IDs, missingness, duplicate IDs/DOIs, tag alias collisions, venue-evidence and verified PDF states. If Drive access unavailable, label BLOCKED and build sanitized fixtures from accessible records; never invent numbers.  
**Exit:** repeat import preserves stable Paper_IDs and tag mappings, no fake local PDFs, deterministic audit checks, SQLite constraints and migration tests passing.  
**Communicate:** exact repositories/protocol needed by Worker D and expected data source shape.

### Worker B — DESKTOP & IPC (worktree ../modern-search-desktop)
**Tasks:** P0-02 (desktop scaffolding and local service contract), shell of P0-11 after working API.  
**Owned paths:** src-tauri/, apps/desktop/ (or agreed frontend dirs), UI tests, packaging bootstrap; avoid migrations and embedding worker.  
**Day-one output:** minimally launching Tauri 2 + React/TypeScript app, searchable placeholder UI using **explicitly mocked data**, typed IPC health check and model/index-unavailable state; useful smoke test and reproducible launch instructions.  
**Exit:** app launches on target Mac (if available), keyboard-accessible search screen, no unsecured IPC/port, offline indicator and clean sidecar quit. If macOS unavailable, mark native smoke test BLOCKED rather than passing it.  
**Communicate:** input/output interface desired for real search service to Worker D; mock state must never be presented as live results.

### Worker C — EMBEDDINGS & VECTOR SPIKE (worktree ../modern-search-embedding)
**Tasks:** P0-08, then vector manifest/index prototype for P0-09 if compatible and validated.  
**Owned paths:** backend/embeddings/, backend/vector/, tests/embeddings/, benchmark reports; not shared SQLite migrations.  
**Day-one output:** verify exact current official EmbeddingGemma 2 checkpoint, license, compatible libs, text-only 270M configuration, query/document prompt policy, vector dimensions, normalization and model revision. Test Apple Silicon MPS and CPU path if hardware available. Compare basic Qwen embedding alternative only after successful baseline.  
**Exit:** pure encoding API, model/version manifest, deterministic shape/normalization tests, offline after download; device/throughput/RAM numbers only if measured on that machine. If incompatible, report blocker and keep search lexical-only.  
**Communicate:** vector index metadata protocol, batch behavior, failures to Worker D/B.

### Worker D — RETRIEVAL / FILTER ENGINE (worktree ../modern-search-retrieval)
**Tasks:** P0-06, P0-07; P0-10 only after data+embedding contracts available.  
**Owned paths:** backend/retrieval/, tests/retrieval/, spec-referenced interface tests. Does **not** edit migrations or frontend.  
**Day-one output:** implement query AST validation, taxonomy alias resolution interface, strict ANY/ALL/NOT filter truth-table evaluator, deterministic BM25/FTS5 prototype against independent synthetic fixture, RRF fusion function and zero-result behavior.  
**Exit:** exact filter semantics on deterministic fixtures; retrieval classes admit both lexical-only and lexical+dense modes; match reasons and candidate-vs-verified flags preserved; never silently relax hard filters.  
**Communicate:** assumptions about data adapter and response envelope to A/B; integrate in own follow-up PR after contracts stable.

### Worker E — QUALITY, PRIVACY & CI (worktree ../modern-search-quality)
**Tasks:** CI/test harness and independent security/acceptance validation; prepares P1-05 query gold-set protocol while P0 runs.  
**Owned paths:** .github/workflows/, tests/contracts/, tests/security/, docs/qa/, static fixtures; do not own runtime code or migrations.  
**Day-one output:** lint/type/unit test matrix appropriate for newly scaffolded languages, schema-validation gate, negative test corpus (malformed DOI, duplicate tag, remote PDF that is HTML, malicious abstract prompt injection), deterministic filter tests and offline mode acceptance plan.  
**Exit:** runnable CI pipelines, documented commands, no secrets in git or logs, unit & integration gates for merges, benchmark report template without fabricated measurements.  
**Communicate:** independently review every proposed release gate and inform lead which are not yet executable.

## Lead agent role — INTEGRATION & RELEASE CONTROL

- Own only contracts, PR review/merge policy, progress.md and cross-module integration; delegate implementation to workers.
- Do not let agents edit progress.md concurrently. Each worker posts status in its PR/issue and lead records verified results centrally.
- Check GitHub PRs/branches, verify tests and evidence; when a worker completes a cohesive deliverable, merge only that worker PR into integration branch, then tell downstream workers to rebase/retest as needed.
- Prefer dependency order: Worker A audit + Worker B skeleton + Worker C spike + Worker D synthetic retrieval + Worker E CI in parallel. Then A migrations+import → D FTS/filter real DB → C embedding versioned index → B real search UI → integrated hybrid search → end-to-end tests.
- Do not claim PASS from documentation, GitHub commit existence, mocked UI or unseen logs. If integration blocked, report exact obstacle and proceed with other independent tasks.
- Avoid running concurrent heavy model indexing on same Mac if it exceeds memory; schedule GPU/MPS device usage with workers. CPU fixture tests may remain parallel.
- Keep working until a cohesive first MVP PR is ready; no promise of work outside current agent runtime without actually running it.

## Reporting / ownership

Use a lead-controlled status table in progress.md; at any checkpoint each task has Task ID, owner, branch, status DONE/IN_PROGRESS/TODO/BLOCKED, last test command/result, PR and next action. No agent marks DONE for another. No secrets/private PDFs/Drive archives or user personal notes in public GitHub. Keep local caches, PDF downloads and model weights outside tracked repo.

Worker mini-report (post to own PR/issue):
~~~text
WORKER: [A–E] | TASK: [P0-xx] | BRANCH:
FILES CHANGED:
IMPLEMENTED (not just planned):
VALIDATION COMMANDS + RESULTS:
SOURCE / DATA / MODEL VERSIONS:
KNOWN LIMITATIONS / BLOCKERS:
DEPENDENCIES UNBLOCKED:
NEXT HANDOFF:
~~~

## First integration definition of success

1. The Mac app starts and shows real local search results from imported, source-traceable metadata/abstract fixtures.
2. 1,616-tag taxonomy importer is idempotent and reports actual counts and discrepancies.
3. Strict AND/OR/NOT and publication-quality filter passes all controlled test cases.
4. BM25-only works when model unavailable/offline; a validated embedding model improves search only if compatible.
5. Hybrid results preserve evidence and verified-vs-candidate status. No fabricated quotes or PDFs.
6. CI passes, exact commands recorded, reviewer approves merge.
7. progress.md is aligned with actual code and verified tests, not aspirations.

## Minimum handoff prompts (lead sends each via its agent runtime)

1. Tell each worker: "Read START_HERE.md, AGENTS.md, progress.md, your assigned docs, and stop if worktree or base branch differs."
2. Assign exactly its Worktree, Tasks, Paths, Deliverables, Acceptance tests and owned PR base.
3. Ask for initial checkpoint with planned files/interfaces within the first iteration, not a free-form research report.
4. Require a running implementation change, tests and a PR; block broad unrelated changes.
5. Have the lead reconcile conflicts and update progress.md only when results verified.

## Repository integration status at kickoff

This file is an instruction handoff only. The tool writing this spec to GitHub does not execute code on a Mac, run subprocess agents, perform Drive imports, or validate native Tauri/model runtime. The status ledger intentionally remains **not started** until actual worker run, commit, test and/or PR evidence is observed.

## Dispatchable GitHub tickets (not yet launched)

- Worker A: https://github.com/anatwork14/modern-search/issues/2
- Worker B: https://github.com/anatwork14/modern-search/issues/3
- Worker C: https://github.com/anatwork14/modern-search/issues/4
- Worker D: https://github.com/anatwork14/modern-search/issues/5
- Worker E: https://github.com/anatwork14/modern-search/issues/6

Lead should assign session/branch to each issue after launching the runtime agents. Issue creation does **not** mean any agent is running.
