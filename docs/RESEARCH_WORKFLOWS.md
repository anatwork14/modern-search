# High-impact research workflows: evidence, comparison, bridge, experimentation

**Status:** proposed workflows; algorithms and example scenarios must be validated on an indexed corpus.

## A. Research project workspace

Every workspace records:
- research question, evolving hypotheses, scope constraints (publication period, quality tier, source types);
- query history with parsed AST, expanded keywords, corpus/index snapshot and online API provider;
- inclusion/exclusion log (human decision + reason), pinned papers and saved filters;
- reading state and structured contribution/assumption/limitation fields;
- comparison matrix with source-backed cells; missing fields "not extracted";
- linked implementation/experiment runs with reviewer status; export markdown/CSV/CSL/BibTeX.
This supports exploratory and systematic-style workflows; **does not imply PRISMA compliance automatically**.

## B. Typed claim/evidence extraction

Data structure for one claim:
- claim_id, canonical paper_id, subject, predicate, object, polarity, method_role (proposed/baseline/ablation/mentioned), experiment_context;
- exact evidence_span with document SHA, page/section offsets, quote and parser confidence;
- extraction method/model revision/confidence; reviewer state pending/verified/rejected;
- extracted quantities include unit, direction, source table, baseline, dataset, hardware and uncertainty.
Candidate claims cannot be advertised as verified findings. Contradictions require compatible setting; conflicting metrics on different benchmarks or hardware should not be treated as direct contradictions.

Comparison table types: method family, core idea, formal objective/complexity, stage (training/prefill/decode), tested model/hardware/dataset, metric definitions, baseline, reported gain, limitations, reproducibility, raw supporting evidence. Do not compare percentages without matching metric definitions.

## C. Mechanism bridge engine (distinctive capability)

Input includes source domain, destination domain, optimization objective and target constraints. Plan two independent high-recall searches, then connect via **typed mechanism roles** and supporting evidence:

1. Identify source mechanism: inputs; weighting/selection/routing/allocation rule; control loop; objective; compute/memory/communication cost; supervision; limitations.
2. Identify target problem: entities, timescale, observed feedback, latency/compute/network/privacy constraints, failure modes.
3. Detect structural analogy such as select-high-value-elements-under-budget, soft importance weighting, sparse communication or hierarchical routing; label only a **hypothesized correspondence**.
4. Construct bridge card with citations in both domains, disanalogies, transfer assumptions, minimum viable falsification experiment, metrics and baseline.
5. Rank cards using evidence coverage, mechanism match, plausibility and novelty-to-local-corpus as independent factors; do not produce a single fake "novelty probability".
6. Human reviews the bridge and can promote to explicit research hypothesis.

### Example — KV cache vs FL client selection

| Source inference mechanism | Target FL/IoT formulation | Critical non-equivalence |
|---|---|---|
| Keep salient KV tokens under memory budget | Select high-value clients under round/communication budget | Token salience != client reliability or trust |
| Group queries sharing KV heads (GQA) | Cluster client behaviors for aggregation | Sharing representation != sharing noisy client updates |
| Recency + heavy-hitter retention | Combine short-term attack recency and long-term client trust | Token attention weights are not secure OOD trust estimates |
| Block-sparse attention / routing | Sparse communication over edge devices | Latency and bandwidth, not token attention FLOPs, dominate |

Candidate hypotheses: context-adaptive client scheduling under bandwidth constraints; non-IID attack-drift-aware aggregator with trust regularization; shared backbone + selected personalized adapters. All require non-IID and OOD controls, security/Byzantine stress tests, comm-round and detection F1/DR/FPR metrics.

## D. Paper→code→experiment provenance chain

Link:
paper ID → reported claim/metric → author code URL → repository COMMIT SHA → environment lock/config → dataset fingerprint/split → artifact/run ID (MLflow optional) → measured metric (user's run) → discrepancy.
Require explicit status: AVAILABLE_CODE, BUILDABLE, RUNNABLE, PARTIALLY_REPRODUCED, REPRODUCED, NOT_TESTED, FAILED, INCOMPARABLE. Never equate repo exists with reproducible result. Keep license and safety checks before any code execution.

## E. Robust evidence-grounded synthesis

Workflow: retrieve high-recall passages → extract typed evidence → cite source per assertion → answer user's question with contrasting interpretations and missing evidence → link to exact passages → allow reviewer correction. Local LLM optional after retrieval; no requirement to add one to V1. Generation must abstain where evidence insufficient. Citation presence is not factual grounding; tests measure support and misleading citation rate.

## F. Literature evolution and alerts

Persist a query snapshot; with user opt-in, fetch provider changes at appropriate cadence, dedupe DOI/arXiv, recheck publication evidence and eligibility, compare previously unseen works. Notify only high-relevance *new* items and explain the source and cause. No default always-on surveillance or expensive scheduled GPU process.

## G. Export and reproducibility

Markdown summary with linked pages, CSL/BibTeX/RIS and structured CSV; full query manifest and sources snapshot; text citation style and copied excerpt lengths respect license; optional notebook or PR draft with explicit user confirmation. Export must be regenerable from stable IDs and indexed versions.

## Acceptance tests

- Every comparison cell has matching source reference or explicitly unknown.
- Bridge ranking not dependent solely on embedding cosine, and labels analogy separate from empirical finding.
- Counterfactual/negative test: "FedALA is attention by definition" must be rejected unless a particular paper provides that architecture.
- Experiment comparison forbids different metrics/hardware silently labeled directly comparable.
- Results of saved systematic review reproduce same local snapshot in offline mode.
