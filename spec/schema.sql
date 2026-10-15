-- ResearchOS draft schema for SQLite. NOT executed or migrated.
-- Must be adapted into versioned migrations and tested before production.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS papers (
 paper_id TEXT PRIMARY KEY,
 title TEXT NOT NULL,
 abstract TEXT,
 publication_year INTEGER,
 venue_name TEXT,
 eligibility_state TEXT NOT NULL DEFAULT 'unknown'
  CHECK(eligibility_state IN ('unknown','exploratory','verified-qualified','verified-not-qualified')),
 review_state TEXT NOT NULL DEFAULT 'discovered'
  CHECK(review_state IN ('discovered','abstract-screened','fulltext-indexed','manually-verified','experiment-reproduced')),
 paper_url TEXT,
 pdf_url TEXT,
 local_pdf_path TEXT,
 pdf_sha256 TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS paper_identifiers (
 paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
 provider TEXT NOT NULL,
 normalized_value TEXT NOT NULL,
 source_url TEXT,
 PRIMARY KEY(paper_id, provider, normalized_value),
 UNIQUE(provider, normalized_value)
);
CREATE TABLE IF NOT EXISTS source_records (
 source_id TEXT PRIMARY KEY,
 paper_id TEXT REFERENCES papers(paper_id) ON DELETE SET NULL,
 provider TEXT NOT NULL,
 provider_record_id TEXT NOT NULL,
 import_run_id TEXT NOT NULL,
 source_version TEXT,
 content_sha256 TEXT,
 original_paper_id TEXT,
 raw_payload_json TEXT NOT NULL,
 imported_at TEXT NOT NULL,
 UNIQUE(provider, provider_record_id, source_version)
);
CREATE TABLE IF NOT EXISTS venue_rankings (
 ranking_id TEXT PRIMARY KEY,
 venue_name TEXT NOT NULL,
 venue_type TEXT NOT NULL CHECK(venue_type IN ('journal','conference')),
 system TEXT NOT NULL,
 rank_label TEXT NOT NULL,
 ranking_year INTEGER NOT NULL,
 category_or_basis TEXT,
 official_source_url TEXT NOT NULL,
 evidence_record_id TEXT,
 verified INTEGER NOT NULL DEFAULT 0 CHECK(verified IN (0,1))
);
CREATE TABLE IF NOT EXISTS paper_venue_evidence (
 paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
 ranking_id TEXT NOT NULL REFERENCES venue_rankings(ranking_id),
 publication_evidence_url TEXT,
 verified INTEGER NOT NULL DEFAULT 0 CHECK(verified IN (0,1)),
 PRIMARY KEY(paper_id,ranking_id)
);
CREATE TABLE IF NOT EXISTS tags (
 tag_id TEXT PRIMARY KEY,
 namespace TEXT NOT NULL,
 subgroup TEXT,
 label TEXT NOT NULL,
 description TEXT,
 taxonomy_version TEXT NOT NULL,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
);
CREATE TABLE IF NOT EXISTS tag_aliases (
 alias TEXT NOT NULL,
 tag_id TEXT NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
 PRIMARY KEY(alias,tag_id)
);
CREATE TABLE IF NOT EXISTS source_artifacts (
 artifact_id TEXT PRIMARY KEY,
 paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
 kind TEXT NOT NULL,
 remote_url TEXT,
 local_path TEXT,
 sha256 TEXT,
 byte_size INTEGER,
 download_state TEXT NOT NULL DEFAULT 'remote-only',
 verified_at TEXT,
 CHECK(download_state IN ('remote-only','downloaded-unverified','verified-local','invalid','missing'))
);
CREATE TABLE IF NOT EXISTS chunks (
 chunk_id TEXT PRIMARY KEY,
 paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
 artifact_id TEXT REFERENCES source_artifacts(artifact_id),
 section_heading TEXT,
 section_path TEXT,
 page_start INTEGER,
 page_end INTEGER,
 start_offset INTEGER,
 end_offset INTEGER,
 content TEXT NOT NULL,
 content_sha256 TEXT NOT NULL,
 parser_name TEXT NOT NULL,
 parser_version TEXT,
 extraction_confidence REAL CHECK(extraction_confidence BETWEEN 0 AND 1),
 CHECK(page_start IS NULL OR page_start >= 1),
 CHECK(page_end IS NULL OR page_start IS NULL OR page_end >= page_start)
);
CREATE TABLE IF NOT EXISTS paper_tags (
 assertion_id TEXT PRIMARY KEY,
 paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
 tag_id TEXT NOT NULL REFERENCES tags(tag_id),
 role TEXT NOT NULL DEFAULT 'candidate',
 asserted_from TEXT NOT NULL,
 review_state TEXT NOT NULL DEFAULT 'needs-manual-review'
  CHECK(review_state IN ('needs-manual-review','verified','rejected')),
 confidence REAL CHECK(confidence IS NULL OR confidence BETWEEN 0 AND 1),
 evidence_chunk_id TEXT REFERENCES chunks(chunk_id) ON DELETE SET NULL,
 evidence_quote TEXT,
 evidence_page INTEGER,
 annotated_at TEXT,
 UNIQUE(paper_id,tag_id,role,asserted_from)
);
CREATE TABLE IF NOT EXISTS concept_relations (
 relation_id TEXT PRIMARY KEY,
 paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
 subject_concept TEXT NOT NULL,
 predicate TEXT NOT NULL,
 object_concept TEXT NOT NULL,
 evidence_chunk_id TEXT REFERENCES chunks(chunk_id),
 asserted_from TEXT NOT NULL,
 confidence REAL,
 verified INTEGER NOT NULL DEFAULT 0 CHECK(verified IN (0,1))
);
CREATE TABLE IF NOT EXISTS citation_edges (
 citing_paper_id TEXT NOT NULL REFERENCES papers(paper_id),
 cited_paper_id TEXT NOT NULL REFERENCES papers(paper_id),
 provider TEXT NOT NULL,
 source_url TEXT,
 PRIMARY KEY(citing_paper_id,cited_paper_id,provider)
);
CREATE TABLE IF NOT EXISTS saved_queries (
 query_id TEXT PRIMARY KEY,
 name TEXT NOT NULL,
 query_text TEXT NOT NULL,
 query_ast_json TEXT NOT NULL,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS index_manifests (
 index_id TEXT PRIMARY KEY,
 model_id TEXT NOT NULL,
 checkpoint_revision TEXT NOT NULL,
 tokenizer_version TEXT,
 prompt_template_version TEXT NOT NULL,
 dimension INTEGER NOT NULL CHECK(dimension IN (128,256,512,768)),
 normalized INTEGER NOT NULL CHECK(normalized IN (0,1)),
 corpus_snapshot TEXT NOT NULL,
 parser_chunker_version TEXT,
 build_state TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS job_runs (
 job_id TEXT PRIMARY KEY,
 job_type TEXT NOT NULL,
 input_source_id TEXT,
 status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed','cancelled')),
 checkpoint_json TEXT,
 error_json TEXT,
 started_at TEXT,
 finished_at TEXT
);
CREATE TABLE IF NOT EXISTS retrieval_runs (
 run_id TEXT PRIMARY KEY,
 query_id TEXT REFERENCES saved_queries(query_id),
 query_text TEXT NOT NULL,
 query_ast_json TEXT NOT NULL,
 index_id TEXT REFERENCES index_manifests(index_id),
 result_ids_json TEXT,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS relevance_judgments (
 run_id TEXT NOT NULL REFERENCES retrieval_runs(run_id) ON DELETE CASCADE,
 paper_id TEXT NOT NULL REFERENCES papers(paper_id),
 assessor TEXT NOT NULL,
 grade INTEGER NOT NULL CHECK(grade BETWEEN 0 AND 3),
 judged_at TEXT NOT NULL,
 PRIMARY KEY(run_id,paper_id,assessor)
);
CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(publication_year);
CREATE INDEX IF NOT EXISTS idx_paper_tags_tag_state ON paper_tags(tag_id,review_state,paper_id);
CREATE INDEX IF NOT EXISTS idx_chunks_paper_page ON chunks(paper_id,page_start);
CREATE INDEX IF NOT EXISTS idx_source_records_paper ON source_records(paper_id);
CREATE INDEX IF NOT EXISTS idx_relations_predicate ON concept_relations(predicate,subject_concept,object_concept);
-- FTS5 is intentionally created during actual migration after tokenizer/field policy is tested.
