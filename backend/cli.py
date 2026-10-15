"""Explicit local catalog import; never performs network requests."""
import argparse
import hashlib
import json
from pathlib import Path

from backend.service import database_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path, help="Local catalog JSON snapshot")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--source-revision", help="Defaults to snapshot SHA-256")
    parser.add_argument("--database", type=Path, default=database_path())
    args = parser.parse_args()
    from backend.persistence import connect, migrate
    from backend.ingest import import_catalog

    raw = args.catalog.read_bytes()
    catalog = json.loads(raw)
    args.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    connection = connect(args.database)
    try:
        migrate(connection)
        result = import_catalog(connection, catalog, args.source_id,
                                args.source_revision or hashlib.sha256(raw).hexdigest())
        print(json.dumps(result, ensure_ascii=False))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
