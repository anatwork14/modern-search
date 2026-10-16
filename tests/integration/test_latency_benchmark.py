"""Offline smoke for the reproducible cold vs persistent worker benchmark."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from backend.service import handle


class BenchmarkSmokeTest(unittest.TestCase):
    def test_measured_outputs_include_sample_count_and_p50_p95(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "local.sqlite3"
            with patch.dict(os.environ, {"RESEARCHOS_DB_PATH": str(path)}):
                result = handle({"version": 1, "id": "health", "command": "health", "payload": {}})
                self.assertTrue(result["ok"], result)
            completed = subprocess.run(
                [sys.executable, "scripts/benchmark_search.py", "--db", str(path),
                 "--mode", "STRICT", "--iterations", "5"],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            measured = json.loads(completed.stdout)
            self.assertEqual(measured["sample_count"], 5)
            self.assertEqual(measured["mode"], "STRICT")
            for route in ("cold_spawn", "persistent"):
                self.assertGreater(measured[route]["p50_ms"], 0)
                self.assertGreaterEqual(measured[route]["p95_ms"], measured[route]["p50_ms"])


if __name__ == "__main__":
    unittest.main()
