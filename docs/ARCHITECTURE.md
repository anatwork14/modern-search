# Technical architecture and runtime contract

## Principle

Embedded local-first application. One source-of-truth relational database, one explicitly versioned vector index, one lexical index, narrow desktop IPC. Do not introduce an agent orchestration dependency for ordinary retrieval.

## Proposed components

| Component | Job | Baseline |
|---|---|---|
| Tauri 2 host | window, OS permissions, packaged sidecar lifecycle | Rust + Tauri |
| React/TypeScript UI | query, filters, source inspector and statuses | React |
| Local worker | parsing/import, embeddings, query planning and search | Python |
| SQLite | papers, sources, tags, assertions, review, citation and jobs | SQLite |
| Lexical | title/abstract/section BM25, exact identifier search | SQLite FTS5 (first); evaluate LanceDB FTS later |
| Dense | chunk vectors, metadata search and ANN/exact scan | embedded LanceDB |
| Embedding adapter | task-specific query/document encoding | google/embeddinggemma-2 |
| PDF adapter | fast text extraction, optional complex layout | PyMuPDF, Docling |
| Remote metadata | optional explicit network enrichment | Drive, Crossref, OpenAlex, Semantic Scholar |

All component choices are proposals; test on the target Mac and pin compatible library versions before implementation. Avoid overengineering with both FTS systems simultaneously unless experiments require them.

## Local process lifecycle

1. Tauri initializes config, grants only required file access and opens a trusted IPC channel.
2. Local worker starts on-demand; use stdio RPC where feasible or loopback service bound to 127.0.0.1 with unguessable per-session authentication, request size limits and CORS denial.
3. Initialize SQLite migrations, verify foreign keys, integrity and index manifest, then load read-only retrieval state.
4. Lazy-load embedding model on first semantic query / indexing job; lexical and metadata search remains available if model unavailable.
5. Import/index job has persistent progress, resumable checkpoints, cancellation and an atomic index-swap boundary.
6. On quit, stop child cleanly, commit completed transactions, leave recoverable work queue. Never leak process or port.

## Diagram

~~~mermaid
flowchart TD
  S["Drive / local PDF / Zotero / APIs"] --> I["Import + dedupe + source provenance"]
  I --> M["SQLite metadata and taxonomy"]
  I --> P["Section/figure extraction"]
  P --> F["FTS5 lexical"]
  P --> E["EmbeddingGemma 2 adapter"]
  E --> V["LanceDB versioned vectors"]
  Q["UI query + filters"] --> C["Query planner"]
  C --> M
  C --> F
  C --> V
  M --> R["Fusion, rerank, paper dedupe"]
  F --> R
  V --> R
  R --> U["Ranked/clustered results + evidence"]
  U --> H["Human QA, saved query, export"]
~~~

## Core module boundaries

- source_adapters: Drive, workbook, Zotero and metadata API normalization; each returns provider ID, version and source state.
- ingest: identity merge, row snapshot, PDF verification, parser selection, chunk segmentation, references.
- persistence: transaction-safe SQLite repositories, migrations, FTS shadow maintenance and index jobs.
- embeddings: interface encode_query, encode_titled_document, model_info, batch_index; query/document prompt policies are part of versioned contract.
- retrieval: structured query validator, hard filters, lexical/dense candidates, RRF, optional reranker, paper aggregation, diversification.
- evidence: tag role and source proof, claim references, review workflow and unverified distinctions.
- ui: browse/search/group/inspect/annotate, accessibility, offline status and sync error visibility.

## Indexing and versioning

- Papers: stable Paper_ID plus provider IDs; chunks are section-aware ~300–700 tokens configurable, store start/end pages and extraction confidence.
- Compute hash of PDF/content; use deterministic chunk IDs including document version, section and offsets.
- Manifest: model id, checkpoint revision, tokenizer/prompt template version, dimension, vector normalization, parser/chunker version, corpus snapshot, build timestamp.
- Query and document representations must share checkpoint and vector dimension; MRL truncation (768→512/256/128) requires normalization and matched dimensions.
- Build new vector index into temporary name, validate document count/integrity, then swap pointer atomically; interrupted jobs do not corrupt prior good index.
- Preserve source text and raw import record so parser or model upgrades can rebuild without losing information.

## Failure handling

| Failure | Expected behavior |
|---|---|
| No GPU, missing weights | BM25/facet search still works; explain dense unavailable |
| Offline external adapter | Continue local; queue or skip only opted-in requests |
| Duplicate DOI/PDF | Show merge provenance; avoid duplicate paper or tags |
| PDF parse failure | Keep metadata, PDF hash and explicit parse error |
| Corrupt vector manifest | Block mixed index, offer safe rebuild |
| Absent full text | Label metadata/abstract-only; never cite nonexistent page |
| Empty strict intersection | Zero matches, explain constraints, offer manual relaxation |
| Low-confidence classifier | Save candidate assertion only; no verified badge |

## Hardware and deployment

Primary: Apple Silicon macOS, local model path tested with PyTorch MPS; CPU fallback and explicit Intel policy. MLX optimization is exploratory and cannot silently replace a tested encoder without embedding-equivalence/relevance ablation. Avoid unsupported memory/latency promises until measured. Release workflow eventually covers notarization, updates, permissions and offline install model packaging/caching.

## Dependencies

Read DATA_AND_TAXONOMY and RETRIEVAL_SPEC before designing storage APIs. Keep all provider adapters optional, authenticated and rate-limited; local search must never require a remote backend.
