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
    parser.add_argument("--build-index", action="store_true", help="Explicitly build local dense vectors using already cached weights")
    parser.add_argument("--index", type=Path, help="Default: database path with .dense.json suffix")
    args = parser.parse_args()
    from backend.persistence import connect, migrate
    from backend.ingest import import_catalog

    with args.catalog.open("rb") as stream:
        raw = stream.read(32 * 1024 * 1024 + 1)
    if len(raw) > 32 * 1024 * 1024:
        parser.error("Catalog exceeds supported size")
    if args.catalog.suffix.lower() == ".xlsx":
        from backend.ingest.workbook import load_workbook_catalog
        catalog = load_workbook_catalog(args.catalog)
    else:
        catalog = json.loads(raw)
    args.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    connection = connect(args.database)
    try:
        migrate(connection)
        result = import_catalog(connection, catalog, args.source_id,
                                args.source_revision or hashlib.sha256(raw).hexdigest())
        if args.build_index:
            from backend.persistence import export_papers, export_tags
            from backend.vector.index import build_index
            result["dense_index"] = build_index(args.index or args.database.with_suffix(".dense.json"),
                                                 export_papers(connection), export_tags(connection))
        print(json.dumps(result, ensure_ascii=False))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
