# ResearchOS platform expansion — evidence-backed opportunity study

**Reviewed:** 2026-10-15. **Status:** RESEARCH / PROPOSAL, not shipped product. **Purpose:** identify extensible, impactful uses beyond AI-paper search while protecting a small trustworthy search core. Refer to [EXTENSIBILITY_AND_PLUGIN_API.md](EXTENSIBILITY_AND_PLUGIN_API.md), [RESEARCH_WORKFLOWS.md](RESEARCH_WORKFLOWS.md), [APPLICATION_PROFILES.md](APPLICATION_PROFILES.md), and root [progress.md](../progress.md).

## Executive decision

Make **modern-search a local-first, evidence-centered Research Intelligence platform** with an academic-paper profile as its first product. Keep the same core indexing/retrieval/storage runtime; layer first-party optional modules for paper evidence, cross-domain exploration, code/experiment traceability and safe agent access. General document management, patents, standards and team enterprise workflows are **application profiles**, not new mandatory subsystems.

### What existing tools teach us (verified resources vs our inference)

| System | Demonstrated mechanism | Our justified extension; not a claim of novelty |
|---|---|---|
| PaperQA2 (Future House) | Scientific paper retrieval, agentic evidence gathering, citations, multi-source metadata | Evidence-backed research synthesis; evaluate output grounding rather than chat UX alone |
| OpenScholar (Nature 2026) | Evidence-grounded multi-paper synthesis and explicit citation accuracy assessment | Claim comparison and cite verification should be tested; generated prose never privileged over sources |
| OpenAlex | Works, topics, references, cited-by, related_works, search/filter/group/pagination; open scholarly entity graph | Metadata enrichment, backward/forward citation snowballing and freshness with source provenance |
| Semantic Scholar | Academic graph and recommendations, including positive/negative paper seeds | Explore beyond corpus, preserve rank/metadata provenance; network optional |
| Docling | Structured parsing across PDF/DOCX/PPTX/HTML etc., with tables/formulas/images/layout | Extensible document converter for high-value source types; do not mandate its heavy pipeline on every import |
| olmOCR/Marker | Specialized PDF/layout/math/table extraction with reported benchmark suites | Test specialized fallback on representative scientific PDFs, especially equations and figures |
| Khoj | Pluggable personal-knowledge search across multiple sources, local/self-hosted | Multi-corpus connector pattern, not an entire personal-assistant architecture |
| MLflow | Parameter/metric/artifact/run traceability for experiments | Link a literature claim to code, run, reproduction and observed limitations rather than asserting reproduction |
| Zotero Local API | Local bibliographic access | Bibliographic references and collection-aware import without direct Zotero DB writes |
| Citation.js | CSL, BibTeX, RIS import/export transformations | Versioned citation/export adapter; original metadata preserved |
| MCP (official specification) | Typed tools/resources, read-only capability exposure, authorization and human controls | Agent-facing query interface after internal API hardening; never default to arbitrary filesystem/tool execution |

Useful primary sources:
- https://github.com/future-house/paper-qa
- https://www.nature.com/articles/s41586-025-10072-4
- https://help.openalex.org/data/works/
- https://help.openalex.org/how-to/api-recipes/
- https://api.semanticscholar.org/api-docs/recommendations
- https://github.com/docling-project/docling
- https://github.com/allenai/olmocr
- https://github.com/khoj-ai/khoj
- https://mlflow.org/docs/latest/ml/tracking/
- https://www.zotero.org/support/dev/web_api/v3/local_api
- https://github.com/citation-js/citation-js
- https://modelcontextprotocol.io/specification/2025-11-25/server/tools

Caution: vendor-reported scores are not apples-to-apples; no benchmark on user's Mac or corpus exists. License and compatibility review is required before incorporating code or pretrained weights.

## Ranked opportunities

Priority classification: P0 = protect core MVP, P1 = high-value follow-on, P2 = post-MVP advanced, P3 = optional exploratory, DEFER = don't build until proven. "Impact" and "effort" are qualitative hypotheses rather than measurements.

| ID | Extension | Main user value | Impact | Effort | Timing |
|---|---|---|---|---|---|
| EX-01 | Claim/evidence extraction & comparison | Compare contributions/limitations with verified page passages | Very high | Medium-high | P1 after PDF evidence |
| EX-02 | Research workspace & structured matrices | Move from finding papers to answering a research question | High | Medium | P1 |
| EX-03 | Paper→code→experiment traceability | Separate published metric from locally reproduced metric | Very high | Medium-high | P1/P2 |
| EX-04 | Bridge search with mechanism ontology | Transfer an idea across attention, FL, IoT, systems, biology | Very high | High | P2 |
| EX-05 | Citation genealogy & evolution | Track predecessors, descendants and changing assumptions | High | Medium | P2 |
| EX-06 | Safe read-only MCP/CLI/JSON interface | Claude/Codex/Hermes can query grounded corpus | Very high | Medium | P1 after stable APIs |
| EX-07 | Source adapter SDK and corpus profiles | Same search engine supports code, manuals, standards, patents | High | Medium | P1 interfaces; P2 profiles |
| EX-08 | Novelty/contradiction hypothesis cards | Surface underexplored combinations with explicit uncertainty | Potentially very high | High | P2 experimental |
| EX-09 | Citation/BibTeX/report export | Useful outputs in LaTeX/Docs/Markdown | High | Low-medium | P1 |
| EX-10 | Topic freshness/subscriptions | Discover changed literature without constant manual searches | Medium-high | Medium | P2 opt-in |
| EX-11 | Equation/figure/table retrieval | Locate architecture visuals and mathematics | High for ML | High | P2 benchmark gate |
| EX-12 | Knowledge map/cluster timeline | Navigate mechanisms and trajectories | Medium | Medium | P2 after graph data |
| EX-13 | Team collaboration/RBAC/shared server | Group research and governance | Medium for individual | Very high | DEFER |
| EX-14 | Auto-running paper code/GPU training | Convenience but major security/reproducibility risks | Uncertain | Very high | DEFER; sandboxed explicit opt-in only |
| EX-15 | Autonomous paper-writing/novelty certification | Attractive but unreliable unsupported claims | High risk | Very high | DO NOT PROMISE |
| EX-16 | Full generic PKM, chat, task and calendar suite | Bloats focus and competes with stronger dedicated apps | Low marginal | Very high | DEFER |

## Research workflows with high expected utility

### W1: Concept map → literature matrix → evidence synthesis
"Understand how token importance is estimated in KV cache compression": retrieve, group submethods, identify cited equations/assumptions, build comparison columns, surface missing evidence, export linked notes with original page passages.

### W2: Cross-domain bridge — attention & federated learning
Two separate search baskets:
- Source mechanisms: token salience / gated attention / sparse retrieval / heavy-hitter selection in inference systems.
- Target constraints: client selection, communication budget, non-IID/OOD dynamics, Byzantine behavior in FL for IDS.
Bridge cards require **analogy mechanism**, **differences** (token ≠ client, feedback distribution, objective, trust), **transfer hypothesis**, **failure modes**, **falsifiable experiment**, **primary evidence**. Ranking similarity is only a discovery signal. No assertion that FL methods can be replaced with attention without validation.

### W3: Research evidence → code implementation → local result
Extract paper's documented approach and evaluation conditions; link author code and external commit ID, environment/data split, MLflow run and reproduced metric; flag mismatch, dataset leakage, missing seeds. Do not automatically execute unknown code. Reproduction score is not publication's reported number.

### W4: Systematic reading and scientific writing
Create a search log with query variants, database/provider coverage, screening decisions and inclusion/exclusion justification; deduplicate; generate evidence table and citation-backed narrative draft with quote/page checks. Not an automatic PRISMA-compliant systematic review without actual protocol/screening audit.

### W5: Ongoing work / topic change detection
User saves a query and opts into a daily/weekly manual or scheduled online discovery check. Incremental candidate arrivals are shown as **discovered, unverified**; notifications only when newly matched primary sources pass user-chosen quality policies. Search never silently changes prior literature review snapshot.

## Shared objects, differentiated products

Core objects: Source, Document, Work, Section, Chunk, Concept, EvidenceSpan, Assertion, Relationship, Artifact, Query, Collection, ExperimentReference, Job, Profile, PluginManifest.

Paper-specific fields and venue rules stay on Paper/Profile. Generic Documents can represent repository files, patents and design docs without requiring citation metadata.

Each application profile supplies: allowed document types, field schema, facet vocabulary, default search template, parser adapters, evidence rules, ranking policy, and export templates. Namespaces and evidence ontologies may be profile-specific; **never mix legal claims with academic research claims without explicit query-scope selection**.

## Technical extension strategy

Modular monolith first:
- **Core**: SQLite + indexed evidence, embedding abstraction, BM25/FTS5 + vector + RRF, query/filter AST, provenance, jobs.
- **Ports**: DocumentSource, Parser, EmbeddingProvider, RetrievalRoute, MetadataEnricher, Ranker, EvidenceExtractor, Exporter, Profile, AgentTool.
- **Adapters**: Drive, Zotero, local filesystem, GitHub, OpenAlex, Semantic Scholar, Docling, MLflow, Citation.js.
- **Module manifests**: declarative capabilities, schema and permissions, lifecycle; versioned host APIs. First-party in-process plugins only initially.
- **Views**: paper library, paper inspector, comparison matrix, relation explorer, experiments, profile-specific search.
- **Background**: on-demand jobs and opt-in incremental sync, never a required always-on daemon.

A single plugin registry and typed APIs is more maintainable than 20 agents/microservices. Each extension must document prerequisites, measured lift or validated user need, failure fallback, resources/privacy and test suite. Default footprint stays tiny when not enabled.

## Concrete falsifiable stage gates

- Extend only after P0 stable: full local retrieval and strict facets pass benchmark.
- Claim comparison EX-01: human-scored extraction precision and zero fabricated page pointers on curated PDFs; unknown fields explicit.
- Cross-domain EX-04: independent assessor labels bridge relevance and whether relation is direct evidence or analogy; report false-equivalence rate.
- Agent interface EX-06: offline read-only MCP tools give exactly same results as UI, no file access beyond app-approved corpus, negative permission tests.
- Experiment EX-03: each result includes paper ID, code repo and pinned commit, data snapshot, hardware, config, run ID, measured metrics, discrepancy annotation.
- Application profiles EX-07: source adapter contract test suite against academic PDFs, Markdown/GitHub and one other document type; no breaking changes to original paper library.
- Freshness EX-10: dedup across providers, rank evidence freshness, notices only for new scoped qualified items.
- Visual EX-11: compare text-only against text+vision on a labeled figure/equation retrieval set; Mac memory/latency measured.

## Risks and anti-patterns

- "Everything app" scope destroys clarity and release cadence.
- Semantic similarity mistaken for citations, correctness, novelty, causality or transferable mechanisms.
- Overaggressive knowledge-graph extraction produces misinformation loops.
- Automatic source ingestion violates publisher rights, terms or private document permissions.
- PDF text prompt injection affects agents; isolated extraction required.
- Rapid taxonomy expansion without aliases/roles duplicates meanings; retain controlled vocabulary governance.
- Too many new embedding models/indexes creates incompatible search results and bloated disk.
- Requiring online SaaS undermines local-first. Optional cloud/team extension requires separate threat model.
- Pure text search misses equations/figures, but multimodal model must prove benefit before default.

## Recommendation

Build **academic research first**, then ship evidence comparison, safe agent querying, code/experiment links and broad source adapters in that order. Make creative cross-domain ideas a central user workflow, **but hypotheses are research suggestions, not automatically validated findings**. Keep patents/enterprise/education as opt-in profiles reusing core, not separate platforms until demand proves value.
