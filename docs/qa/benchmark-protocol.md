# Retrieval benchmark protocol

No relevance, latency, memory, or throughput result is implied by this
protocol. The starter query file is not a judged gold set. A report must leave
an item `NOT RUN` until an operator records the command output and input
fingerprints.

## Before measuring

1. Freeze and record the corpus snapshot SHA, paper and passage counts, and the
   query-set file SHA. Keep private catalog rows and PDFs outside the repository.
2. Build a judged set with 60–100 representative queries and two annotators, or
   document an adjudicator and disagreement handling. Record query intent,
   hard filters, language, judged document IDs, 0–3 relevance labels, and a
   source note for every judgment. Do not turn synthetic fixtures into quality
   judgments.
3. Pin model checkpoint and revision, tokenizer, prompt policy, dimensions,
   normalization, parser/chunker versions, and retrieval parameters. State
   whether weights and corpus are local and whether the run was offline.
4. Record host model, RAM, OS, Python and package versions, storage medium, and
   device backend. Separate cold-start and warmed measurements; do not compare
   runs with different inputs or filters.

## Required comparison set

Run BM25-only, dense-only, and BM25+dense reciprocal-rank fusion against the
same frozen corpus, judged queries, and hard-filter policy. Add reranking or
dimension/chunk ablations only after their inputs and configuration are pinned.
Never report a score for a run that did not complete. The report must include
the raw command and output artifact path so another operator can reproduce it.

## Report template

```text
Status: NOT RUN | MEASURED
Date (local timezone):
Commit SHA:
Corpus snapshot SHA / access classification:
Query-set SHA / adjudication protocol:
Host chip / RAM / OS:
Python / relevant package versions:
Model checkpoint / revision / tokenizer / prompt version:
Parser / chunker / vector dimension / normalization:
Retrieval configuration and filter policy:
Offline confirmation and network guard:

Variant | Recall@20 | Recall@100 | nDCG@10 | MRR@10 | p50 | p95 | peak RSS
BM25-only | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN
Dense-only | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN
Hybrid | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN

Facet truth-table result:
Citation/page evidence audit:
Failures, false positives, and false negatives:
Raw command:
Output artifact path:
Limitations and uncertainty:
```

`NOT RUN` is the truthful value for all rows until an actual corpus run with
adjudicated relevance labels has been observed. Do not substitute a model card,
synthetic fixture, developer-machine smoke test, or UI screenshot for a
measurement.
