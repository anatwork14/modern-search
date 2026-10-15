"""Compatibility checks for dense indexes; no vector database dependency."""

from __future__ import annotations

from typing import Any, Mapping

from backend.embeddings import model_manifest


class IndexMismatchError(ValueError):
    """A query encoder cannot safely search this dense index."""

    code = "INDEX_MISMATCH"


def make_index_manifest(*, corpus_revision: str) -> dict[str, Any]:
    if not isinstance(corpus_revision, str) or not corpus_revision.strip():
        raise ValueError("corpus_revision must be a non-empty string")
    return {
        "schema_version": 1,
        "encoder": model_manifest(corpus_revision=corpus_revision),
    }


def assert_compatible(
    index_manifest: Mapping[str, Any], *, expected_corpus_revision: str | None = None
) -> None:
    if not isinstance(index_manifest, Mapping) or index_manifest.get("schema_version") != 1:
        raise IndexMismatchError("Dense index manifest schema is missing or unsupported.")
    encoder = index_manifest.get("encoder")
    if not isinstance(encoder, Mapping):
        raise IndexMismatchError("Dense index encoder manifest is missing.")
    expected = model_manifest(corpus_revision=expected_corpus_revision)
    for key in (
        "model_id",
        "model_revision",
        "tokenizer",
        "prompt_version",
        "query_template",
        "document_template",
        "dimension",
        "normalized",
        "normalization",
    ):
        if encoder.get(key) != expected.get(key):
            raise IndexMismatchError(f"Dense index {key} does not match the query encoder.")
    if expected_corpus_revision is not None and encoder.get("corpus_revision") != expected_corpus_revision:
        raise IndexMismatchError("Dense index corpus revision does not match the requested corpus.")
