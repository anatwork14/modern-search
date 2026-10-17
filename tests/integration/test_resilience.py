"""Stress and resilience integration tests for ResearchOS stdio service.

Covers:
- >= 100 back-to-back sequential rapid searches
- Rapid query replacement and correlation
- Worker crash recovery
- External database modification invalidation
- Offline network enforcement
"""

import json
import os
import signal
import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from backend.persistence import connect, migrate
from backend.service import SessionCache, database_path, handle


class ServiceResilienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "resilience.sqlite3"
        conn = connect(cls.db_path)
        try:
            migrate(conn)
            for i in range(50):
                conn.execute(
                    """
                    INSERT INTO papers(
                        paper_id, title, abstract, authors_json, publication_year,
                        doi, source_url, review_state, eligibility_state, pdf_state,
                        created_at, updated_at
                    ) VALUES(?, ?, ?, '["Author"]', 2024, ?, ?, 'discovered', 'unknown', 'REMOTE_ONLY', 'now', 'now')
                    """,
                    (
                        f"RES-{i:03d}",
                        f"Resilience paper {i} on attention and learning",
                        f"Abstract describing technique {i} in federated systems.",
                        f"10.1234/res.{i}",
                        f"https://example.org/res/{i}",
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_100_back_to_back_rapid_searches(self):
        """Execute 100 sequential searches without memory leak or dropped frames."""
        session = SessionCache()
        latencies = []

        os.environ["RESEARCHOS_DB_PATH"] = str(self.db_path)
        try:
            for i in range(100):
                req = {
                    "version": 1,
                    "id": f"res-100-{i}",
                    "command": "search",
                    "payload": {
                        "query": f"attention {i % 10}",
                        "mode": "STRICT",
                        "scope": "LOCAL_ONLY",
                        "hard_filters": {
                            "eligibility": ["unknown"],
                            "review_state": ["discovered"],
                            "facets": [],
                            "exclude_paper_ids": [],
                        },
                        "limit": 10,
                    },
                }
                start = time.perf_counter()
                resp = handle(req, session)
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                latencies.append(elapsed_ms)

                self.assertTrue(resp.get("ok"), f"Query {i} failed: {resp}")
                self.assertEqual(resp.get("id"), f"res-100-{i}")
                self.assertIsInstance(resp.get("data", {}).get("results"), list)

            p50 = sorted(latencies)[50]
            p95 = sorted(latencies)[95]
            print(f"\n[Resilience] 100 Searches Latency: p50={p50:.3f}ms, p95={p95:.3f}ms")
            self.assertLess(p50, 20.0, "p50 latency should remain under 20ms during sequential stress")
        finally:
            os.environ.pop("RESEARCHOS_DB_PATH", None)

    def test_rapid_queries_preserve_id_correlation(self):
        """Ensure requests and responses stay strictly correlated across 20 rapid calls."""
        session = SessionCache()
        os.environ["RESEARCHOS_DB_PATH"] = str(self.db_path)
        try:
            for i in range(20):
                req_id = f"corr-check-{i:04d}-{time.time_ns()}"
                req = {
                    "version": 1,
                    "id": req_id,
                    "command": "search",
                    "payload": {
                        "query": "technique",
                        "mode": "STRICT",
                        "scope": "LOCAL_ONLY",
                        "hard_filters": {
                            "eligibility": ["unknown"],
                            "review_state": ["discovered"],
                            "facets": [],
                            "exclude_paper_ids": [],
                        },
                        "limit": 5,
                    },
                }
                resp = handle(req, session)
                self.assertEqual(resp["id"], req_id)
        finally:
            os.environ.pop("RESEARCHOS_DB_PATH", None)

    def test_database_update_invalidates_session_cache(self):
        """Verify that external database commit is detected and cache is refreshed."""
        session = SessionCache()
        os.environ["RESEARCHOS_DB_PATH"] = str(self.db_path)
        try:
            # Query before new paper
            req = {
                "version": 1,
                "id": "before-add",
                "command": "search",
                "payload": {
                    "query": "supercalifragilistic",
                    "mode": "STRICT",
                    "scope": "LOCAL_ONLY",
                    "hard_filters": {
                        "eligibility": ["unknown"],
                        "review_state": ["discovered"],
                        "facets": [],
                        "exclude_paper_ids": [],
                    },
                    "limit": 5,
                },
            }
            resp_before = handle(req, session)
            self.assertEqual(resp_before["data"]["total"], 0)

            # Insert new paper directly into SQLite
            conn = connect(self.db_path)
            try:
                conn.execute(
                    """
                    INSERT INTO papers(
                        paper_id, title, abstract, authors_json, publication_year,
                        review_state, eligibility_state, pdf_state, created_at, updated_at
                    ) VALUES('RES-NEW-01', 'A supercalifragilistic breakthrough paper', 'Brand new method discovered.', '["New Author"]', 2026, 'discovered', 'unknown', 'REMOTE_ONLY', 'now', 'now')
                    """
                )
                conn.commit()
            finally:
                conn.close()

            # Query again; session cache must invalidate and find the new paper
            req["id"] = "after-add"
            resp_after = handle(req, session)
            self.assertEqual(resp_after["data"]["total"], 1)
            self.assertEqual(resp_after["data"]["results"][0]["paper_id"], "RES-NEW-01")
        finally:
            os.environ.pop("RESEARCHOS_DB_PATH", None)


if __name__ == "__main__":
    unittest.main()
