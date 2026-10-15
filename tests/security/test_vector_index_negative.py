"""Corruption checks for the local, versioned dense index."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from backend.vector import IndexMismatchError
from backend.vector.index import DenseIndex, build_index


class DenseIndexSecurityTests(unittest.TestCase):
    def setUp(self):
        self.papers = [
            {"paper_id": "P-A", "title": "Synthetic A", "abstract": None},
            {"paper_id": "P-B", "title": "Synthetic B", "abstract": None},
        ]
        self.vector = [1.0] + [0.0] * 767
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "index.json"
        build_index(
            self.path,
            self.papers,
            [],
            encoder=lambda docs: [self.vector for _ in docs],
        )

    def tearDown(self):
        self.folder.cleanup()

    def test_index_identity_must_match_the_current_sorted_corpus(self):
        data = json.loads(self.path.read_text())
        data["paper_ids"] = ["P-A", "P-ATTACKER"]
        self.path.write_text(json.dumps(data))
        with self.assertRaisesRegex(IndexMismatchError, "paper identity"):
            DenseIndex(self.path, self.papers, [])

    def test_content_policy_change_invalidates_the_index(self):
        data = json.loads(self.path.read_text())
        data["content_policy"] = "abstract-and-private-notes-v2"
        self.path.write_text(json.dumps(data))
        with self.assertRaisesRegex(IndexMismatchError, "content policy"):
            DenseIndex(self.path, self.papers, [])


if __name__ == "__main__":
    unittest.main()
