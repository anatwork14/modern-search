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
    from collections import defaultdict

    aliases_by_tag: dict[str, list[str]] = defaultdict(list)
    for r in connection.execute("SELECT tag_id, alias FROM tag_aliases ORDER BY tag_id, alias_normalized, alias"):
        aliases_by_tag[r["tag_id"]].append(r["alias"])

    tags = []
    for row in connection.execute("SELECT tag_id, namespace, label FROM tags WHERE active = 1 ORDER BY tag_id"):
        tid = row["tag_id"]
        tags.append({
            "tag_id": tid,
            "namespace": row["namespace"],
            "label": row["label"],
            "aliases": aliases_by_tag.get(tid, []),
        })
    return tags


def export_papers(connection: sqlite3.Connection) -> list[dict]:
    """Export papers and their typed tag assertions for the retrieval service."""
    from collections import defaultdict
    import json

    tags_by_paper: dict[str, list[dict]] = defaultdict(list)
    for r in connection.execute("SELECT paper_id, tag_id, review_state, role FROM paper_tags ORDER BY paper_id, tag_id, role"):
        tags_by_paper[r["paper_id"]].append({
            "tag_id": r["tag_id"],
            "review_state": r["review_state"],
            "role": r["role"],
        })

    venue_by_paper: dict[str, list[dict]] = defaultdict(list)
    for r in connection.execute(
        "SELECT paper_id, venue_type, core_rank, sjr_quartile, ranking_system, ranking_year, "
        "ranking_category, ranking_source_url, publication_evidence_url "
        "FROM venue_evidence ORDER BY paper_id, source_record_id"
    ):
        d = dict(r)
        d["source_asserted"] = True
        pid = d.pop("paper_id")
        venue_by_paper[pid].append(d)

    idents_by_paper: dict[str, list[str]] = defaultdict(list)
    for r in connection.execute("SELECT paper_id, normalized_value FROM paper_identifiers ORDER BY paper_id, normalized_value"):
        idents_by_paper[r["paper_id"]].append(r["normalized_value"])

    ident_records_by_paper: dict[str, list[dict]] = defaultdict(list)
    for r in connection.execute("SELECT paper_id, kind, normalized_value AS value FROM paper_identifiers ORDER BY paper_id, kind, normalized_value"):
        ident_records_by_paper[r["paper_id"]].append({
            "kind": r["kind"],
            "value": r["value"],
        })

    papers = []
    rows = connection.execute(
        "SELECT paper_id, title, abstract, authors_json, publication_year, doi, source_url, "
        "review_state, eligibility_state, pdf_state, venue_name FROM papers ORDER BY paper_id"
    )

    for row in rows:
        pid = row["paper_id"]
        papers.append({
            "paper_id": pid,
            "title": row["title"],
            "abstract": row["abstract"],
            "authors": json.loads(row["authors_json"]),
            "year": row["publication_year"],
            "doi": row["doi"],
            "source_url": row["source_url"],
            "review_state": row["review_state"],
            "eligibility": row["eligibility_state"],
            "pdf_state": row["pdf_state"],
            "tags": tags_by_paper.get(pid, []),
            "venue": row["venue_name"],
            "venue_evidence": venue_by_paper.get(pid, []),
            "identifiers": idents_by_paper.get(pid, []),
            "identifier_records": ident_records_by_paper.get(pid, []),
        })
    return papers



__all__ = ["connect", "migrate", "export_papers", "export_tags"]
