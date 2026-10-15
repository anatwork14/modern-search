"""SQLite persistence for local-first paper search."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_MIGRATIONS = Path(__file__).with_name("migrations")


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with foreign keys and deterministic row access."""
    path = str(path)
    if path != ":memory:":
        Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def migrate(connection: sqlite3.Connection) -> int:
    """Apply pending forward-only migrations in individual transactions."""
    connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    connection.commit()
    applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
    files = sorted(_MIGRATIONS.glob("[0-9][0-9][0-9][0-9]_*.sql"))
    versions = [int(file.name[:4]) for file in files]
    if len(versions) != len(set(versions)):
        raise RuntimeError("duplicate migration version in application bundle")
    latest = max(versions, default=0)
    if applied and max(applied) > latest:
        raise RuntimeError(f"database schema version {max(applied)} is newer than this application ({latest})")
    for file in files:
        version = int(file.name[:4])
        if version in applied:
            continue
        script = file.read_text(encoding="utf-8")
        try:
            connection.executescript("BEGIN IMMEDIATE;\n" + script + "\nINSERT INTO schema_migrations(version, applied_at) VALUES (" + str(version) + ", '" + datetime.now(timezone.utc).isoformat() + "');\nCOMMIT;")
        except Exception:
            connection.rollback()
            raise
    return latest


def export_tags(connection: sqlite3.Connection) -> list[dict]:
    """Return active canonical tags using the agreed retrieval interface."""
    tags = []
    for row in connection.execute("SELECT tag_id, namespace, label FROM tags WHERE active = 1 ORDER BY tag_id"):
        aliases = [r[0] for r in connection.execute("SELECT alias FROM tag_aliases WHERE tag_id = ? ORDER BY alias_normalized, alias", (row["tag_id"],))]
        tags.append({"tag_id": row["tag_id"], "namespace": row["namespace"], "label": row["label"], "aliases": aliases})
    return tags


def export_papers(connection: sqlite3.Connection) -> list[dict]:
    """Export papers and their typed tag assertions for the retrieval service."""
    papers = []
    rows = connection.execute(
        "SELECT paper_id, title, abstract, authors_json, publication_year, doi, source_url, "
        "review_state, eligibility_state, pdf_state, venue_name FROM papers ORDER BY paper_id"
    )
    import json

    for row in rows:
        tags = [dict(r) for r in connection.execute(
            "SELECT tag_id, review_state, role FROM paper_tags WHERE paper_id = ? ORDER BY tag_id, role",
            (row["paper_id"],),
        )]
        papers.append({
            "paper_id": row["paper_id"], "title": row["title"], "abstract": row["abstract"],
            "authors": json.loads(row["authors_json"]), "year": row["publication_year"],
            "doi": row["doi"], "source_url": row["source_url"],
            "review_state": row["review_state"], "eligibility": row["eligibility_state"],
            "pdf_state": row["pdf_state"], "tags": tags,
            "venue": row["venue_name"],
            "venue_evidence": [{**dict(r), "source_asserted": True} for r in connection.execute(
                "SELECT venue_type,core_rank,sjr_quartile,ranking_system,ranking_year,ranking_category,ranking_source_url,publication_evidence_url FROM venue_evidence WHERE paper_id=? ORDER BY source_record_id", (row["paper_id"],))],
            "identifiers": [r[0] for r in connection.execute(
                "SELECT normalized_value FROM paper_identifiers WHERE paper_id=? ORDER BY normalized_value", (row["paper_id"],))],
            "identifier_records": [dict(r) for r in connection.execute(
                "SELECT kind,normalized_value AS value FROM paper_identifiers WHERE paper_id=? ORDER BY kind,normalized_value", (row["paper_id"],))],
        })
    return papers


__all__ = ["connect", "migrate", "export_papers", "export_tags"]
