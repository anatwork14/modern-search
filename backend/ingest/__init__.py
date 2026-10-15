"""Transactional import of source-attributed catalog snapshots."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

_PAPER_REVIEW = {"discovered", "abstract-screened", "fulltext-indexed", "manually-verified", "experiment-reproduced"}
_TAG_REVIEW = {"needs-manual-review", "verified", "rejected"}
_ROLES = {"primary_method", "supporting_method", "application", "benchmark", "objective", "negative_result", "survey_coverage", "mention_only", "candidate"}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _doi(value: Any) -> str | None:
    if not value or not str(value).strip():
        return None
    normalized = str(value).strip()
    normalized = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", normalized, flags=re.I)
    normalized = normalized.strip().casefold()
    return normalized or None


def _source_record(connection: sqlite3.Connection, source_id: str, revision: str, kind: str, record_id: str, paper_id: str | None, payload: dict, now: str) -> str:
    payload_json = _json(payload)
    record_id_hash = _hash(f"{source_id}\0{revision}\0{kind}\0{record_id}")
    connection.execute(
        "INSERT OR IGNORE INTO source_records(source_record_id,source_id,source_revision,record_kind,provider_record_id,paper_id,payload_json,payload_sha256,imported_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (record_id_hash, source_id, revision, kind, record_id, paper_id, payload_json, _hash(payload_json), now),
    )
    existing = connection.execute("SELECT source_record_id,payload_sha256 FROM source_records WHERE source_id=? AND source_revision=? AND record_kind=? AND provider_record_id=?", (source_id, revision, kind, record_id)).fetchone()
    if existing["payload_sha256"] != _hash(payload_json):
        raise ValueError(f"conflicting {kind} rows for source key {record_id!r} in one revision")
    return existing["source_record_id"]


def import_catalog(connection: sqlite3.Connection, catalog: dict, source_id: str, source_revision: str) -> dict:
    """Validate and transactionally import {tags, papers, paper_tags}.

    Source snapshots are immutable by source ID/revision. Canonical paper IDs are
    retained; DOI collisions across IDs abort the entire import.
    """
    if not source_id or not source_revision:
        raise ValueError("source_id and source_revision are required")
    if not isinstance(catalog, dict):
        raise ValueError("catalog must be an object")
    tags = catalog.get("tags", [])
    papers = catalog.get("papers", [])
    edges = catalog.get("paper_tags", [])
    for field, rows in (("tags", tags), ("papers", papers), ("paper_tags", edges)):
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError(f"{field} must be an array of objects")

    tag_by_id: dict[str, dict] = {}
    for tag in tags:
        tag_id = str(tag.get("tag_id", "")).strip()
        namespace = str(tag.get("namespace", "")).strip()
        if not tag_id or not namespace or "/" not in tag_id or tag_id.split("/", 1)[0] != namespace:
            raise ValueError(f"invalid canonical tag namespace/id: {tag_id!r}")
        if tag_id in tag_by_id and _json(tag_by_id[tag_id]) != _json(tag):
            raise ValueError(f"conflicting duplicate canonical tag {tag_id!r}")
        tag_by_id[tag_id] = tag

    paper_by_id: dict[str, dict] = {}
    for paper in papers:
        paper_id = str(paper.get("paper_id", "")).strip()
        if not paper_id or not str(paper.get("title", "")).strip():
            raise ValueError("each paper requires a stable paper_id and title")
        if paper_id in paper_by_id and _json(paper_by_id[paper_id]) != _json(paper):
            raise ValueError(f"conflicting duplicate paper_id {paper_id!r}")
        paper_by_id[paper_id] = paper
    for edge in edges:
        if edge.get("paper_id") not in paper_by_id:
            raise ValueError(f"paper_tag references unknown paper {edge.get('paper_id')!r}")
        if edge.get("tag_id") not in tag_by_id:
            raise ValueError(f"paper_tag references unknown tag {edge.get('tag_id')!r}")
    doi_owners: dict[str, str] = {}
    for paper_id, paper in paper_by_id.items():
        doi = _doi(paper.get("doi"))
        if doi and doi in doi_owners and doi_owners[doi] != paper_id:
            raise ValueError(f"DOI collision across paper IDs: {doi}")
        if doi:
            doi_owners[doi] = paper_id

    now = datetime.now(timezone.utc).isoformat()
    inserted = {"papers": 0, "tags": 0, "paper_tags": 0, "source_records": 0}
    updated = {"papers": 0, "tags": 0}
    connection.execute("BEGIN IMMEDIATE")
    try:
        # Retire assertions and canonical tags omitted from a newer snapshot of
        # this source while leaving immutable source_records available for audit.
        old_edge_ids = [row[0] for row in connection.execute(
            "SELECT source_record_id FROM source_records WHERE source_id=? AND record_kind='paper_tag' AND source_revision<>?",
            (source_id, source_revision),
        )]
        if old_edge_ids:
            connection.executemany("DELETE FROM paper_tags WHERE source_record_id=?", ((record_id,) for record_id in old_edge_ids))
        if tag_by_id:
            placeholders = ",".join("?" for _ in tag_by_id)
            connection.execute(
                f"UPDATE tags SET active=0 WHERE source_id=? AND tag_id NOT IN ({placeholders})",
                (source_id, *sorted(tag_by_id)),
            )
        else:
            connection.execute("UPDATE tags SET active=0 WHERE source_id=?", (source_id,))

        for tag_id in sorted(tag_by_id):
            tag = tag_by_id[tag_id]
            src = _source_record(connection, source_id, source_revision, "tag", tag_id, None, tag, now)
            exists = connection.execute("SELECT 1 FROM tags WHERE tag_id=?", (tag_id,)).fetchone()
            connection.execute(
                "INSERT INTO tags(tag_id,source_id,namespace,subgroup,label,description,taxonomy_revision,active) VALUES(?,?,?,?,?,?,?,?) "
                "ON CONFLICT(tag_id) DO UPDATE SET source_id=excluded.source_id,namespace=excluded.namespace,subgroup=excluded.subgroup,label=excluded.label,description=excluded.description,taxonomy_revision=excluded.taxonomy_revision,active=excluded.active",
                (tag_id, source_id, tag["namespace"], tag.get("subgroup"), tag.get("label") or tag_id.rsplit("/", 1)[-1], tag.get("description"), source_revision, int(tag.get("active", True))),
            )
            inserted["tags"] += not bool(exists)
            updated["tags"] += bool(exists)
            connection.execute("DELETE FROM tag_aliases WHERE tag_id=?", (tag_id,))
            for alias in tag.get("aliases", []) or []:
                alias = str(alias).strip()
                if alias:
                    connection.execute("INSERT OR IGNORE INTO tag_aliases(alias_normalized,alias,tag_id) VALUES(?,?,?)", (alias.casefold(), alias, tag_id))

        for paper_id in sorted(paper_by_id):
            paper = paper_by_id[paper_id]
            exists = connection.execute("SELECT 1 FROM papers WHERE paper_id=?", (paper_id,)).fetchone()
            doi = _doi(paper.get("doi"))
            review = paper.get("review_state", "discovered")
            if review not in _PAPER_REVIEW:
                review = "discovered"
            eligibility = paper.get("eligibility", paper.get("eligibility_state", "unknown"))
            if eligibility not in {"unknown", "exploratory", "verified-qualified", "verified-not-qualified"}:
                eligibility = "unknown"
            # Catalog rows can identify remote links, but only the local PDF
            # verification pipeline may promote bytes to VERIFIED_LOCAL.
            pdf_state = "REMOTE_ONLY" if paper.get("pdf_url") else "UNAVAILABLE"
            authors = paper.get("authors") or []
            if isinstance(authors, str):
                authors = [item.strip() for item in authors.split(";") if item.strip()]
            connection.execute(
                "INSERT INTO papers(paper_id,title,abstract,authors_json,publication_year,venue_name,doi,source_url,eligibility_state,review_state,pdf_state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(paper_id) DO UPDATE SET title=excluded.title,abstract=excluded.abstract,authors_json=excluded.authors_json,publication_year=excluded.publication_year,venue_name=excluded.venue_name,doi=excluded.doi,source_url=excluded.source_url,eligibility_state=excluded.eligibility_state,review_state=excluded.review_state,pdf_state=CASE WHEN papers.pdf_state='VERIFIED_LOCAL' THEN papers.pdf_state ELSE excluded.pdf_state END,updated_at=excluded.updated_at",
                (paper_id, str(paper["title"]).strip(), paper.get("abstract") or None, _json(authors), paper.get("year"), paper.get("venue"), doi, paper.get("source_url"), eligibility, review, pdf_state, now, now),
            )
            inserted["papers"] += not bool(exists)
            updated["papers"] += bool(exists)
            src = _source_record(connection, source_id, source_revision, "paper", paper_id, paper_id, paper, now)
            connection.execute(
                "DELETE FROM paper_identifiers WHERE paper_id=? AND kind='doi' AND source_record_id IN (SELECT source_record_id FROM source_records WHERE source_id=?)",
                (paper_id, source_id),
            )
            if doi:
                connection.execute("INSERT INTO paper_identifiers(paper_id,kind,normalized_value,source_record_id) VALUES(?,?,?,?) ON CONFLICT(kind,normalized_value) DO UPDATE SET source_record_id=excluded.source_record_id", (paper_id, "doi", doi, src))
            if paper.get("venue_evidence"):
                ev = paper["venue_evidence"]
                connection.execute("INSERT OR IGNORE INTO venue_evidence(paper_id,venue_type,core_rank,sjr_quartile,ranking_system,ranking_year,ranking_category,ranking_source_url,publication_evidence_url,source_record_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (paper_id, ev.get("venue_type"), ev.get("core_rank"), ev.get("sjr_quartile"), ev.get("ranking_system"), ev.get("ranking_year"), ev.get("ranking_category"), ev.get("ranking_source_url"), ev.get("publication_evidence_url"), src))
            if paper.get("pdf_url"):
                artifact_id = _hash(f"pdf\0{paper_id}\0{paper['pdf_url']}")
                connection.execute("INSERT OR IGNORE INTO artifacts(artifact_id,paper_id,kind,remote_url,state,source_record_id) VALUES(?,?,?,?,?,?)", (artifact_id, paper_id, "pdf", paper["pdf_url"], "REMOTE_ONLY", src))

        for edge in edges:
            paper_id, tag_id = edge["paper_id"], edge["tag_id"]
            role = edge.get("role", "candidate")
            if role not in _ROLES:
                role = "candidate"
            asserted_from = edge.get("asserted_from", "metadata")
            review_state = edge.get("review_state", "needs-manual-review")
            if review_state not in _TAG_REVIEW:
                review_state = "needs-manual-review"
            key = f"{paper_id}\0{tag_id}\0{role}\0{asserted_from}"
            src = _source_record(connection, source_id, source_revision, "paper_tag", _hash(key), paper_id, edge, now)
            before = connection.total_changes
            connection.execute("INSERT OR IGNORE INTO paper_tags(paper_id,tag_id,role,asserted_from,review_state,confidence,evidence,source_record_id) VALUES(?,?,?,?,?,?,?,?)", (paper_id, tag_id, role, asserted_from, review_state, edge.get("confidence"), edge.get("evidence"), src))
            inserted["paper_tags"] += connection.total_changes > before

        inserted["source_records"] = connection.execute("SELECT count(*) FROM source_records WHERE source_id=? AND source_revision=?", (source_id, source_revision)).fetchone()[0]
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {"source_id": source_id, "source_revision": source_revision, "imported": inserted, "updated": updated, "total": {"papers": len(paper_by_id), "tags": len(tag_by_id), "paper_tags": len(edges)}, "reconciliation": {"doi_collisions": 0}}


__all__ = ["import_catalog"]
