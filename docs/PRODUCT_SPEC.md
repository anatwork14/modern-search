# Product specification (PRD) — ResearchOS

**Product:** modern-search / ResearchOS. **Version:** 0.1 proposal. **Target:** macOS-first standalone desktop app, local-first by default. **Status:** design only.

## Problem

Researchers maintain PDFs, spreadsheets, DOI/arXiv bookmarks, annotations and loosely structured tags. Exact search loses paraphrased or cross-domain mechanisms. Embedding-only search loses named methods and deterministic filtering. A flat tag match often conflates a survey's mention with an experimentally used method. Existing Drive catalog is broadly discovered but not fully verified or PDF-indexed.

## Primary goals

G1. Find the most related papers in the user's *indexed corpus* for technical English/Vietnamese questions, with explicit evidence and coverage limits.
G2. Filter/group thousands of papers using 1,616 existing canonical tags and role-aware assertions, ANY/ALL/NOT operators, venue/year/verification constraints.
G3. Find mechanism transfer opportunities across domains, especially attention-for-LLM-inference and attention-for-FL/IoT IDS, without claiming analogous mechanisms are identical.
G4. Build a reliable research workspace: save queries, reading queue, notes, comparisons, evidence references, and reproducible exports.
G5. Keep local papers/notes private by default and operate search without internet access after setup.

## Primary workflows

W1 **Exact method lookup:** search GQA, FedAMP, CICIoT2023 or FlashAttention; retrieve title/abstract and source URL with exact-match highlight and sorted related papers.
W2 **Broad research question:** "How can attention reduce prefill compute and KV-cache memory?" Plan method-family expansions, retrieve semantic+lexical candidates, group by IO kernels, KV-head sharing, cache policy, sparse attention and serving.
W3 **Cross-domain bridge:** "Federated learning using attention" returns independent groups for attention inside client models, attention over clients, adaptive personalization (not automatically attention), and FL+attention+IoT IDS.
W4 **Faceted exploration:** select field/FL AND (method/FedAMP OR method/personalized-FL) AND data/non-IID; optionally verified only, Q1/Q2/A/A*; count and explain empty intersections.
W5 **Evidence review:** open PDF at real page; confirm/reject a generated method/limitation tag and save reviewer notes; no page shown if PDF absent.
W6 **Offline research:** disable network; search indexed local data, read imported PDFs, save queries; online discovery requests remain user-triggered.

## Personas

- Student/researcher: high-recall reading list and research-gap discovery.
- Technical ML engineer: algorithm details, hardware/latency constraints, related implementations.
- Research reviewer: verification of venue, method roles, citations and limitations.
- Coding agents: safe source-backed API to query curated library, not an unbounded shell tool.

## In scope V1

Drive workbook import; deduped bibliography; 1,616-tag dictionary and aliases; role/evidence distinctions; English/Vietnamese query; BM25 and text embeddings; RRF; deterministic advanced facets; lists/groups and paper inspector; saved queries; offline execution; local backup/reindex. Start with metadata/abstract when PDF absent. PDF section extraction and reranker are subsequent staged work.

## Post-MVP

OCR, page-grounded full-text viewer, citation graph, discovery APIs, relevance-learning, Zotero local API, Drive change sync, multimodal figures, comparison matrices and agent-facing read-only retrieval endpoints.

## Explicit non-goals V1

- Exhaustive global scholarly search or guaranteed discovery of every related paper.
- A general LLM chatbot claiming to reason over papers with no inspectable citations.
- Blindly downloading copyrighted PDFs or presenting URLs as downloaded files.
- Automatic confirmation of a paper's correctness, reproducibility or full-read status.
- Continuous cloud sync, realtime collaboration or a remote hosted database.
- Running GitHub/PDF-supplied code or instructions autonomously.
- Premature vector-server clusters, graph databases, or orchestration frameworks.

## Publication policy

Default primary library: Q1/Q2 SCImago/SJR journal OR A/A* CORE/ICORE conference **with publication evidence**; persist rank year, official source and category. arXiv-only is exploratory unless independently published in an eligible venue. Rank ≠ correctness. Preserve unknown rank as unknown; give users explicit filter to include exploratory/unranked sources.

## Success definition

User can import and reconcile real Drive data, run three representative research query families with clearly differentiated mechanisms, filter on exact many-to-many tags, read relevance explanations backed by source, save the query, and repeat search offline. Quantitative goals and tests in EVALUATION_AND_TESTS.md; no fabricated benchmark numbers.

## User experience principles

Research-first rather than chat-first; show query interpretation and allowed expansions. Separate exact matches, semantic similarity, related/citation expansion, and hypothesized bridges. Make indexing coverage and annotation reliability visible. Keep the interaction keyboard-accessible, fast under realistic corpus sizes, and recoverable from interruptions.

## Long-term platform expansion (not V1 scope)

ResearchOS may add evidence-grounded claim comparisons, citation genealogy, cross-domain mechanism transfer, research project matrices, paper→code→experiment lineage and read-only agent/CLI access. The same local-first retrieval core could host multiple *application profiles* (technical documentation, source repositories, patent prior art, educational materials); each needs explicit source permissions, facets, quality policies and type-aware evidence. See [PLATFORM_EXPANSION_RESEARCH.md](PLATFORM_EXPANSION_RESEARCH.md) and [APPLICATION_PROFILES.md](APPLICATION_PROFILES.md).

Impact priorities: trusted retrieval and provenance first, then evidence comparison and researcher workflow, then testable concept bridges, then generic profiles. Automated novelty certification, uncontrolled paper-code execution and multiuser cloud collaboration are not MVP claims. Do not convert this into a chatbot or generic enterprise content management suite.
