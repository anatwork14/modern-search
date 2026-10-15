# Retrieval, scientific and product evaluation specification

No local benchmark has been run as of the initial specification (2026-10-15). Do not report invented accuracy, latency or memory values.

## Gold set

Create 60–100 representative research queries with two annotators or an explicit adjudication protocol; relevance scale 0=irrelevant, 1=loosely related, 2=relevant, 3=direct central mechanism. Record query intent, filters, language, expected document set, coverage of actually indexed corpus, and source note supporting each judgment.

Strata:
- Named methods/DOI/arXiv acronyms (FlashAttention, GQA, FedAMP, CICIoT2023).
- English semantic paraphrases and Vietnamese-to-English retrieval.
- Attention optimization by prefill/decode/KV memory/quality trade-off.
- Federated attention in client aggregation vs local encoders, personalized non-IID methods.
- FL+attention+IoT IDS cross-domain query: strict combined hits vs semantically related families.
- Constraint algebra: ANY/ALL within facet, AND across facets, explicit NOT; zero-result cases.
- Negative controls: misleading attention word in abstract, survey mentions, unranked preprint, duplicated DOI, corrupted remote-PDF link.
- Later: figure/table queries and citation graph provenance.

Use spec/search_queries.json as a *starter fixture*, not a labeled benchmark or evidence of successful retrieval.

## Comparisons / ablations

Every model should search identical corpus snapshot, filtering rules and query set:
1. BM25-only (lexical control).
2. EmbeddingGemma 2 270M text-only 768d.
3. BM25+Gemma RRF hybrid.
4. Hybrid + reranker (BGE-reranker-v2-m3 candidate).
5. Qwen3-Embedding-0.6B dense / hybrid alternatives.
6. Ablations: 768 vs 512/256/128 normalized MRL; title+abstract vs section chunks; chunk sizes; paper aggregation; prompt prefixes, synonym expansion, graph neighbor widening.
7. Figure retrieval using 440M text+vision configuration (future separate experiment).

Record embedding model revision, tokenizer library and version, prompt formatting, dimension, vector precision/normalization, CPU/GPU backend, Mac chip/RAM, dataset snapshot, paper count, passage count, rerank K, rank fusion weights, exact vs ANN indexing parameters.

## Metrics

- Recall@20, Recall@100 (judged corpus), nDCG@10 and MRR@10.
- Precision for typed methods/evidence; exact facet-filter correctness (target 100% on truth-table fixtures).
- Cross-domain grouping correctness, false-equivalence rate, explanation faithfulness and abstention correctness.
- Citation/page evidence validity; target zero fabricated page references.
- Query p50/p95 latency measured on representative warmed/cold conditions (separate lexical/dense/rerank), indexing docs/sec, model peak RSS, storage and failure/restart rate.
- Percentage corpus metadata-only / abstract-indexed / PDF-verified / fulltext-indexed / manual-verified.
- Incremental sync conflict rate, skipped/duplicate source rows, parsing failures.

## Initial target policy (proposals, not achieved results)

- Strict facets and policy constraints: 100% correct on deterministic truth-table tests.
- Page citations: 0 fabricated from absent PDFs.
- Recall@100 >= 0.90 is a *proposed* target for agreed judged query/corpus set; revisit once relevance labels exist.
- Interactive latency targets only after profiling target Mac classes; do not set untested absolute milliseconds as fact.
- Prefer model with best recall/latency/cost trade-off on user-specific data, not public leaderboard alone.

## Test layers and acceptance gates

Unit:
- identifier normalization, dedup collisions, taxonomy aliases, AST validation, filter SQL truth tables, RRF, score pagination, BM25 exact phrase fallback, index manifest mismatch.
- prompt correctness (SearchQuery vs titled documents), MRL dimension equivalence/re-normalization.
- evidence confidence/role transitions (candidate must not become verified without explicit QA).

Integration:
- import/reimport source workbook and verified fixtures; transaction cancellation/resume; parser failures; PDF remote/local differentiation.
- local offline lexical search, dense service failure fallback, hybrid retrieval and saved query round-trip.
- cross-domain query boundaries and no fabricated citations; evidence page mapping on known test PDFs.
- full index rebuild, crash recovery, rollback and cross-model mismatch rejection.
- providers disabled offline and source scope no implicit network transfer.

Desktop:
- startup/exit, sidecar isolation, focus/keyboard accessible query/facets, progress/cancel, indexing status and backup restore.
- packaging and OS security smoke tests when executable exists.

Security:
- reject remote SSRF destinations and unexpected redirects; no executable PDF instructions; no credentials in logs; no loopback unauthenticated APIs; corrupt PDF bounded parse.

## Report template (required for benchmark PR)

Date; commit; corpus SHA/snapshot; device chip/RAM/OS; model checkpoint; Python/package versions; parser/chunker; query set + graded labels; retrieval variants; metric table; p50/p95 breakdown; accuracy/latency regressions; qualitative false negatives/positives; recommendation with uncertainty; raw reproducibility command and output artifact path.

## Example expected distinctions

- FlashAttention: IO-aware attention computation; GQA: KV-head sharing; PagedAttention: KV page allocation; H2O/SnapKV: KV retention/selection. Each must be grouped by actual optimization bottleneck.
- FedAMP: attentive inter-client collaboration; FedALA: adaptive aggregation and personalization but not necessarily attention. Search must not present both as equal "attention models".
- Attentive IDS feature extraction != attentive federated aggregation. Combined paper must explicitly meet relevant conditions.
