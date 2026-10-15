# Data model, taxonomy, quality and provenance

**Companion draft schema:** [spec/schema.sql](../spec/schema.sql). Implementation agents must convert to incremental versioned migrations with tests; this SQL is not a deployed database.

## Starting data (external Drive snapshot; not app state)

The linked taxonomy workbook reports 1,616 canonical tags across 18 namespaces and 42 subgroups, 2,478 paper candidates, and 3,197 paper–tag edges. The research notes mention only 35 screened records; none fully read. Most mappings came from lexical discovery and require manual QA. Full-text availability and PDF links must be distinguished; reported verified local downloads = 0.

Sources:
- Workbook: https://docs.google.com/spreadsheets/d/1aFPn80GxpTaapzMnIc6dJlE1esn0W9Lk/edit
- Policy: https://drive.google.com/file/d/19TraX52uXqq7NhX7b1InkafB60yMtPAj/view
- Scope: https://drive.google.com/file/d/1ly-GvzVRmut_InDjepFzWBCIJWr_csuL/view

**Do not silently copy an earlier local workbook over the Drive version.** Stage 0 compares remote source revision, local snapshots and schema columns.

## Core entities

- papers: canonical internal Paper_ID (preserve original when imported), bibliographic metadata, venue/review status, local/remote attachment distinction.
- source_records: immutable or versioned provider file/row payload, remote file ID, import run, evidence of authoritative source.
- paper_identifiers: DOI, arXiv, Corpus ID, OpenAlex work ID, publisher URL; case-normalized where appropriate.
- paper_versions: preprint/published/updated versions and canonical merge rationale.
- taxonomy_tags and aliases: existing 1,616 canonical tags with namespace, subgroup, description and lifecycle. Never treat aliases as separate active tags.
- paper_tags: MANY-to-MANY assertions, role, source, model confidence, QA status and supporting evidence. Never infer primary method from abstract keyword presence alone.
- sections/chunks: extracted source text with page boundary, parsing status, source hash and index version.
- concept_relations: typed edges (USES_METHOD, OPTIMIZES, APPLIES_TO, EVALUATED_ON, COMPARES_TO, CITES, EXTENDS, SUPPORTS_CLAIM, CHALLENGES_CLAIM), with verified vs inferred state.
- venues/venue_rankings: journal/conference identity and rank evidence per snapshot/year/category.
- artifacts: PDF URI/local path/verified checksum, code/dataset links and legal source.
- saved_queries / retrieval_runs / relevance_judgments: reproducibility and evaluation.
- job_runs / index_manifests: importing, parsing, embedding, sync and recovery.

## Identity and dedupe

1. Normalize DOI (strip DOI prefixes and trim/casefold), validate syntax without inventing values; strongest external key when trustworthy.
2. Compare arXiv stable ID (store version separately); handle multiple versions/published work links.
3. For absent identifiers, use normalized title+year+first author with human-review confidence and explicit collision handling; do not merge solely by approximate title.
4. SHA-256 identify identical PDF bytes; PDF file identity is NOT necessarily paper identity.
5. Preserve all original Paper_IDs as source identifiers even after canonical merging through paper_versions/source_records cross-reference.
6. Repeat imports must have same canonical paper count and mappings unless source version changed; generate a reconciliation report on discrepancies.

## Taxonomy semantics and relationship evidence

Namespaced taxonomy remains fixed until versioned review. Example tags known to exist: field/federated-learning, model/attention-mechanism, model/self-attention, method/fedamp, data/non-iid, inference/flash-attention, inference/kv-cache-compression, objective/low-latency and task/iot-intrusion-detection.

Per paper/tag assertion persist:
- role: primary_method, supporting_method, application, benchmark, objective, negative_result, survey_coverage, mention_only, candidate
- asserted_from: author_keywords, metadata, lexical_discovery, abstract_model, fulltext_model, human
- review_state: needs-manual-review, verified, rejected
- confidence: optional model-specific calibrated score, not automatic proof
- evidence_chunk_id, page and evidence_quote when available
- tag dictionary revision and annotated_at timestamp

Do not map survey_coverage/mention_only into a confirmed USES_METHOD edge. Absence of a tag does not mean absence of a method (especially before fulltext indexing).

Relationships cannot be established solely by embedding proximity. Store subject-predicate-object, extraction mode, supporting source and manual verification state. Contradictory claims remain separate annotated evidence, not overwritten.

## Publication eligibility policy

Primary eligible = verified publication evidence AND (SCImago/SJR Q1/Q2 journal or CORE/ICORE A/A* conference); preserve ranking year, category and source URL as separate columns. Workshop/Findings/demo tracks do not inherit parent main-conference ranks. Ranking may be from a different year than publication and must be shown as such. Unknown/ambiguous papers are 'unknown' or 'exploratory', never promoted to qualified. Scholarly relevance and scientific reliability are separate from venue rank.

## Evidence reliability

Levels: discovered, abstract-screened, fulltext-indexed, manually-verified, experiment-reproduced. Model confidence and human verification must be separate fields. Paper conclusions require attributable source text; analyst interpretations explicitly labeled as interpretations.

## FTS, vector and migration invariants

- SQLite foreign_keys=ON and transactions for import; uniqueness constraints prevent duplicate identifiers and mappings.
- FTS5 indexes normalized title/abstract/extracted text; never returns authoritative evidence not in source_record/chunk.
- Vector stores chunk ID, paper ID, raw source reference, and index_manifest ID; preserve 768d float vectors initially and MRL re-normalization rules.
- Index builds are idempotent, resumable and atomic; broken/obsolete manifest never silently searched.
- Provide schema migrations up/down or forward+backup policy, tested on seeded source fixtures and on re-import.
