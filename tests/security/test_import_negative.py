"""Synthetic source-import boundary checks; never reads the private catalog."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.ingest import import_catalog
from backend.ingest import workbook
from backend.persistence import connect, migrate
from backend.retrieval import search


def paper(paper_id: str, doi: str | None = None, **extra):
    return {"paper_id": paper_id, "title": f"Synthetic {paper_id}", "doi": doi, **extra}


class ImportSecurityTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")
        migrate(self.db)

    def tearDown(self):
        self.db.close()

    def test_doi_collision_across_sources_cannot_repoint_another_papers_provenance(self):
        import_catalog(self.db, {"papers": [paper("P-OWNER", "10.1234/same")]},
                       "source-one", "revision-1")
        before = self.db.execute(
            "SELECT paper_id, source_record_id FROM paper_identifiers WHERE kind='doi'"
        ).fetchone()
        self.assertEqual(before[0], "P-OWNER")
        with self.assertRaisesRegex(ValueError, "DOI collision"):
            import_catalog(self.db, {"papers": [paper("P-SECOND", "doi:10.1234/SAME")]},
                           "source-two", "revision-1")
        after = self.db.execute(
            "SELECT paper_id, source_record_id FROM paper_identifiers WHERE kind='doi'"
        ).fetchone()
        self.assertEqual(tuple(after), tuple(before))
        self.assertIsNone(self.db.execute(
            "SELECT 1 FROM papers WHERE paper_id='P-SECOND'"
        ).fetchone())

    def test_malformed_doi_is_not_persisted_as_a_valid_identifier(self):
        import_catalog(self.db, {"papers": [paper("P-BAD-DOI", "not a doi")]},
                       "source", "revision-1")
        paper_row = self.db.execute(
            "SELECT doi FROM papers WHERE paper_id='P-BAD-DOI'"
        ).fetchone()
        identifier = self.db.execute(
            "SELECT normalized_value FROM paper_identifiers WHERE paper_id='P-BAD-DOI'"
        ).fetchone()
        self.assertIsNone(paper_row[0])
        self.assertIsNone(identifier)

    def test_qualified_state_requires_publication_evidence(self):
        import_catalog(self.db, {"papers": [paper(
            "P-UNSUPPORTED-QUALIFICATION", eligibility="verified-qualified",
        )]}, "untrusted-source", "revision-1")
        row = self.db.execute(
            "SELECT eligibility_state FROM papers WHERE paper_id='P-UNSUPPORTED-QUALIFICATION'"
        ).fetchone()
        self.assertEqual(row[0], "unknown")

    def test_alias_collision_remains_ambiguous_and_never_selects_a_tag(self):
        catalog = {
            "tags": [
                {"tag_id": "method/alpha", "namespace": "method", "label": "Alpha",
                 "aliases": ["shared alias"]},
                {"tag_id": "method/beta", "namespace": "method", "label": "Beta",
                 "aliases": ["shared alias"]},
            ],
            "papers": [paper("P-ALIAS")],
        }
        import_catalog(self.db, catalog, "source", "revision-1")
        exported_tags = [dict(row) for row in self.db.execute(
            "SELECT tag_id, namespace, label FROM tags ORDER BY tag_id"
        )]
        for tag in exported_tags:
            tag["aliases"] = [row[0] for row in self.db.execute(
                "SELECT alias FROM tag_aliases WHERE tag_id=? ORDER BY alias", (tag["tag_id"],)
            )]
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            search([{"paper_id": "P-ALIAS", "eligibility": "verified-qualified",
                     "title": "Synthetic", "tags": []}], exported_tags,
                   {"query": "", "hard_filters": {"facets": [{
                       "namespace": "method", "operator": "ANY", "tags": ["shared alias"],
                   }]}})

    def test_workbook_adapter_does_not_silently_drop_unknown_edge_references(self):
        sheets = {
            "TAG_DICTIONARY": [["Canonical tag", "Namespace", "English label"],
                               ["method/known", "method", "Known"]],
            "PAPER_LIBRARY": [["Paper_ID", "Title"], ["P-KNOWN", "Known paper"]],
            "PAPER_TAGS": [["Paper_ID", "Canonical tag"], ["P-MISSING", "method/known"]],
        }
        with patch.object(workbook, "_xlsx_sheets", return_value=sheets):
            with self.assertRaisesRegex(ValueError, "unknown paper"):
                workbook.load_workbook_catalog("synthetic-only.xlsx")


if __name__ == "__main__":
    unittest.main()
