import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class StdioTests(unittest.TestCase):
    def invoke(self, raw, path):
        result = subprocess.run([sys.executable, "-m", "backend.service"], input=raw,
                                text=True, capture_output=True, timeout=10,
                                env={**os.environ, "RESEARCHOS_DB_PATH": str(path)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_malformed_input_and_unsupported_command_do_not_create_db(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.sqlite3"
            self.assertEqual(self.invoke("{", path)["error"]["code"], "INVALID_REQUEST")
            request = {"version": 1, "id": "test", "command": "shell", "payload": {}}
            self.assertEqual(self.invoke(json.dumps(request), path)["error"]["code"],
                             "INVALID_REQUEST")
            invalid = {"version":1,"id":"p","command":"get_paper","payload":{"paper_id":123}}
            self.assertEqual(self.invoke(json.dumps(invalid),path)["error"]["code"],"INVALID_REQUEST")
            overshared = {"version":1,"id":"p","command":"get_paper","payload":{"paper_id":"P-12345678","path":"/secret"}}
            self.assertEqual(self.invoke(json.dumps(overshared),path)["error"]["code"],"INVALID_REQUEST")
            self.assertFalse(path.exists())

    def test_health_taxonomy_and_search_with_empty_database(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.sqlite3"
            health = self.invoke(json.dumps({"version": 1, "id": "h", "command": "health",
                                            "payload": {}}), path)
            self.assertTrue(health["ok"], health)
            self.assertTrue(health["data"]["offline"])
            self.assertEqual(health["data"]["paper_count"], 0)
            self.assertIn("get_paper", health["data"]["capabilities"])
            self.assertFalse(health["data"]["fulltext_page_evidence"])
            self.assertEqual(health["data"]["index_version"], "sqlite-v1")
            taxonomy = self.invoke(json.dumps({"version": 1, "id": "t", "command": "taxonomy",
                                              "payload": {}}), path)
            self.assertEqual(taxonomy["data"]["tags"], [])
            search = self.invoke(json.dumps({"version": 1, "id": "s", "command": "search",
                                            "payload": {"query": "attention", "mode": "STRICT",
                                                        "scope": "LOCAL_ONLY"}}), path)
            self.assertTrue(search["ok"], search)
            self.assertEqual(search["data"]["results"], [])
            self.assertEqual(search["data"]["total"], 0)
            get_paper = self.invoke(json.dumps({"version":1,"id":"p","command":"get_paper",
                                                "payload":{"paper_id":"P-example0123"}}),path)
            self.assertTrue(get_paper["ok"])
            self.assertFalse(get_paper["data"]["found"])
            self.assertIsNone(get_paper["data"]["paper"])
            self.assertEqual(get_paper["data"]["evidence_state"],"catalog-metadata-only")


    def test_get_paper_returns_existing_source_attributed_record(self):
        from backend.ingest import import_catalog
        from backend.persistence import connect, migrate
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"catalog.sqlite3"
            db=connect(path)
            try:
                migrate(db)
                fixture={
                    "tags":[{"tag_id":"method/example","namespace":"method","label":"Example","aliases":[]}],
                    "papers":[{"paper_id":"P-original-1","title":"Source-backed paper",
                               "authors":["Researcher"],"year":2025,"source_url":"https://example.org/paper",
                               "eligibility":"unknown"}],
                    "paper_tags":[{"paper_id":"P-original-1","tag_id":"method/example",
                                   "role":"candidate","asserted_from":"lexical_discovery",
                                   "review_state":"needs-manual-review","evidence":"synthetic fixture"}],
                }
                import_catalog(db, fixture, "fixture", "revision1")
            finally:
                db.close()
            found=self.invoke(json.dumps({"version":1,"id":"read","command":"get_paper",
                                          "payload":{"paper_id":"P-original-1"}}),path)
            self.assertTrue(found["ok"],found)
            result=found["data"]
            self.assertTrue(result["found"])
            self.assertEqual(result["paper"]["paper_id"],"P-original-1")
            self.assertEqual(result["paper"]["title"],"Source-backed paper")
            self.assertEqual(result["paper"]["tags"][0]["review_state"],"needs-manual-review")
            self.assertEqual(result["evidence_state"],"catalog-metadata-only")
            missing=self.invoke(json.dumps({"version":1,"id":"miss","command":"get_paper",
                                            "payload":{"paper_id":"P-nonexisting"}}),path)
            self.assertFalse(missing["data"]["found"])


if __name__ == "__main__":
    unittest.main()
