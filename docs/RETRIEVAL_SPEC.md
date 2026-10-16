# Search, embeddings, ranking and cross-domain discovery

## Search contract

Every search request has a natural-language query, a parsed query plan, search mode, indexing scope, hard constraints, candidate routes and an evidence policy. The user always sees *why* a paper matched and whether expansion occurred.

Modes:
- STRICT: literal/phrase/method terms and exact tag/metadata facets; no silent relaxations.
- BROAD: synonyms, semantic paraphrases and soft SHOULD concepts, grouped by mechanism.
- BRIDGE: retrieve each domain independently, then intersections plus transferable mechanisms; clearly label verified combined work vs proposed analogies.
- EXHAUSTIVE DISCOVERY (later): many query variants + citation-neighbor retrieval + dedup, cursor pagination and coverage report; never claim globally complete results.

## Query planner AST

~~~json
{
 "query": "attention mechanisms to reduce LLM KV-cache cost",
 "mode": "BROAD",
 "scope": "LOCAL_ONLY",
 "hard_filters": {
   "eligibility": ["verified-qualified"],
   "review_state": ["discovered", "abstract-screened", "fulltext-indexed", "manually-verified"],
   "facets": [
     {"namespace":"field","operator":"ANY","tags":["field/large-language-models"]}
   ],
   "exclude_paper_ids": []
 },
 "soft_concepts": {
   "mechanisms":["GQA","MQA","FlashAttention","sparse attention","KV retention"],
   "objectives":["latency","memory","throughput"],
   "stages":["prefill","decoding"]
 },
 "group_by":["optimization_bottleneck","mechanism_family"],
 "ranker":"RRF",
 "include_exploratory":false
}
~~~

Validation: canonical tag names must exist, validate allowed predicates, avoid arbitrary SQL expression input, reject unknown operators, ensure source scope was explicitly selected. Within-facet ANY => SQL OR, ALL => AND through relational division or count distinct; across required facets AND; NOT is explicit exclusion. Differentiate required taxonomy assertions by review_state and role.

## Retrieval stages

1. Normalize and language-identify query but preserve acronyms, formulae and quotes; detect DOI/arXiv IDs as direct lookup route.
2. Interpret intent and show expanded concepts. Use taxonomy aliases; cache plan with planner/prompt version. Deterministic rules first; optional local model for assisted planning later; never add a hard filter not requested.
3. Apply metadata/quality filters. For hard constraints, avoid returning filtered-out candidates as final hits even if dense similarity is high. Execute SQL pre-filter or post-filter correctly with recall accounting.
4. Lexical top-K: FTS5/BM25 title, abstract, sections and canonical tag labels/aliases; tune field weights; exact phrase and cited identifiers are high-value.
5. Dense top-K: Embed query with asymmetric SearchQuery prefix; retrieve from versioned 768d document-chunk index. Aggregate top sections and title+abstract vectors as separate document units.
6. Merge candidate lists by RRF(d) = sum_i weight_i/(k+rank_i(d)); k=60 is an initial tunable baseline, not a universal optimum. Do not add raw BM25 and cosine without score calibration.
7. Optional cross-encoder rerank top 30–100 candidate passages (BGE-reranker-v2-m3 is an evaluation candidate). Respect timeout and offer fallback.
8. Deduplicate passages at paper level; show best 2–3 matching sections. Apply diversification carefully after relevance.
9. Group by method family, bottleneck, objective, domain and annotated mechanism relation. Concept clusters are *navigation*, not evidence of scientific equivalence.
10. Return ranked cursor pagination with total candidate count, actual indexed corpus coverage, stage timings and complete match explanation.

## EmbeddingGemma 2 contract (official Google 2026 release)

Model: https://huggingface.co/google/embeddinggemma-2. Full 740M; text-only 270M by omitting vision/audio configs; text+vision 440M; shared 768d representation; 8,192 token text context; MRL 512/256/128. Default V1 uses text-only 768d. GPU backend and memory footprint are not yet measured.

- Query text: task: search result | query: {query}
- Titled document: title: {title} | text: {passage}
- Untitled document: title: none | text: {passage}
- Question answering and fact checking have distinct task prefixes; use only when explicitly evaluating that retrieval task.
- SentenceTransformers SearchQuery prompt_name may apply query prefix; Document shortcut supplies title: none, so build manual titled inputs.
- For selective text-only loading, test config_kwargs={"vision_config":None,"audio_config":None} on pinned version.
- If truncating MRL embeddings, normalize AFTER truncation, and query + index dimensions MUST match.
- Manifest must include checkpoint revision, tokenizer, template, normalization, dimension and source content version; fail closed on mismatch.
- Benchmark Qwen3-Embedding-0.6B as an alternative; no model wins until measured on corpus.

## Faceted grouping UX

- Filters: fields, tasks, methods, architectures, learning paradigms, objectives, evaluations, benchmark, data, domain, model, year, publication rank, tag evidence role, review_state, remote/local PDF, code link.
- Saved filter groups: reusable named subsets of tags (e.g. "Attention Optimization" expands to flash/sparse/GQA/MQA/KV mechanisms); semantic membership and hard tag condition remain separate.
- Live facet counts reflect currently filtered candidate set, not global estimates.
- Explain zero results and offer user-approved broad search outside strict group.
- Emit matched routes: EXACT_TERM, TAG_VERIFIED, TAG_CANDIDATE, SEMANTIC, GRAPH_NEIGHBOR, CROSS_DOMAIN_ANALOGY, with evidence source.

## Concrete research cases

A. "attention improve LLM inference" => separated: IO-aware kernels (FlashAttention), KV-head reduction (GQA/MQA), important KV retention (H2O/SnapKV), sparse/long-context mechanisms, memory allocation/serving (PagedAttention). PagedAttention is serving/memory management rather than an interchangeable attention kernel. Include model quality regressions and hardware/workload caveats.
B. "Federated learning using attention" => attention inside client feature encoders, attention among clients/message weights (FedAMP), adaptive local/global personalization (FedALA, NOT automatically attention), attention-based IoT intrusion detectors. Do not claim these families are one mechanism.
C. "FL attention IoT IDS" => 3 groups: FL aggregation-attention, IDS classifier-attention, confirmed combined methods. If no paper satisfies all hard conditions, show zero combined verified with separate literature groups as optional bridge suggestions.
D. "importance signals for cache/FL aggregation" => surface graph neighbor importance, token salience, client trust/reliability, and unproven transfer hypotheses with limitations.

## Relevance and provenance policy

- A lexical paper-tag candidate is not a verified primary-method assertion.
- Only show page references if extracted and auditable to stored PDF bytes/source page.
- If embedding retrieval finds an analogous paper, describe "potentially related" instead of "same method".
- Capture query planner, expanded terms, retrieval index, hard constraints, source scope, scores/ranks, evidence text and user feedback for reproducibility.
- External exploration adds discovered candidates to a separate review queue; it never silently changes the qualified primary corpus.
