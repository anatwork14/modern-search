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
            self.assertFalse(path.exists())

    def test_health_taxonomy_and_search_with_empty_database(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.sqlite3"
            health = self.invoke(json.dumps({"version": 1, "id": "h", "command": "health",
                                            "payload": {}}), path)
            self.assertTrue(health["ok"], health)
            self.assertTrue(health["data"]["offline"])
            self.assertEqual(health["data"]["paper_count"], 0)
            taxonomy = self.invoke(json.dumps({"version": 1, "id": "t", "command": "taxonomy",
                                              "payload": {}}), path)
            self.assertEqual(taxonomy["data"]["tags"], [])
            search = self.invoke(json.dumps({"version": 1, "id": "s", "command": "search",
                                            "payload": {"query": "attention", "mode": "STRICT",
                                                        "scope": "LOCAL_ONLY"}}), path)
            self.assertTrue(search["ok"], search)
            self.assertEqual(search["data"]["results"], [])
            self.assertEqual(search["data"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
