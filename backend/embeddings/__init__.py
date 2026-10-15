"""Offline-only text embedding adapter for the ResearchOS search MVP."""

from .encoder import (
    MODEL_ID,
    MODEL_REVISION,
    EmbeddingsUnavailableError,
    encode_query,
    encode_titled_documents,
    model_manifest,
)

__all__ = [
    "MODEL_ID",
    "MODEL_REVISION",
    "EmbeddingsUnavailableError",
    "encode_query",
    "encode_titled_documents",
    "model_manifest",
]
