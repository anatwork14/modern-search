# Sources, technical decisions, open questions and ADR registry

## Decision record — as of 2026-10-15

ADR-001 **Local-first macOS desktop** — Tauri 2 + React/TS, Python local worker. Rationale: local privacy, packaged app, Python embedding/PDF ecosystem. Status: proposed, not implemented.

ADR-002 **SQLite metadata and taxonomy** — one relational authority, many-to-many tag assertions with evidence. Status: proposed schema awaiting migrations/validation.

ADR-003 **Hybrid search** — BM25 (prefer SQLite FTS5 V1) + embedded LanceDB dense search + weighted RRF (k=60 initial candidate) + optional reranking. Status: proposed; comparative retrieval test required.

ADR-004 **EmbeddingGemma 2 text-only baseline** — google/embeddinggemma-2 270M effective text configuration, native 768d, asymmetric SearchQuery/titled-document prompts, manifests. Status: documentation verified; macOS runtime untested. Alternative Qwen3-Embedding-0.6B remains benchmark candidate. Full multimodal 740M and text+vision 440M are later.

ADR-005 **Data authority** — import Drive workbook and stable Paper_IDs with provenance, NOT a new speculative taxonomy. Status: source inspected remotely, local ingestion pending.

ADR-006 **Publication quality** — qualified paper gate based on evidence plus Q1/Q2 SJR or A/A* CORE/ICORE rank, preserving ranking year, official source; exploratory preprints separate. Status: external policy defined, enforcement pending.

ADR-007 **Citation and concept graph** — relational edges with typed evidence in SQLite first, not Neo4j or a second stateful service. Status: proposed.

ADR-008 **Avoid premature services/agents** — no Qdrant, server search, hosted LLM requirement or elaborate multi-agent platform in first usable release. Revisit only against measured requirements.

## Open decisions requiring evidence

- Native code layout: Tauri Rust commands + Python sidecar protocol and packaged environment.
- Fastest reliable MPS/CPU/MLX EmbeddingGemma backend on target Macs.
- Whether FTS5 is enough vs LanceDB FTS when corpus reaches large PDF-scale volumes.
- Optimal chunk size/overlap/section boundaries, BM25 title weighting, RRF weights, rerank cutoff.
- UI indexing trigger and model download/cache experience; size and offline installer behavior.
- Provider rate limits/access scopes, conflict policy for eventual Drive/Zotero write features.
- Exact app identity/branding "modern-search" vs "ResearchOS", packaging and notarization budget.
- How to generate/maintain human relevance judgments and annotation review workflow.

## Verified primary documentation for implementation

- EmbeddingGemma 2 official launch (2026-10-06): https://blog.google/innovation-and-ai/technology/developers-tools/embeddinggemma-2/
- EmbeddingGemma 2 developer guide and prompts: https://developers.googleblog.com/embeddinggemma-2-the-developer-guide/
- Google model card: https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2
- Hugging Face checkpoint: https://huggingface.co/google/embeddinggemma-2
- SentenceTransformers inference guide: https://ai.google.dev/gemma/docs/embeddinggemma/inference-embeddinggemma-with-sentence-transformers
- Qwen3 embedding baseline: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- BGE reranker baseline: https://huggingface.co/BAAI/bge-reranker-v2-m3
- Tauri v2 sidecars: https://v2.tauri.app/develop/sidecar/
- SQLite FTS5: https://www.sqlite.org/fts5.html
- LanceDB hybrid: https://docs.lancedb.com/search/hybrid-search/
- Docling: https://github.com/docling-project/docling
- PyMuPDF: https://pymupdf.readthedocs.io/
- Zotero Local API: https://www.zotero.org/support/dev/web_api/v3/local_api
- OpenAlex: https://help.openalex.org/how-to/api-recipes/
- Crossref REST: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- Semantic Scholar: https://api.semanticscholar.org/api-docs/
- arXiv categories: https://arxiv.org/category_taxonomy

## Primary papers for example queries

- FlashAttention: https://arxiv.org/abs/2205.14135
- GQA: https://aclanthology.org/2023.emnlp-main.298/
- PagedAttention/vLLM: https://doi.org/10.1145/3600006.3613165
- H2O: https://proceedings.nips.cc/paper_files/paper/2023/hash/6ceefa7b15572587b78ecfcebb2827f8-Abstract-Conference.html
- SnapKV: https://proceedings.neurips.cc/paper_files/paper/2024/hash/28ab418242603e0f7323e54185d19bde-Abstract-Conference.html
- FedAMP: https://ojs.aaai.org/index.php/AAAI/article/view/16960
- FedALA: https://ojs.aaai.org/index.php/AAAI/article/view/26330

## Source limitations

Three user-provided X posts were linked in the originating research discussion, but their content was not independently available; rely on Google's first-party material rather than attributing unseen claims. The local search and benchmark numbers remain unknown, and the full tagged Drive corpus has not been independently checked article-by-article. This repository should not claim it has run those experiments.
