"""Local EmbeddingGemma 2 encoder with explicit offline failure behavior.

The import path and manifest are standard-library-only. Model packages and files
are optional; the first query never downloads anything and raises a typed error
when the pinned snapshot is not already cached.
"""

from __future__ import annotations

import os
import math
import threading
from pathlib import Path
from typing import Any, Mapping, Sequence

MODEL_ID = "google/embeddinggemma-2"
MODEL_REVISION = "914f7f89142e33e77833254d9c9b90c3cef7303b"
DIMENSION = 768
QUERY_PROMPT_VERSION = "embeddinggemma2-searchquery-v1"
DOCUMENT_PROMPT_VERSION = "embeddinggemma2-titled-document-v1"
NORMALIZATION = "l2-float32"


class EmbeddingsUnavailableError(RuntimeError):
    """Dense search is unavailable; callers should continue lexical search."""

    code = "MODEL_UNAVAILABLE"


_model: Any = None
_model_lock = threading.Lock()


def model_manifest(*, corpus_revision: str | None = None) -> dict[str, Any]:
    """Return the pinned encoder contract, including absent-runtime metadata."""
    return {
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "license": "apache-2.0",
        "tokenizer": "google/embeddinggemma-2@" + MODEL_REVISION,
        "prompt_version": {
            "query": QUERY_PROMPT_VERSION,
            "document": DOCUMENT_PROMPT_VERSION,
        },
        "query_template": "task: search result | query: {query}",
        "document_template": "title: {title} | text: {text}",
        "dimension": DIMENSION,
        "normalized": True,
        "normalization": NORMALIZATION,
        "corpus_revision": corpus_revision,
        "modalities": ["text"],
    }


def _resolve_cached_snapshot() -> Path:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise EmbeddingsUnavailableError(
            "Dense search is unavailable: install the optional embedding runtime."
        ) from exc
    try:
        path = snapshot_download(
            repo_id=MODEL_ID,
            revision=MODEL_REVISION,
            local_files_only=True,
        )
    except Exception as exc:
        raise EmbeddingsUnavailableError(
            "Dense search is unavailable: the pinned model snapshot is not cached."
        ) from exc
    snapshot = Path(path)
    if not (snapshot / "model.safetensors").is_file():
        raise EmbeddingsUnavailableError(
            "Dense search is unavailable: the cached snapshot lacks safe model weights."
        )
    return snapshot


def _get_model() -> Any:
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        snapshot = _resolve_cached_snapshot()
        try:
            import torch
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingsUnavailableError(
                "Dense search is unavailable: install the optional embedding runtime."
            ) from exc

        requested = os.environ.get("RESEARCHOS_EMBEDDING_DEVICE", "auto").lower()
        if requested == "auto":
            device = "mps" if torch.backends.mps.is_available() else "cpu"
        elif requested in {"cpu", "mps"}:
            if requested == "mps" and not torch.backends.mps.is_available():
                raise EmbeddingsUnavailableError(
                    "Dense search is unavailable: MPS was requested but is not available."
                )
            device = requested
        else:
            raise EmbeddingsUnavailableError(
                "Dense search is unavailable: RESEARCHOS_EMBEDDING_DEVICE must be auto, mps, or cpu."
            )
        try:
            _model = SentenceTransformer(
                str(snapshot),
                device=device,
                config_kwargs={"vision_config": None, "audio_config": None},
                local_files_only=True,
                trust_remote_code=False,
                model_kwargs={
                    "use_safetensors": True,
                },
            )
        except Exception as exc:
            raise EmbeddingsUnavailableError(
                "Dense search is unavailable: the pinned text-only model could not be loaded."
            ) from exc
        return _model


def _encode(texts: list[str], **kwargs: Any) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    try:
        encoded = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
            **kwargs,
        )
        rows = encoded.tolist()
    except Exception as exc:
        raise EmbeddingsUnavailableError(
            "Dense search is unavailable: local model inference failed."
        ) from exc
    if len(rows) != len(texts) or any(len(row) != DIMENSION for row in rows):
        raise EmbeddingsUnavailableError(
            "Dense search is unavailable: model output does not match the 768d manifest."
        )
    normalized: list[list[float]] = []
    for row in rows:
        try:
            vector = [float(value) for value in row]
        except (TypeError, ValueError) as exc:
            raise EmbeddingsUnavailableError(
                "Dense search is unavailable: model output contains non-numeric values."
            ) from exc
        if not all(math.isfinite(value) for value in vector):
            raise EmbeddingsUnavailableError(
                "Dense search is unavailable: model output contains non-finite values."
            )
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            raise EmbeddingsUnavailableError(
                "Dense search is unavailable: model output has zero norm."
            )
        # MPS float32 outputs can retain small norm error from lower-precision
        # model kernels. Normalize the final host vector explicitly for the index.
        normalized.append([value / norm for value in vector])
    return normalized


def encode_query(text: str) -> list[float]:
    """Encode one retrieval query with Google's SearchQuery task prompt."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    rows = _encode([text], prompt_name="SearchQuery")
    return rows[0]


def encode_titled_documents(
    documents: Sequence[Mapping[str, str]],
) -> list[list[float]]:
    """Encode titled text units using the model card's document template."""
    if isinstance(documents, (str, bytes)) or not isinstance(documents, Sequence):
        raise TypeError("documents must be a sequence of {title, text} mappings")
    formatted: list[str] = []
    for index, document in enumerate(documents):
        if not isinstance(document, Mapping):
            raise TypeError(f"documents[{index}] must be a mapping")
        title, text = document.get("title"), document.get("text")
        if not isinstance(title, str) or not isinstance(text, str):
            raise TypeError(f"documents[{index}] requires string title and text")
        formatted.append(f"title: {title or 'none'} | text: {text}")
    # The title is already in the text. Empty prompt avoids SentenceTransformers'
    # generic Document prompt from adding a second `title: none` prefix.
    return _encode(formatted, prompt="")
