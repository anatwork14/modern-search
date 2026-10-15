"""One request per process stdio bridge. No socket or implicit network access."""
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


def handle(request: object) -> dict:
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
        from backend.persistence import connect, migrate, export_papers, export_tags

        path = database_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        connection = connect(path)
        try:
            migrate(connection)
            papers, tags = export_papers(connection), export_tags(connection)
            if command == "health":
                data = {"status": "ready", "offline": True, "dense_status": "unavailable",
                        "index_version": "sqlite-v1", "paper_count": len(papers)}
            elif command == "taxonomy":
                data = {"tags": tags}
            else:
                from backend.retrieval import search
                data = search(papers, tags, request["payload"])
        finally:
            connection.close()
        return {**envelope, "ok": True, "data": data}
    except (ValueError, TypeError, KeyError) as error:
        return {**envelope, "ok": False, "error": {"code": "INVALID_REQUEST", "message": str(error)}}
    except Exception:
        # Do not expose private database paths, source records or credentials.
        return {**envelope, "ok": False, "error": {"code": "INTERNAL_ERROR",
                "message": "Local service failed; inspect local setup and database compatibility"}}


def main() -> int:
    raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
    try:
        if len(raw) > MAX_REQUEST_BYTES:
            raise ValueError("Request exceeds maximum size")
        request = json.loads(raw)
        response = handle(request)
    except (ValueError, UnicodeError):
        response = {"version": 1, "id": None, "ok": False,
                    "error": {"code": "INVALID_REQUEST", "message": "Invalid JSON request or size"}}
    print(json.dumps(response, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
