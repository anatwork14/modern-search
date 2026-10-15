# Application profiles and multi-domain deployment

**Status:** design proposal. ResearchOS starts with academic AI/ML literature; every other domain requires a separate opt-in profile with explicit indexing scope and evidence rules.

## Why application profiles instead of separate apps

The same primitives—identity, chunks, metadata, taxonomy/facets, lexical+dense search, source evidence, versioned index and read-only APIs—can serve more than academic papers. Differences belong in source adapters, schema/facets, citation/evidence standards and ranking/evaluation policies, not duplicated codebases.

| Profile | Core input types | Retrieval intent | Specialty evidence | Risk/gate |
|---|---|---|---|---|
| Academic Research (FIRST) | Papers, abstracts, PDFs, BibTeX, Zotero/Drive | Method, benchmark, related work, limitations | DOI/arXiv, venue evidence, page passages | Validate citations and paper-tag roles |
| AI Research Engineering | Papers + GitHub source, README, issues, benchmark reports, MLflow runs | Paper→code→experiment, implementation lookup | Repo commit, code line range, dataset/run hash | Never execute repository code on import |
| Software Architecture | RFCs, ADRs, repos, design docs, logs | Design decisions, alternatives, bug history | file path, line, commit, decision date | Code index ACLs, secrets exclusion |
| Patent / Prior Art (PILOT) | Granted applications, claims, citations, standards | Similar mechanism, novelty clues, historical prior art | patent ID, claim number, jurisdiction, filing date | **Not** legal novelty clearance, status/jurisdiction checks |
| IoT / Cybersecurity (PILOT) | IDS papers, network documentation, configs, standards | Methods under constraints, attack models, datasets | deployment assumptions, testbed, attack/dataset split | Don't include operational exploit guidance in outputs without safety review |
| Science / Biomedical (FUTURE) | PubMed metadata, articles, protocols, studies | Study design and intervention evidence | population, outcome, limitations, regulatory status | No clinical decisions; explicit review and evidence grading |
| Education / Thesis (PILOT) | Course PDFs, lecture slides, own notes, papers | Learning paths, concept prerequisites, source-backed MCQ | note/page/section and authorship | Distinguish user notes from published facts |
| Product / Market Intelligence (FUTURE) | Product docs, public filings, policy, research | Technology landscape, technical competitor scan | dates, companies, source authenticity | No guaranteed stock/financial or strategic recommendations |
| Enterprise Knowledge (FUTURE) | Internal docs, tickets, approved repositories | Find decisions, architecture, support knowledge | ACL, owner, revision, restricted access | RBAC + audit + deletion propagation required |

## Profile descriptor contract

- profile_id/version, display_name, default_corpus_scope, allowed_media_types.
- source_adapter_ids, extractor_ids, citation/evidence format and document identity keys.
- facets/taxonomy namespace(s), quality gates, search presets, rerank and grouping strategies.
- indexed fields, block/page/line offsets and source metadata schema.
- export adapters, UI tabs, access permissions and data retention policy.
- feature dependencies and explicit enable/disable setting.

If a profile requires high-stakes accuracy (medicine/law/finance), ship only domain-specific retrieval and source evidence unless expert review has established safe decision boundaries.

## Cross-profile bridge queries

Can search two or more profile-scoped baskets with an explicit consent and capability boundary, then create mechanism-analogy links. Never merge text/index ACLs or pretend shared concept names imply identical definitions. Every result contains its source profile, retrieval method, role and quality state.

Example: scientific attention mechanisms ↔ GPU scheduling docs ↔ FL aggregation studies. Proposed transfer cards cite sources and specify differences and failure conditions.

## Delivery sequence

1. Academic Research — stable and benchmarked.
2. AI Research Engineering — integrate code repo metadata, benchmark/MLflow links and line-level evidence.
3. Education / Thesis — reuse paper + user notes, export study and literature-review artifacts.
4. Patent / standards pilot — claim-specific schema with careful disclaimers.
5. Other profiles only after real users and quality criteria.
