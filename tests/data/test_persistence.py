import sqlite3
import unittest

from backend.ingest import import_catalog
from backend.persistence import connect, export_papers, export_tags, migrate


def catalog():
    return {
        "tags": [{"tag_id": "method/example", "namespace": "method", "label": "Example", "aliases": ["Example alias"]}],
        "papers": [{"paper_id": "P-original-1", "title": "A source-backed paper", "authors": ["A. Author"], "year": 2025,
                    "doi": "https://doi.org/10.1234/ABC", "source_url": "https://example.org/paper",
                    "pdf_url": "https://example.org/paper.pdf", "eligibility": "unknown"}],
        "paper_tags": [{"paper_id": "P-original-1", "tag_id": "method/example", "role": "candidate",
                         "asserted_from": "lexical_discovery", "review_state": "needs-manual-review",
                         "evidence": "Synthetic fixture only"}],
    }


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")
        migrate(self.db)

    def tearDown(self):
        self.db.close()

    def test_migration_is_repeatable_and_enables_constraints_and_fts(self):
        self.assertEqual(migrate(self.db), 1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM schema_migrations").fetchone()[0], 1)
        self.assertEqual(self.db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.db.execute("INSERT INTO papers(paper_id,title,created_at,updated_at) VALUES('p','searchable title','now','now')")
        self.assertEqual(self.db.execute("SELECT paper_id FROM papers_fts WHERE papers_fts MATCH 'searchable'").fetchone()[0], "p")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO paper_tags(paper_id,tag_id,role,asserted_from) VALUES('missing','missing','candidate','metadata')")

    def test_reimport_preserves_identity_and_is_idempotent(self):
        first = import_catalog(self.db, catalog(), "fixture", "revision-1")
        second = import_catalog(self.db, catalog(), "fixture", "revision-1")
        self.assertEqual(first["imported"]["papers"], 1)
        self.assertEqual(second["imported"]["papers"], 0)
        self.assertEqual(second["imported"]["paper_tags"], 0)
        self.assertEqual(self.db.execute("SELECT paper_id FROM papers").fetchone()[0], "P-original-1")
        self.assertEqual(self.db.execute("SELECT count(*) FROM source_records").fetchone()[0], 3)
        paper = export_papers(self.db)[0]
        self.assertEqual(paper["doi"], "10.1234/abc")
        self.assertEqual(paper["pdf_state"], "REMOTE_ONLY")
        self.assertEqual(paper["tags"][0]["review_state"], "needs-manual-review")
        self.assertEqual(export_tags(self.db)[0]["aliases"], ["Example alias"])

    def test_new_source_revision_retains_prior_provenance_without_duplicate_assertions(self):
        source = catalog()
        import_catalog(self.db, source, "fixture", "r1")
        source["papers"][0]["title"] = "Updated source title"
        result = import_catalog(self.db, source, "fixture", "r2")
        self.assertEqual(result["updated"]["papers"], 1)
        self.assertEqual(self.db.execute("SELECT title FROM papers WHERE paper_id='P-original-1'").fetchone()[0], "Updated source title")
        self.assertEqual(self.db.execute("SELECT count(*) FROM source_records WHERE record_kind='paper'").fetchone()[0], 2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM paper_tags").fetchone()[0], 1)

    def test_newer_snapshot_reconciles_removed_source_mappings_and_tags(self):
        source = catalog()
        import_catalog(self.db, source, "fixture", "r1")
        source["paper_tags"].clear()
        source["tags"].clear()
        result = import_catalog(self.db, source, "fixture", "r2")
        self.assertEqual(result["total"]["paper_tags"], 0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM paper_tags").fetchone()[0], 0)
        self.assertEqual(export_tags(self.db), [])
        self.assertEqual(self.db.execute("SELECT count(*) FROM source_records WHERE record_kind='paper_tag'").fetchone()[0], 1)

    def test_doi_collision_aborts_whole_batch(self):
        source = catalog()
        source["papers"].append({"paper_id": "P-original-2", "title": "Another paper", "doi": "10.1234/abc"})
        with self.assertRaisesRegex(ValueError, "DOI collision"):
            import_catalog(self.db, source, "fixture", "r1")
        self.assertEqual(self.db.execute("SELECT count(*) FROM papers").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM source_records").fetchone()[0], 0)

    def test_unknown_tag_reference_is_rejected_before_writes(self):
        source = catalog()
        source["paper_tags"][0]["tag_id"] = "missing/tag"
        with self.assertRaisesRegex(ValueError, "unknown tag"):
            import_catalog(self.db, source, "fixture", "r1")
        self.assertEqual(self.db.execute("SELECT count(*) FROM papers").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
