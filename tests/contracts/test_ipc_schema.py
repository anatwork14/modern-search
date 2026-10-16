"""Executable validation of the published stdio IPC request contract."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]


class IpcSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "spec/ipc-v1.schema.json").read_text())
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)

    def test_schema_accepts_minimal_health_and_strict_local_search(self):
        examples = [
            {"version": 1, "id": "health-1", "command": "health", "payload": {}},
            {"version": 1, "id": "search-1", "command": "search", "payload": {
                "query": '"federated learning"', "mode": "STRICT", "scope": "LOCAL_ONLY",
                "limit": 20, "cursor": None,
                "hard_filters": {"eligibility": ["verified-qualified"], "facets": []},
            }},
        ]
        examples.append({"version":1,"id":"paper-1","command":"get_paper",
                         "payload":{"paper_id":"P-example0123"}})
        for request in examples:
            with self.subTest(command=request["command"]):
                self.assertEqual(list(self.validator.iter_errors(request)), [])

    def test_schema_rejects_boolean_integer_nan_and_unknown_fields(self):
        base = {"version": 1, "id": "search-1", "command": "search", "payload": {
            "query": "attention", "mode": "STRICT", "scope": "LOCAL_ONLY",
        }}
        cases = []
        boolean_version = json.loads(json.dumps(base))
        boolean_version["version"] = True
        cases.append(boolean_version)
        boolean_limit = json.loads(json.dumps(base))
        boolean_limit["payload"]["limit"] = True
        cases.append(boolean_limit)
        nan_limit = json.loads(json.dumps(base))
        nan_limit["payload"]["limit"] = float("nan")
        cases.append(nan_limit)
        unknown = json.loads(json.dumps(base))
        unknown["payload"]["filesystem_path"] = "/private/catalog.sqlite3"
        cases.append(unknown)
        for request in cases:
            with self.subTest(request=request):
                self.assertTrue(list(self.validator.iter_errors(request)))

    def test_get_paper_metadata_contract_rejects_extra_fields_and_controls(self):
        base={"version":1,"id":"paper","command":"get_paper","payload":{"paper_id":"P-abcdef1234"}}
        self.assertFalse(list(self.validator.iter_errors(base)))
        for payload in ({"paper_id":1},{"paper_id":""},{"paper_id":"bad\nname"},
                        {"paper_id":"P-abcdef1234","filesystem_path":"/private/db"}):
            candidate={**base,"payload":payload}
            self.assertTrue(list(self.validator.iter_errors(candidate)))

    def test_schema_rejects_unsafe_scope_and_malformed_cursor(self):
        base = {"version": 1, "id": "search-1", "command": "search", "payload": {
            "query": "attention", "mode": "STRICT", "scope": "REMOTE",
        }}
        self.assertTrue(list(self.validator.iter_errors(base)))
        bad_cursor = json.loads(json.dumps(base))
        bad_cursor["payload"]["scope"] = "LOCAL_ONLY"
        bad_cursor["payload"]["cursor"] = {"offset": 0}
        self.assertTrue(list(self.validator.iter_errors(bad_cursor)))


if __name__ == "__main__":
    unittest.main()
