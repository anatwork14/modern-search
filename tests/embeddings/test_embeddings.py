import unittest
from unittest.mock import patch

from backend.embeddings import (
    MODEL_ID,
    MODEL_REVISION,
    EmbeddingsUnavailableError,
    encode_query,
    encode_titled_documents,
    model_manifest,
)
from backend.embeddings import encoder
from backend.vector import IndexMismatchError, assert_compatible, make_index_manifest


class EmbeddingContractTests(unittest.TestCase):
    def test_manifest_pins_official_model_and_prompt_contract(self):
        manifest = model_manifest(corpus_revision="fixture-v1")
        self.assertEqual(manifest["model_id"], MODEL_ID)
        self.assertEqual(manifest["model_revision"], MODEL_REVISION)
        self.assertEqual(manifest["dimension"], 768)
        self.assertTrue(manifest["normalized"])
        self.assertEqual(
            manifest["query_template"], "task: search result | query: {query}"
        )
        self.assertEqual(
            manifest["document_template"], "title: {title} | text: {text}"
        )
        self.assertEqual(manifest["corpus_revision"], "fixture-v1")

    def test_missing_snapshot_is_a_typed_unavailable_error(self):
        with patch.object(
            encoder,
            "_resolve_cached_snapshot",
            side_effect=EmbeddingsUnavailableError("snapshot absent"),
        ):
            with self.assertRaises(EmbeddingsUnavailableError) as caught:
                encode_query("test query")
        self.assertEqual(caught.exception.code, "MODEL_UNAVAILABLE")

    def test_empty_documents_need_no_model(self):
        self.assertEqual(encode_titled_documents([]), [])

    def test_inputs_are_validated_before_model_load(self):
        with self.assertRaises(TypeError):
            encode_query(42)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            encode_titled_documents([{"title": "missing text"}])  # type: ignore[list-item]

    def test_query_and_titled_document_prompt_inputs(self):
        calls = []

        class FakeModel:
            def encode(self, texts, **kwargs):
                calls.append((texts, kwargs))
                return FakeVectors([[1.0] + [0.0] * 767 for _ in texts])

        class FakeVectors:
            def __init__(self, values):
                self.values = values

            def tolist(self):
                return self.values

        with patch.object(encoder, "_get_model", return_value=FakeModel()):
            query = encode_query("cache-efficient attention")
            documents = encode_titled_documents(
                [{"title": "A paper", "text": "Body text"}, {"title": "", "text": "No title"}]
            )
        self.assertEqual(len(query), 768)
        self.assertEqual(len(documents), 2)
        self.assertEqual(calls[0][0], ["cache-efficient attention"])
        self.assertEqual(calls[0][1]["prompt_name"], "SearchQuery")
        self.assertEqual(
            calls[1][0],
            ["title: A paper | text: Body text", "title: none | text: No title"],
        )
        self.assertEqual(calls[1][1]["prompt"], "")

    def test_non_normalized_and_non_finite_model_outputs_fail_closed(self):
        class FakeVectors:
            def __init__(self, values):
                self.values = values

            def tolist(self):
                return self.values

        class FakeModel:
            def __init__(self, first):
                self.first = first

            def encode(self, texts, **kwargs):
                return FakeVectors([self.first for _ in texts])

        for bad_value in (0.0, float("nan"), float("inf")):
            vector = [0.0] * 768
            vector[0] = bad_value
            with patch.object(encoder, "_get_model", return_value=FakeModel(vector)):
                with self.assertRaises(EmbeddingsUnavailableError):
                    encode_query("query")

    def test_vector_index_requires_matching_model_and_corpus(self):
        manifest = make_index_manifest(corpus_revision="fixture-v1")
        assert_compatible(manifest, expected_corpus_revision="fixture-v1")
        with self.assertRaises(IndexMismatchError):
            assert_compatible(manifest, expected_corpus_revision="fixture-v2")
        manifest["encoder"]["dimension"] = 512
        with self.assertRaises(IndexMismatchError):
            assert_compatible(manifest)
        manifest = make_index_manifest(corpus_revision="fixture-v1")
        manifest["encoder"]["query_template"] = "task: changed | query: {query}"
        with self.assertRaises(IndexMismatchError):
            assert_compatible(manifest)


if __name__ == "__main__":
    unittest.main()
