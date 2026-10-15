# modern-search / ResearchOS

Local-first research search and knowledge discovery for AI, ML, and deep learning papers.

> **Status (2026-10-15): SPECIFICATION ONLY.** No Tauri app, embedding model, PDF parser, local index, ingestion job, benchmark, or packaged binary exists in this repository yet. See [progress.md](progress.md).

## Product vision

A macOS-first desktop research workbench for discovering, validating and organizing scholarly work. The system must combine **EmbeddingGemma 2 semantic search, exact BM25 search, faceted multi-tag filtering, passage-grounded evidence, and cross-domain concept connections**. It must make it easy to research both "attention mechanisms for LLM inference optimization" and "attention in personalized federated learning", without conflating unrelated meanings of attention.

### Non-negotiable behavior

- Local paper search works offline once models and indexes are installed. Online discovery is explicit opt-in.
- Search uses lexical + dense + metadata retrieval; embeddings alone are insufficient.
- Tags are many-to-many and follow the existing 1,616-tag controlled vocabulary; uncertain tags stay marked as candidates.
- Strict filters never silently relax. Result metadata distinguishes discovered, abstract-screened, fulltext-indexed, verified, and reproduced work.
- Relevance explanations point to provenance and supporting text/pages whenever available. Never fabricate an unavailable PDF, DOI, venue rank, page, experimental outcome or citation.
- Preserve user privacy, source records, stable Paper_IDs and incremental indexing state.

## Current inputs (NOT ingested into an app yet)

- [AI/ML Drive folder](https://drive.google.com/drive/folders/1tUj_kTXYSAuBCXlnGNK-HpUQBfn5r7R1)
- [Canonical taxonomy workbook](https://docs.google.com/spreadsheets/d/1aFPn80GxpTaapzMnIc6dJlE1esn0W9Lk/edit)
- [Existing research notes](https://drive.google.com/file/d/1OGBNkcObBPjrEzoO1TJBsuU9gkA-rERa/view)
- [Venue-quality policy](https://drive.google.com/file/d/19TraX52uXqq7NhX7b1InkafB60yMtPAj/view)
- [Catalog archive](https://drive.google.com/file/d/12o8VtbYbGgIUmpyRr29v4nYCBBwLpIPg/view)

The Drive workbook reports 1,616 canonical tags, 2,478 discovery candidates and 3,197 candidate paper/tag links. Only 35 records are described as screened in the research notes, and none as fully read. The previous collection confirmed zero downloaded PDFs. These are **external source inventory numbers**, not app capability metrics or validated annotations.

## Suggested architecture (subject to benchmark gates)

| Layer | Initial proposal |
|---|---|
| Desktop | Tauri 2 + React/TypeScript |
| Local service | Python worker/sidecar, narrow authenticated IPC |
| Metadata | SQLite with migrations, constraints and provenance |
| Search | SQLite FTS5 or LanceDB FTS + LanceDB dense vectors; hybrid RRF |
| Embeddings | google/embeddinggemma-2; text-only 270M configuration, 768d index |
| PDF ingestion | PyMuPDF baseline, Docling optional rich layout fallback |
| External adapters | Drive read-only, Zotero Local API, OpenAlex, Crossref, Semantic Scholar |
| Quality | Relevance gold set, labeled test queries, reproducible BM25/dense/hybrid ablation |

## Documentation map

- [progress.md](progress.md): verified done/in-progress/backlog, acceptance gates and handoff.
- [AGENTS.md](AGENTS.md): binding implementation protocol for AI coding agents.
- [Product requirements](docs/PRODUCT_SPEC.md): user stories, workflows, scope and nonfunctional requirements.
- [Architecture](docs/ARCHITECTURE.md): modules, lifecycle, offline behavior and deployment.
- [Data model and taxonomy](docs/DATA_AND_TAXONOMY.md): normalized relations and provenance; machine-readable draft in [spec/schema.sql](spec/schema.sql).
- [Search/retrieval specification](docs/RETRIEVAL_SPEC.md): query planner, operators, ranking, grouping and bridge queries.
- [Ingestion and synchronization](docs/INGESTION_AND_SYNC.md): source identity, PDFs, Drive, Zotero and discovery.
- [UI/UX specification](docs/UI_UX_SPEC.md): screens, facets, paper inspector and visualizations.
- [Evaluation and tests](docs/EVALUATION_AND_TESTS.md): gold queries, acceptance criteria, metrics and model comparisons.
- [Security and privacy](docs/SECURITY_PRIVACY.md): trust boundaries, local data and secret handling.
- [Decisions and references](docs/REFERENCES_AND_DECISIONS.md): source URLs, assumptions and open ADRs.
- [Sample queries](spec/search_queries.json): initial executable-style acceptance fixtures.

## First contribution

Do NOT claim this README provides a working desktop app. Follow Stage 0 in [progress.md](progress.md) to implement the smallest import and search vertical slice. For every task: tests + evidence + progress update + PR review.
