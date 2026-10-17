"""Private, persistent newline-delimited stdio service. No listening socket."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

MAX_REQUEST_BYTES = 1_048_576


def database_path() -> Path:
    configured = os.environ.get("RESEARCHOS_DB_PATH")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "Library/Application Support/ResearchOS/catalog.sqlite3"



class SessionCache:
    """Reuse paper exports, taxonomy and prepared FTS between queries.

    SQLite PRAGMA data_version detects commits from other connections (including
    catalog imports). File identity detects atomic replacement of the database.
    The index is rebuilt on changes instead of serving a stale catalog.
    """

    def __init__(self):
        self.path = None
        self.identity = None
        self.connection = None
        self.version = None
        self.papers = []
        self.tags = []
        self.prepared = None
        self.dense_key = None
        self.dense = None

    def close(self) -> None:
        if self.prepared is not None:
            self.prepared.close()
        self.prepared = None
        if self.connection is not None:
            self.connection.close()
        self.connection = None
        self.version = None
        self.dense_key = None
        self.dense = None

    def snapshot(self, path: Path):
        from backend.persistence import connect, migrate, export_papers, export_tags
        from backend.retrieval import PreparedSearch

        identity = None
        if path.is_file():
            info = path.stat()
            identity = (info.st_dev, info.st_ino)
        if self.connection is None or self.path != path or identity != self.identity:
            self.close()
            self.path = path
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.connection = connect(path)
            migrate(self.connection)
            info = path.stat()
            self.identity = (info.st_dev, info.st_ino)
        current_version = self.connection.execute("PRAGMA data_version").fetchone()[0]
        if self.prepared is None or current_version != self.version:
            papers, tags = export_papers(self.connection), export_tags(self.connection)
            prepared = PreparedSearch(papers, tags)
            if self.prepared is not None:
                self.prepared.close()
            self.papers, self.tags, self.prepared = papers, tags, prepared
            self.dense_key, self.dense = None, None
            self.version = current_version
        return self.papers, self.tags, self.prepared

    def dense_index(self, path: Path):
        """Recheck the local file and corpus revision; never accept stale vectors."""
        info = path.stat()
        key = (str(path), info.st_size, info.st_mtime_ns, self.prepared.index_hash)
        if self.dense_key != key:
            from backend.vector.index import DenseIndex
            dense = DenseIndex(path, self.papers, self.tags)
            self.dense = dense
            self.dense_key = key
        return self.dense


def handle(request: object, session: SessionCache | None = None) -> dict:
    request_id = request.get("id") if isinstance(request, dict) else None
    envelope = {"version": 1, "id": request_id}
    try:
        if not isinstance(request, dict) or set(request) != {"version", "id", "command", "payload"}:
            raise ValueError("Expected version, id, command and payload")
        if type(request["version"]) is not int or request["version"] != 1:
            raise ValueError("Unsupported protocol version")
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
            raise ValueError("Invalid request ID")
        command = request["command"]
        if command not in ("health", "search", "taxonomy") or not isinstance(request["payload"], dict):
            raise ValueError("Unsupported command or payload")
        if command != "search" and request["payload"]:
            raise ValueError("This command has no payload fields")
        path = database_path()
        prepared = None
        if session is None:
            from backend.persistence import connect, migrate, export_papers, export_tags
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            connection = connect(path)
            try:
                migrate(connection)
                papers, tags = export_papers(connection), export_tags(connection)
            finally:
                connection.close()
        else:
            papers, tags, prepared = session.snapshot(path)
        if command == "health":
            # Show how many papers are actually searchable under each hard
            # eligibility filter. Catalog imports usually start as unverified
            # candidates; reporting only total count makes an empty default
            # verified-only search look like a broken index.
            eligibility_counts = {
                "verified-qualified": 0,
                "verified-not-qualified": 0,
                "unknown": 0,
                "exploratory": 0,
            }
            for paper in papers:
                state = paper.get("eligibility", "unknown")
                if state in eligibility_counts:
                    eligibility_counts[state] += 1
            data = {"status": "ready", "offline": True, "dense_status": "unavailable",
                    "index_version": "sqlite-v1", "paper_count": len(papers),
                    "eligibility_counts": eligibility_counts}
        elif command == "taxonomy":
            data = {"tags": tags}
        else:
            from backend.retrieval import search
            dense = None
            warnings = []
            payload = request["payload"]
            index_path = Path(os.environ.get("RESEARCHOS_INDEX_PATH", str(path.with_suffix(".dense.json"))))
            if payload.get("mode", "STRICT") == "BROAD" and isinstance(payload.get("query", ""), str) and payload.get("query", "").strip():
                if index_path.is_file():
                    try:
                        from backend.vector.index import DenseIndex
                        dense = session.dense_index(index_path) if session is not None else DenseIndex(index_path, papers, tags)
                    except Exception:
                        warnings.append("Dense index is invalid or out of date; lexical search remains available")
                else:
                    warnings.append("No local dense index is installed; lexical search remains available")
            data = search(papers, tags, payload, dense=dense, prepared=prepared)
            data["warnings"].extend(warnings)
            lookup = prepared.by_id if prepared is not None else {paper["paper_id"]: paper for paper in papers}
            for result in data["results"]:
                paper = lookup.get(result["paper_id"])
                if paper:
                    result["venue"] = paper.get("venue")
                    result["venue_evidence"] = paper.get("venue_evidence", [])
        return {**envelope, "ok": True, "data": data}
    except (ValueError, TypeError, KeyError) as error:
        return {**envelope, "ok": False, "error": {"code": "INVALID_REQUEST", "message": str(error)}}
    except Exception:
        # Do not expose private database paths, source records or credentials.
        return {**envelope, "ok": False, "error": {"code": "INTERNAL_ERROR",
                "message": "Local service failed; inspect local setup and database compatibility"}}


def main() -> int:
    """Serve newline-delimited RPC frames until EOF, without opening any port.

    Legacy one-shot callers still work: send one JSON line, close stdin, and
    consume one response. A desktop parent can keep the same child alive for
    many commands. Each frame remains independently validated by handle().
    """
    session = SessionCache()
    while True:
        raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
        if not raw:
            return 0
        try:
            if len(raw) > MAX_REQUEST_BYTES:
                # Drain the remainder of an overlong line before parsing the
                # next request; do not accidentally interpret its tail as RPC.
                while not raw.endswith(b"\n"):
                    raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
                    if not raw or raw.endswith(b"\n"):
                        break
                raise ValueError("Request exceeds maximum size")
            request = json.loads(raw)
            response = handle(request, session=session)
        except (ValueError, UnicodeError):
            response = {"version": 1, "id": None, "ok": False,
                        "error": {"code": "INVALID_REQUEST", "message": "Invalid JSON request or size"}}
        # A persistent stdio worker must flush before the next request arrives.
        print(json.dumps(response, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
