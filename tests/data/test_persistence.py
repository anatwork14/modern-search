import sqlite3
import unittest

from backend.ingest import import_catalog
from backend.persistence import connect, export_papers, export_tags, migrate


def catalog():
    return {
        "tags": [{"tag_id": "method/example", "namespace": "method", "label": "Example", "aliases": ["Example alias"]}],
        "papers": [{"paper_id": "P-original-1", "title": "A source-backed paper", "authors": ["A. Author"], "year": 2025,
                    "doi": "https://doi.org/10.1234/ABC", "source_url": "https://example.org/paper",
                    "arxiv_id": "https://arxiv.org/abs/2401.12345v2",
                    "pdf_url": "https://example.org/paper.pdf", "eligibility": "unknown",
                    "venue_evidence": {"ranking_system": "SJR", "sjr_quartile": "Q1", "ranking_year": 2023,
                                       "ranking_source_url": "https://example.org/rank", "publication_evidence_url": "https://example.org/pub"}}],
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
        self.assertEqual(paper["identifiers"], ["10.1234/abc", "2401.12345v2"])
        self.assertEqual(paper["identifier_records"], [{"kind": "arxiv", "value": "2401.12345v2"}, {"kind": "doi", "value": "10.1234/abc"}])
        self.assertTrue(paper["venue_evidence"][0]["source_asserted"])
        self.assertEqual(paper["venue_evidence"][0]["ranking_year"], 2023)
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

    def test_source_reimport_preserves_human_review_and_qualification_decisions(self):
        source = catalog()
        import_catalog(self.db, source, "fixture", "r1")
        self.db.execute("UPDATE papers SET review_state='manually-verified', eligibility_state='verified-qualified' WHERE paper_id='P-original-1'")
        self.db.execute("UPDATE paper_tags SET review_state='verified' WHERE paper_id='P-original-1'")
        self.db.commit()
        source["paper_tags"].clear()
        source["papers"][0]["review_state"] = "discovered"
        source["papers"][0]["eligibility"] = "unknown"
        import_catalog(self.db, source, "fixture", "r2")
        row = self.db.execute("SELECT review_state,eligibility_state FROM papers WHERE paper_id='P-original-1'").fetchone()
        self.assertEqual(tuple(row), ("manually-verified", "verified-qualified"))
        tag_row = self.db.execute("SELECT review_state FROM paper_tags WHERE paper_id='P-original-1'").fetchone()
        self.assertEqual(tag_row[0], "verified")

    def test_changed_arxiv_identifier_replaces_prior_source_identifier(self):
        source = catalog()
        import_catalog(self.db, source, "fixture", "r1")
        source["papers"][0]["arxiv_id"] = "2501.98765"
        import_catalog(self.db, source, "fixture", "r2")
        values = [r[0] for r in self.db.execute("SELECT normalized_value FROM paper_identifiers WHERE paper_id='P-original-1' AND kind='arxiv'")]
        self.assertEqual(values, ["2501.98765"])

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
