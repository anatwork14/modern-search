import json
import os
import select
import sqlite3
from unittest.mock import patch
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


    def test_session_reuses_fts_then_refreshes_after_catalog_commit(self):
        from backend.service import SessionCache, handle

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.sqlite3"
            session = SessionCache()
            def request(command, payload):
                return {"version": 1, "id": command, "command": command, "payload": payload}
            with patch.dict(os.environ, {"RESEARCHOS_DB_PATH": str(path)}):
                first = handle(request("health", {}), session=session)
                self.assertEqual(first["data"]["paper_count"], 0)
                old = session.prepared
                again = handle(request("taxonomy", {}), session=session)
                self.assertTrue(again["ok"])
                self.assertIs(session.prepared, old)

                # Simulate a legitimate external catalog importer committing
                # while the desktop's private Python worker remains alive.
                with sqlite3.connect(path) as writer:
                    writer.execute(
                        "INSERT INTO papers (paper_id,title,created_at,updated_at) VALUES (?,?,?,?)",
                        ("CACHE-001", "Cached Search Freshness", "2026-10-16", "2026-10-16"),
                    )

                refreshed = handle(request("health", {}), session=session)
                self.assertEqual(refreshed["data"]["paper_count"], 1)
                self.assertIsNot(session.prepared, old)
                result = handle(request("search", {
                    "query": "Cached Search Freshness", "mode": "STRICT",
                    "scope": "LOCAL_ONLY", "hard_filters": {"eligibility": ["unknown"]},
                }), session=session)
                self.assertTrue(result["ok"], result)
                self.assertEqual([p["paper_id"] for p in result["data"]["results"]], ["CACHE-001"])
            session.close()

    def test_multiple_requests_stay_on_one_process_without_eof(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.sqlite3"
            process = subprocess.Popen(
                [sys.executable, "-m", "backend.service"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env={**os.environ, "RESEARCHOS_DB_PATH": str(path)},
                bufsize=0,
            )
            try:
                assert process.stdin is not None
                assert process.stdout is not None
                for idx, command, payload in (
                    (1, "health", {}),
                    (2, "taxonomy", {}),
                    (3, "search", {"query": "hello", "mode": "STRICT", "scope": "LOCAL_ONLY"}),
                    (4, "unsupported", {}),
                    (5, "health", {}),
                ):
                    request = {"version": 1, "id": str(idx), "command": command, "payload": payload}
                    process.stdin.write((json.dumps(request) + "\n").encode())
                    process.stdin.flush()
                    readable, _, _ = select.select([process.stdout], [], [], 10)
                    self.assertTrue(readable, "Worker failed to flush a response before stdin EOF")
                    response = json.loads(process.stdout.readline())
                    self.assertEqual(response["id"], str(idx))
                    self.assertEqual(response["ok"], command != "unsupported")
                    self.assertIsNone(process.poll(), "Worker should remain live across requests")
                process.stdin.close()
                self.assertEqual(process.wait(timeout=10), 0)
                self.assertEqual(process.stderr.read(), b"")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)

    def test_oversize_frame_does_not_poison_following_request(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.sqlite3"
            good = json.dumps({"version": 1, "id": "after", "command": "health", "payload": {}})
            raw = b"x" * (1_048_576 + 200) + b"\n" + good.encode() + b"\n"
            result = subprocess.run([sys.executable, "-m", "backend.service"], input=raw,
                                    capture_output=True, timeout=10,
                                    env={**os.environ, "RESEARCHOS_DB_PATH": str(path)})
            self.assertEqual(result.returncode, 0, result.stderr)
            responses = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(responses), 2)
            self.assertEqual(responses[0]["error"]["code"], "INVALID_REQUEST")
            self.assertTrue(responses[1]["ok"])
            self.assertEqual(responses[1]["id"], "after")


if __name__ == "__main__":
    unittest.main()
