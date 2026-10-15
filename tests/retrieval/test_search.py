import unittest

from backend.retrieval import search


TAGS = [
    {"tag_id": "field/federated-learning", "namespace": "field", "label": "Federated learning", "aliases": ["FL"]},
    {"tag_id": "field/deep-learning", "namespace": "field", "label": "Deep learning", "aliases": []},
    {"tag_id": "task/iot-ids", "namespace": "task", "label": "IoT intrusion detection", "aliases": []},
    {"tag_id": "method/attention", "namespace": "method", "label": "Attention mechanism", "aliases": ["attention"]},
]


def paper(paper_id, *, tags=(), doi=None, title="", abstract="", eligibility="verified-qualified"):
    return {
        "paper_id": paper_id,
        "title": title,
        "abstract": abstract,
        "authors": ["A. Author"],
        "year": 2024,
        "doi": doi,
        "source_url": "https://example.org/paper",
        "review_state": "abstract-screened",
        "eligibility": eligibility,
        "pdf_state": "REMOTE_ONLY",
        "tags": [
            {"tag_id": tag_id, "review_state": state, "role": "candidate"}
            for tag_id, state in tags
        ],
    }


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.papers = [
            paper("P1", tags=[("field/federated-learning", "verified"), ("field/deep-learning", "verified"),
                              ("method/attention", "verified")],
                  doi="10.1234/example.1", title="Federated learning with attention",
                  abstract="Attention helps federated clients."),
            paper("P2", tags=[("field/federated-learning", "needs-manual-review"),
                              ("task/iot-ids", "verified")],
                  title="IoT intrusion detection", abstract="Federated learning for IoT."),
            paper("P3", tags=[("task/iot-ids", "verified")], title="A survey", abstract="Security survey."),
            paper("P4", title="Exploratory record", eligibility="unknown"),
        ]

    def run_query(self, request, papers=None, tags=None, dense=None):
        return search(self.papers if papers is None else papers,
                      TAGS if tags is None else tags, request, dense=dense)

    def ids(self, result):
        return [row["paper_id"] for row in result["results"]]

    def test_exact_doi_is_direct_and_safe_url_is_preserved(self):
        result = self.run_query({"query": "doi:10.1234/EXAMPLE.1"})
        self.assertEqual(self.ids(result), ["P1"])
        self.assertIn("EXACT_TERM", result["results"][0]["match_routes"])
        self.assertEqual(result["results"][0]["source_url"], "https://example.org/paper")

    def test_doi_with_balanced_parentheses_is_exact_not_token_expanded(self):
        exact = paper("DOI-1", doi="10.5555/example(4)", title="Example four")
        token_overlap = paper("DOI-2", doi="10.5555/example(5)", title="Example four")
        result = self.run_query({"query": "doi:10.5555/example(4)"}, papers=[exact, token_overlap])
        self.assertEqual(self.ids(result), ["DOI-1"])

    def test_arxiv_identifier_is_direct_lookup(self):
        record = paper("ARXIV-1", title="Paper without DOI", eligibility="exploratory")
        record["source_url"] = "https://arxiv.org/abs/2401.01234v2"
        result = self.run_query({"query": "https://arxiv.org/abs/2401.01234v1",
                                 "hard_filters": {"eligibility": ["exploratory"]}}, papers=[record])
        self.assertEqual(self.ids(result), ["ARXIV-1"])
        self.assertIn("EXACT_TERM", result["results"][0]["match_routes"])

    def test_quoted_phrase_matches_literal_phrase(self):
        result = self.run_query({"query": '"federated learning"'})
        self.assertEqual(self.ids(result), ["P1", "P2"])

    def test_empty_query_browses_qualified_only_and_has_deterministic_order(self):
        result = self.run_query({"query": ""})
        self.assertEqual(self.ids(result), ["P1", "P2", "P3"])
        self.assertEqual(result["total"], 3)

    def test_unknown_records_require_explicit_eligibility(self):
        self.assertNotIn("P4", self.ids(self.run_query({"query": ""})))
        result = self.run_query({"query": "", "hard_filters": {"eligibility": ["unknown"]}})
        self.assertEqual(self.ids(result), ["P4"])

    def test_facet_truth_table_any_all_not_and_across_facets(self):
        def filtered(operator, tags):
            return self.run_query({"query": "", "hard_filters": {"facets": [
                {"namespace": "field", "operator": operator, "tags": tags}
            ]}})

        self.assertEqual(self.ids(filtered("ANY", ["field/federated-learning"])), ["P1", "P2"])
        self.assertEqual(self.ids(filtered("ALL", ["field/federated-learning"])), ["P1", "P2"])
        self.assertEqual(self.ids(filtered("NOT", ["field/federated-learning"])), ["P3"])
        self.assertEqual(self.ids(filtered("ALL", ["field/federated-learning", "field/deep-learning"])), ["P1"])
        all_two = self.run_query({"query": "", "hard_filters": {"facets": [
            {"namespace": "field", "operator": "ALL", "tags": ["field/federated-learning"]},
            {"namespace": "method", "operator": "ALL", "tags": ["method/attention"]},
        ]}})
        self.assertEqual(self.ids(all_two), ["P1"])
        across = self.run_query({"query": "", "hard_filters": {"facets": [
            {"namespace": "field", "operator": "ANY", "tags": ["field/federated-learning"]},
            {"namespace": "task", "operator": "ANY", "tags": ["task/iot-ids"]},
        ]}})
        self.assertEqual(self.ids(across), ["P2"])

    def test_rejected_assertions_are_inactive_for_any_all_and_not(self):
        rejected = paper("REJECTED", tags=[("field/federated-learning", "rejected")])
        papers = self.papers + [rejected]
        def filtered(operator):
            return self.run_query({"query": "", "hard_filters": {"facets": [
                {"namespace": "field", "operator": operator, "tags": ["field/federated-learning"]}
            ]}}, papers=papers)
        self.assertNotIn("REJECTED", self.ids(filtered("ANY")))
        self.assertNotIn("REJECTED", self.ids(filtered("ALL")))
        self.assertIn("REJECTED", self.ids(filtered("NOT")))

    def test_review_filter_keeps_candidate_and_verified_assertions_distinct(self):
        result = self.run_query({"query": "", "hard_filters": {"facets": [
            {"namespace": "field", "operator": "ANY", "tags": ["FL"], "review_state": "verified"}
        ]}})
        self.assertEqual(self.ids(result), ["P1"])
        self.assertEqual(result["results"][0]["tags"][0]["review_state"], "verified")

    def test_unknown_or_ambiguous_tags_fail_even_for_empty_catalog(self):
        request = {"query": "", "hard_filters": {"facets": [
            {"namespace": "field", "operator": "ANY", "tags": ["field/missing"]}
        ]}}
        with self.assertRaisesRegex(ValueError, "Unknown or ambiguous tag"):
            self.run_query(request, papers=[])
        ambiguous = TAGS + [{"tag_id": "other/attention", "namespace": "other", "label": "Other", "aliases": ["attention"]}]
        with self.assertRaisesRegex(ValueError, "Unknown or ambiguous tag"):
            self.run_query({"query": "", "hard_filters": {"facets": [
                {"namespace": "method", "operator": "ANY", "tags": ["attention"]}
            ]}}, tags=ambiguous)

    def test_cursor_is_deterministic_and_bound_to_request_and_index(self):
        first = self.run_query({"query": "", "limit": 2})
        self.assertEqual(self.ids(first), ["P1", "P2"])
        self.assertIsNotNone(first["next_cursor"])
        second = self.run_query({"query": "", "limit": 2, "cursor": first["next_cursor"]})
        self.assertEqual(self.ids(second), ["P3"])
        with self.assertRaisesRegex(ValueError, "Invalid or stale cursor"):
            self.run_query({"query": "changed", "limit": 2, "cursor": first["next_cursor"]})
        modified = self.papers + [paper("P5", title="new paper")]
        with self.assertRaisesRegex(ValueError, "Invalid or stale cursor"):
            self.run_query({"query": "", "limit": 2, "cursor": first["next_cursor"]}, papers=modified)

    def test_unsupported_modes_fields_and_boolean_limit_are_rejected(self):
        for request in ({"query": "x", "mode": "BRIDGE"},
                        {"query": "x", "mode": []},
                        {"query": "x", "sql": "select * from papers"},
                        {"query": "x", "limit": True},
                        {"query": "x", "hard_filters": {"facets": [], "soft_concepts": []}},
                        {"query": "x", "hard_filters": {"facets": [
                            {"namespace": "field", "operator": [], "tags": ["field/federated-learning"]}
                        ]}}):
            with self.subTest(request=request), self.assertRaises(ValueError):
                self.run_query(request)

    def test_dense_failure_does_not_break_lexical_results(self):
        result = self.run_query({"query": "attention"}, dense=object())
        self.assertEqual(self.ids(result), ["P1"])
        self.assertEqual(result["dense_status"], "unavailable")

    def test_dense_rank_is_fused_and_tag_alias_is_searchable(self):
        result = self.run_query({"query": "FL", "mode": "BROAD"}, dense=["P2", "P1"])
        self.assertEqual(result["dense_status"], "ready")
        self.assertIn("P1", self.ids(result))
        self.assertIn("SEMANTIC", result["results"][0]["match_routes"])

    def test_strict_keeps_dense_only_candidates_out_but_broad_fuses_them(self):
        strict = self.run_query({"query": "attention", "mode": "STRICT"}, dense=["P3"])
        broad = self.run_query({"query": "attention", "mode": "BROAD"}, dense=["P3"])
        self.assertEqual(self.ids(strict), ["P1"])
        self.assertIn("P3", self.ids(broad))

    def test_empty_and_malformed_dense_rankings_are_unavailable(self):
        for dense in ([], {}, {"results": []}, {"results": [{}]}, ["P1", "P1"]):
            with self.subTest(dense=dense):
                result = self.run_query({"query": "attention", "mode": "BROAD"}, dense=dense)
                self.assertEqual(result["dense_status"], "unavailable")
                self.assertEqual(self.ids(result), ["P1"])

    def test_dense_callback_is_called_only_for_broad_search_and_failure_falls_back(self):
        calls = []
        def provider(query):
            calls.append(query)
            return {"results": ["P3"]}
        strict = self.run_query({"query": "attention", "mode": "STRICT"}, dense=provider)
        broad = self.run_query({"query": "attention", "mode": "BROAD"}, dense=provider)
        self.assertEqual(calls, ["attention"])
        self.assertNotIn("P3", self.ids(strict))
        self.assertIn("P3", self.ids(broad))
        failed = self.run_query({"query": "attention", "mode": "BROAD"}, dense=lambda _: 1 / 0)
        self.assertEqual(self.ids(failed), ["P1"])
        self.assertEqual(failed["dense_status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
