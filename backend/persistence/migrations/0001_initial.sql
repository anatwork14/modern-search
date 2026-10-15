CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE papers (
    paper_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT,
    authors_json TEXT NOT NULL DEFAULT '[]',
    publication_year INTEGER,
    venue_name TEXT,
    doi TEXT,
    source_url TEXT,
    eligibility_state TEXT NOT NULL DEFAULT 'unknown'
        CHECK (eligibility_state IN ('unknown','exploratory','verified-qualified','verified-not-qualified')),
    review_state TEXT NOT NULL DEFAULT 'discovered'
        CHECK (review_state IN ('discovered','abstract-screened','fulltext-indexed','manually-verified','experiment-reproduced')),
    pdf_state TEXT NOT NULL DEFAULT 'REMOTE_ONLY'
        CHECK (pdf_state IN ('REMOTE_ONLY','UNAVAILABLE','VERIFIED_LOCAL')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE source_records (
    source_record_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_revision TEXT NOT NULL,
    record_kind TEXT NOT NULL CHECK (record_kind IN ('paper','tag','paper_tag')),
    provider_record_id TEXT NOT NULL,
    paper_id TEXT REFERENCES papers(paper_id) ON DELETE SET NULL,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    UNIQUE(source_id, source_revision, record_kind, provider_record_id)
);
CREATE INDEX idx_source_records_paper ON source_records(paper_id);

CREATE TABLE paper_identifiers (
    paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('doi','arxiv','corpus_id','openalex','publisher_url')),
    normalized_value TEXT NOT NULL,
    source_record_id TEXT REFERENCES source_records(source_record_id),
    PRIMARY KEY(kind, normalized_value),
    UNIQUE(paper_id, kind, normalized_value)
);

CREATE TABLE tags (
    tag_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    namespace TEXT NOT NULL,
    subgroup TEXT,
    label TEXT NOT NULL,
    description TEXT,
    taxonomy_revision TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
);
CREATE TABLE tag_aliases (
    alias_normalized TEXT NOT NULL,
    alias TEXT NOT NULL,
    tag_id TEXT NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
    UNIQUE(alias_normalized, tag_id)
);
CREATE INDEX idx_tag_aliases_normalized ON tag_aliases(alias_normalized);

CREATE TABLE paper_tags (
    paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
    tag_id TEXT NOT NULL REFERENCES tags(tag_id),
    role TEXT NOT NULL DEFAULT 'candidate',
    asserted_from TEXT NOT NULL DEFAULT 'metadata',
    review_state TEXT NOT NULL DEFAULT 'needs-manual-review'
        CHECK (review_state IN ('needs-manual-review','verified','rejected')),
    confidence REAL CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    evidence TEXT,
    source_record_id TEXT REFERENCES source_records(source_record_id),
    PRIMARY KEY(paper_id, tag_id, role, asserted_from)
);
CREATE INDEX idx_paper_tags_tag_state ON paper_tags(tag_id, review_state, paper_id);

CREATE TABLE venue_evidence (
    paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
    venue_type TEXT,
    core_rank TEXT,
    sjr_quartile TEXT,
    ranking_system TEXT,
    ranking_year INTEGER,
    ranking_category TEXT,
    ranking_source_url TEXT,
    publication_evidence_url TEXT,
    source_record_id TEXT REFERENCES source_records(source_record_id),
    PRIMARY KEY(paper_id, source_record_id)
);

CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    remote_url TEXT,
    local_path TEXT,
    sha256 TEXT,
    byte_size INTEGER,
    state TEXT NOT NULL DEFAULT 'REMOTE_ONLY'
        CHECK (state IN ('REMOTE_ONLY','DOWNLOADED_UNVERIFIED','VERIFIED_LOCAL','INVALID','UNAVAILABLE')),
    verified_at TEXT,
    source_record_id TEXT REFERENCES source_records(source_record_id)
);

CREATE VIRTUAL TABLE papers_fts USING fts5(
    paper_id UNINDEXED, title, abstract, venue_name,
    content='papers', content_rowid='rowid', tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER papers_fts_insert AFTER INSERT ON papers BEGIN
    INSERT INTO papers_fts(rowid, paper_id, title, abstract, venue_name)
    VALUES (new.rowid, new.paper_id, new.title, new.abstract, new.venue_name);
END;
CREATE TRIGGER papers_fts_delete AFTER DELETE ON papers BEGIN
    INSERT INTO papers_fts(papers_fts, rowid, paper_id, title, abstract, venue_name)
    VALUES ('delete', old.rowid, old.paper_id, old.title, old.abstract, old.venue_name);
END;
CREATE TRIGGER papers_fts_update AFTER UPDATE OF title, abstract, venue_name ON papers BEGIN
    INSERT INTO papers_fts(papers_fts, rowid, paper_id, title, abstract, venue_name)
    VALUES ('delete', old.rowid, old.paper_id, old.title, old.abstract, old.venue_name);
    INSERT INTO papers_fts(rowid, paper_id, title, abstract, venue_name)
    VALUES (new.rowid, new.paper_id, new.title, new.abstract, new.venue_name);
END;
