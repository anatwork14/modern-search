"""Relevance evaluation and correctness test suite across 30 hand-judged queries.

Evaluates:
- 10 identity queries (exact DOI, arXiv ID, exact title)
- 10 domain/topic queries (methods, architectures, systems)
- 5 Vietnamese natural language queries
- 5 negative and filter invariant queries
"""

import json
import math
import os
import unittest
from pathlib import Path

from backend.persistence import connect, export_papers, export_tags, migrate
from backend.retrieval import search


class RelevanceEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_path = Path(__file__).parent.parent / "fixtures" / "relevance_30_queries.json"
        with open(fixture_path, encoding="utf-8") as f:
            cls.fixture = json.load(f)

        # Check for user catalog or use fallback
        db_env = os.environ.get("RESEARCHOS_DB_PATH")
        default_db = Path.home() / "Library" / "Application Support" / "ResearchOS" / "catalog.sqlite3"
        cls.db_path = Path(db_env) if db_env else (default_db if default_db.is_file() else None)

        if cls.db_path and cls.db_path.is_file():
            connection = connect(cls.db_path)
            try:
                cls.papers = export_papers(connection)
                cls.tags = export_tags(connection)
            finally:
                connection.close()
        else:
            cls.papers = []
            cls.tags = []

    def test_fixture_contains_at_least_30_queries(self):
        queries = self.fixture.get("queries", [])
        self.assertGreaterEqual(len(queries), 30, "Fixture must contain at least 30 judged queries")

        categories = {q["category"] for q in queries}
        self.assertIn("identity", categories)
        self.assertIn("topic", categories)
        self.assertIn("vietnamese", categories)
        self.assertIn("negative", categories)

    def test_evaluate_30_queries_on_catalog(self):
        if not self.papers:
            self.skipTest("Real catalog.sqlite3 not present; skipping catalog evaluation")

        queries = self.fixture["queries"]
        reciprocal_ranks = []
        dcg_scores = []

        for case in queries:
            qid = case["id"]
            query = case["query"]
            mode = case.get("mode", "STRICT")
            eligibility = case.get("eligibility", "unknown")
            facets = case.get("facets", [])

            request = {
                "query": query,
                "mode": mode,
                "scope": "LOCAL_ONLY",
                "hard_filters": {
                    "eligibility": [eligibility],
                    "review_state": ["discovered", "abstract-screened", "fulltext-indexed", "manually-verified"],
                    "facets": facets,
                    "exclude_paper_ids": [],
                },
                "limit": 20,
            }

            if "expected_error" in case:
                with self.assertRaises(ValueError, msg=f"Query {qid} should fail"):
                    search(self.papers, self.tags, request)
                continue

            result = search(self.papers, self.tags, request)
            results = result.get("results", [])
            total = result.get("total", 0)

            # Check min/max counts
            if "expected_min_count" in case:
                self.assertGreaterEqual(
                    total,
                    case["expected_min_count"],
                    f"Query {qid} ('{query}') returned {total} < expected {case['expected_min_count']}",
                )
            if "expected_max_count" in case:
                self.assertLessEqual(
                    total,
                    case["expected_max_count"],
                    f"Query {qid} ('{query}') returned {total} > expected {case['expected_max_count']}",
                )

            # Check target IDs
            expected_targets = case.get("expected_target_ids", [])
            if expected_targets:
                retrieved_ids = [r["paper_id"] for r in results]
                found = any(tid in retrieved_ids for tid in expected_targets)
                self.assertTrue(
                    found,
                    f"Query {qid} ('{query}') failed to retrieve any target in {expected_targets}; got {retrieved_ids[:5]}",
                )

            # Check top ID if specified
            if "expected_top_id" in case:
                self.assertTrue(len(results) > 0, f"Query {qid} returned 0 results")
                self.assertEqual(
                    results[0]["paper_id"],
                    case["expected_top_id"],
                    f"Query {qid} top result was {results[0]['paper_id']} instead of {case['expected_top_id']}",
                )

            # Calculate Reciprocal Rank for identity queries
            if case["category"] == "identity" and expected_targets:
                rank = None
                for i, r in enumerate(results, start=1):
                    if r["paper_id"] in expected_targets:
                        rank = i
                        break
                reciprocal_ranks.append(1.0 / rank if rank else 0.0)

        if reciprocal_ranks:
            mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
            print(f"\n[Relevance Evaluation] Identity Queries MRR@10: {mrr:.4f} across {len(reciprocal_ranks)} queries")
            self.assertEqual(mrr, 1.0, "Identity queries must have 100% precision (MRR = 1.0)")


if __name__ == "__main__":
    unittest.main()
