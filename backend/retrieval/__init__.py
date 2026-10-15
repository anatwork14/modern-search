"""Deterministic, offline-first lexical retrieval and hard-filter evaluation."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import sqlite3
from typing import Any, Iterable
from urllib.parse import urlsplit

_PAPER_STATES = {
    "discovered", "abstract-screened", "fulltext-indexed",
    "manually-verified", "experiment-reproduced",
}
_ELIGIBILITY = {
    "unknown", "exploratory", "verified-qualified", "verified-not-qualified",
}
_TAG_STATES = {"verified", "needs-manual-review", "rejected"}
_FACET_STATES = {"verified", "needs-manual-review"}
_REQUEST_FIELDS = {"query", "mode", "scope", "limit", "cursor", "hard_filters"}
_HARD_FILTER_FIELDS = {"eligibility", "review_state", "exclude_paper_ids", "facets"}
_FACET_FIELDS = {"namespace", "operator", "tags", "review_state"}
_DOI = re.compile(r"(?i)(?:https?://(?:dx\.)?doi\.org/|doi:\s*)?(10\.\d{4,9}/[^\s\"<>]+)")
_ARXIV = re.compile(r"(?i)(?:arxiv:\s*)?((?:\d{4}\.\d{4,5})(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?")
_WORD = re.compile(r"[\w]+", re.UNICODE)


def _object(value: Any, name: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _keys(value: dict, allowed: set[str], name: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"Unsupported {name} field: {sorted(unknown)[0]}")


def _unique_strings(value: Any, name: str, allowed: set[str] | None = None) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be an array of strings")
    if len(set(value)) != len(value):
        raise ValueError(f"{name} must not contain duplicates")
    if allowed is not None and set(value) - allowed:
        raise ValueError(f"Invalid value in {name}")
    return value


def _validate(request: Any) -> tuple[str, str, int, str | None, dict]:
    request = _object(request, "request")
    _keys(request, _REQUEST_FIELDS, "request")
    query = request.get("query", "")
    if not isinstance(query, str) or len(query) > 10000:
        raise ValueError("query must be a string of at most 10000 characters")
    mode = request.get("mode", "STRICT")
    if mode not in {"STRICT", "BROAD"}:
        raise ValueError("mode must be STRICT or BROAD")
    scope = request.get("scope", "LOCAL_ONLY")
    if scope != "LOCAL_ONLY":
        raise ValueError("scope must be LOCAL_ONLY")
    limit = request.get("limit", 20)
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer from 1 to 100")
    cursor = request.get("cursor")
    if cursor is not None and not isinstance(cursor, str):
        raise ValueError("cursor must be a string or null")
    filters = _object(request.get("hard_filters", {}), "hard_filters")
    _keys(filters, _HARD_FILTER_FIELDS, "hard_filters")
    if "eligibility" in filters:
        _unique_strings(filters["eligibility"], "eligibility", _ELIGIBILITY)
    if "review_state" in filters:
        _unique_strings(filters["review_state"], "review_state", _PAPER_STATES)
    if "exclude_paper_ids" in filters:
        _unique_strings(filters["exclude_paper_ids"], "exclude_paper_ids")
    facets = filters.get("facets", [])
    if not isinstance(facets, list):
        raise ValueError("facets must be an array")
    for facet in facets:
        _object(facet, "facet")
        _keys(facet, _FACET_FIELDS, "facet")
        if not isinstance(facet.get("namespace"), str) or not facet["namespace"]:
            raise ValueError("facet namespace must be a non-empty string")
        if facet.get("operator") not in {"ANY", "ALL", "NOT"}:
            raise ValueError("facet operator must be ANY, ALL or NOT")
        tags = _unique_strings(facet.get("tags"), "facet tags")
        if not tags or any(not tag for tag in tags):
            raise ValueError("facet tags must be non-empty strings")
        if "review_state" in facet and facet["review_state"] not in _FACET_STATES:
            raise ValueError("Invalid facet review_state")
    return query, mode, limit, cursor, filters


def _tag_dictionary(tags: Iterable[dict]) -> tuple[dict[str, dict], dict[str, str]]:
    by_id: dict[str, dict] = {}
    names: dict[str, str] = {}
    for tag in tags:
        if not isinstance(tag, dict) or not isinstance(tag.get("tag_id"), str):
            raise ValueError("Invalid tag dictionary entry")
        tag_id = tag["tag_id"]
        if tag_id in by_id:
            raise ValueError("Duplicate tag_id in dictionary")
        by_id[tag_id] = tag
        aliases = tag.get("aliases", [])
        if not isinstance(aliases, list) or any(not isinstance(alias, str) for alias in aliases):
            raise ValueError("Tag aliases must be an array of strings")
        candidates = [tag_id, tag.get("label", ""), *aliases]
        for candidate in candidates:
            if not isinstance(candidate, str) or not candidate:
                continue
            key = candidate.casefold()
            previous = names.get(key)
            if previous is not None and previous != tag_id:
                # Keep collisions ambiguous so that neither tag is silently selected.
                names[key] = ""
            elif key not in names:
                names[key] = tag_id
    return by_id, names


def _resolve_facets(filters: dict, tag_by_id: dict, names: dict) -> list[dict]:
    resolved = []
    for facet in filters.get("facets", []):
        ids = []
        for raw in facet["tags"]:
            canonical = raw if raw in tag_by_id else names.get(raw.casefold())
            if not canonical or canonical not in tag_by_id:
                raise ValueError(f"Unknown or ambiguous tag: {raw}")
            if tag_by_id[canonical].get("namespace") != facet["namespace"]:
                raise ValueError(f"Tag {raw} is outside namespace {facet['namespace']}")
            ids.append(canonical)
        resolved.append({**facet, "tags": ids})
    return resolved


def _safe_source_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else None


def _normalize_doi(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DOI.fullmatch(value.strip())
    return match.group(1).rstrip(".,;)").casefold() if match else None


def _normalize_arxiv(value: str) -> str | None:
    match = _ARXIV.fullmatch(value.strip())
    return match.group(1).casefold() if match else None


def _query_parts(query: str) -> tuple[str | None, str | None, list[str], list[str]]:
    doi_match = _DOI.search(query.strip())
    arxiv_match = _ARXIV.search(query.strip())
    doi = doi_match.group(1).rstrip(".,;)").casefold() if doi_match else None
    arxiv = arxiv_match.group(1).casefold() if arxiv_match else None
    phrases = [" ".join(_WORD.findall(item)) for item in re.findall(r'"([^"\n]+)"', query)]
    terms = _WORD.findall(re.sub(r'"[^"\n]+"', " ", query))
    # DOI/arXiv punctuation is not meaningful to FTS. Their direct route handles identity.
    terms = [word for word in terms if not (doi and word.casefold() in doi.split("/"))]
    return doi, arxiv, [p for p in phrases if p], terms


def _fts_match(phrases: list[str], terms: list[str]) -> str:
    pieces = [f'"{phrase.replace(chr(34), chr(34)*2)}"' for phrase in phrases]
    pieces.extend(f'"{term.replace(chr(34), chr(34)*2)}"' for term in terms)
    return " AND ".join(pieces)


def _build_fts(papers: list[dict], tag_by_id: dict[str, dict]) -> tuple[sqlite3.Connection, dict[str, dict]]:
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE VIRTUAL TABLE paper_fts USING fts5(paper_id UNINDEXED, title, abstract, authors, tags)")
    valid: dict[str, dict] = {}
    for paper in papers:
        if not isinstance(paper, dict) or not isinstance(paper.get("paper_id"), str):
            raise ValueError("Invalid paper dictionary entry")
        paper_id = paper["paper_id"]
        if paper_id in valid:
            raise ValueError("Duplicate paper_id")
        valid[paper_id] = paper
        tag_rows = paper.get("tags", [])
        labels = " ".join(
            " ".join([str(tag_by_id[t.get("tag_id")].get("label", "")),
                       *tag_by_id[t.get("tag_id")].get("aliases", [])])
            for t in tag_rows if isinstance(t, dict) and t.get("tag_id") in tag_by_id
        )
        values = (
            paper_id,
            str(paper.get("title") or ""),
            str(paper.get("abstract") or ""),
            " ".join(str(a) for a in paper.get("authors", []) if isinstance(a, str)),
            labels,
        )
        connection.execute("INSERT INTO paper_fts VALUES (?, ?, ?, ?, ?)", values)
    return connection, valid


def _paper_filter(paper: dict, filters: dict, facets: list[dict]) -> bool:
    eligibilities = filters.get("eligibility")
    if eligibilities is None:
        eligibilities = ["verified-qualified"]
    elif not eligibilities:
        # An empty constraint does not make exploratory/unknown records eligible.
        eligibilities = ["verified-qualified"]
    if paper.get("eligibility", "unknown") not in eligibilities:
        return False
    states = filters.get("review_state")
    if states is not None and paper.get("review_state", "discovered") not in states:
        return False
    if paper["paper_id"] in filters.get("exclude_paper_ids", []):
        return False
    for facet in facets:
        selected = set(facet["tags"])
        actual: set[str] = set()
        for tag in paper.get("tags", []):
            if not isinstance(tag, dict) or tag.get("tag_id") not in selected:
                continue
            if tag.get("review_state") not in _TAG_STATES:
                continue
            if facet.get("review_state") and tag.get("review_state") != facet["review_state"]:
                continue
            actual.add(tag["tag_id"])
        op = facet["operator"]
        if (op == "ANY" and not actual) or (op == "ALL" and actual != selected) or (op == "NOT" and actual):
            return False
    return True


def _fingerprint(papers: dict, tags: list[dict]) -> str:
    content = {"papers": papers, "tags": tags}
    payload = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _request_fingerprint(request: dict) -> str:
    value = {k: v for k, v in request.items() if k != "cursor"}
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _encode_cursor(offset: int, query_hash: str, index_hash: str) -> str:
    raw = json.dumps({"offset": offset, "query": query_hash, "index": index_hash}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str | None, query_hash: str, index_hash: str) -> int:
    if cursor is None:
        return 0
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        data = json.loads(raw)
        offset = data["offset"]
        if type(offset) is not int or offset < 0 or data["query"] != query_hash or data["index"] != index_hash:
            raise ValueError
        return offset
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid or stale cursor") from error


def _dense_ranks(dense: Any, warnings: list[str]) -> tuple[dict[str, int], str]:
    if dense is None:
        return {}, "unavailable"
    try:
        if isinstance(dense, dict):
            values = dense.get("results", dense.get("paper_ids", []))
        else:
            values = dense
        if not isinstance(values, (list, tuple)):
            raise ValueError
        ranks = {}
        for item in values:
            paper_id = item if isinstance(item, str) else item.get("paper_id") if isinstance(item, dict) else None
            if isinstance(paper_id, str) and paper_id not in ranks:
                ranks[paper_id] = len(ranks) + 1
        return ranks, "ready"
    except Exception:
        warnings.append("Dense retrieval was unavailable; lexical results were used")
        return {}, "unavailable"


def search(papers: Iterable[dict], tags: Iterable[dict], request: dict, dense: Any = None) -> dict:
    """Search an exported paper/tag catalog and return MVP wire response data.

    The catalog is treated as untrusted input. All SQL values are bound parameters;
    FTS expressions are built only from individually quoted literal tokens.
    """
    query, mode, limit, cursor, filters = _validate(request)
    papers = list(papers)
    tags = list(tags)
    tag_by_id, names = _tag_dictionary(tags)
    facets = _resolve_facets(filters, tag_by_id, names)
    connection, by_id = _build_fts(papers, tag_by_id)
    try:
        index_hash = _fingerprint(by_id, tags)
        query_hash = _request_fingerprint(request)
        offset = _decode_cursor(cursor, query_hash, index_hash)
        doi, arxiv, phrases, terms = _query_parts(query)
        fts = _fts_match(phrases, terms)
        lexical: dict[str, float] = {}
        if fts:
            # BM25 returns lower values for better matches. The SQL contains no caller syntax.
            for paper_id, score in connection.execute(
                "SELECT paper_id, bm25(paper_fts, 0.0, 5.0, 1.0, 0.5, 0.5) "
                "FROM paper_fts WHERE paper_fts MATCH ? ORDER BY bm25(paper_fts, 0.0, 5.0, 1.0, 0.5, 0.5), paper_id",
                (fts,),
            ):
                lexical[paper_id] = float(score)
        warnings: list[str] = []
        dense_rank, dense_status = _dense_ranks(dense, warnings)
        candidate_ids = set(lexical) | set(dense_rank)
        direct_ids = set()
        if doi:
            direct_ids = {pid for pid, paper in by_id.items() if _normalize_doi(paper.get("doi")) == doi}
            candidate_ids.update(direct_ids)
        if arxiv:
            direct_ids.update(
                pid for pid, paper in by_id.items()
                if any(_normalize_arxiv(identifier) == arxiv for identifier in paper.get("identifiers", []))
                or _normalize_arxiv(str(paper.get("source_url") or "").rsplit("/", 1)[-1]) == arxiv
            )
            candidate_ids.update(direct_ids)
        if not query.strip() or not (fts or doi or arxiv):
            candidate_ids = set(by_id)

        eligible_ids = {pid for pid, paper in by_id.items() if _paper_filter(paper, filters, facets)}
        candidate_ids &= eligible_ids
        # Exact identifiers and phrase hits are direct evidence routes; dense failures never abort.
        ordered = sorted(candidate_ids, key=lambda pid: (
            0 if pid in direct_ids else 1,
            0 if pid in lexical else 1,
            lexical.get(pid, 0.0),
            -1.0 / (60 + dense_rank[pid]) if pid in dense_rank else 0.0,
            pid,
        ))
        # Reciprocal-rank fusion combines route order, with lexical score as a stable tie break.
        lexical_order = sorted(lexical, key=lambda pid: (lexical[pid], pid))
        lex_rank = {pid: rank for rank, pid in enumerate(lexical_order, 1)}
        if dense_rank:
            ordered.sort(key=lambda pid: (
                -(1 if pid in direct_ids else 0),
                -(1 / (60 + lex_rank[pid]) if pid in lex_rank else 0) -
                (1 / (60 + dense_rank[pid]) if pid in dense_rank else 0),
                lexical.get(pid, 0.0), pid,
            ))
        total = len(ordered)
        result_rows = []
        for pid in ordered[offset:offset + limit]:
            paper = by_id[pid]
            paper_tags = [
                {"tag_id": t.get("tag_id"), "review_state": t.get("review_state", "needs-manual-review"),
                 "role": t.get("role", "candidate")}
                for t in paper.get("tags", []) if isinstance(t, dict)
            ]
            routes = []
            if pid in direct_ids:
                routes.append("EXACT_TERM")
            elif pid in lexical:
                routes.append("EXACT_TERM")
            if pid in dense_rank:
                routes.append("SEMANTIC")
            selected = {tid for facet in facets for tid in facet["tags"]}
            matched_tags = [t for t in paper_tags if t["tag_id"] in selected]
            if any(t["review_state"] == "verified" for t in matched_tags):
                routes.append("TAG_VERIFIED")
            if any(t["review_state"] == "needs-manual-review" for t in matched_tags):
                routes.append("TAG_CANDIDATE")
            if not routes:
                routes.append("FILTER_BROWSE")
            score = 1 / (60 + lex_rank[pid]) if pid in lex_rank else 0.0
            if pid in dense_rank:
                score += 1 / (60 + dense_rank[pid])
            if pid in direct_ids:
                score += 1.0
            result_rows.append({
                "paper_id": pid,
                "title": str(paper.get("title") or ""),
                "abstract": paper.get("abstract"),
                "authors": list(paper.get("authors") or []),
                "year": paper.get("year"),
                "doi": paper.get("doi"),
                "source_url": _safe_source_url(paper.get("source_url")),
                "review_state": paper.get("review_state", "discovered"),
                "eligibility": paper.get("eligibility", "unknown"),
                "tags": paper_tags,
                "pdf_state": paper.get("pdf_state", "UNAVAILABLE"),
                "match_routes": routes,
                "score": float(score),
            })
        next_offset = offset + len(result_rows)
        next_cursor = _encode_cursor(next_offset, query_hash, index_hash) if next_offset < total else None
        return {"results": result_rows, "total": total, "next_cursor": next_cursor,
                "index_version": f"sqlite-fts5-v1:{index_hash[:16]}", "dense_status": dense_status,
                "warnings": warnings}
    finally:
        connection.close()


__all__ = ["search"]
