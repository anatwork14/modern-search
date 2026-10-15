"""Run a small reproducible local encoder timing check after model install."""

from __future__ import annotations

import argparse
import json
import platform
import resource
import statistics
import time
from typing import Sequence

from .encoder import _get_model, encode_query, encode_titled_documents, model_manifest


def _timings(call, repeat: int) -> dict:
    samples = []
    for _ in range(repeat):
        started = time.perf_counter()
        call()
        samples.append(time.perf_counter() - started)
    ordered = sorted(samples)
    return {
        "samples_seconds": samples,
        "p50_seconds": statistics.median(samples),
        "p95_nearest_rank_seconds": ordered[-1],
    }


def run(repeat: int, corpus_revision: str) -> dict:
    started = time.perf_counter()
    model = _get_model()
    load_seconds = time.perf_counter() - started
    query = "cache-efficient attention mechanisms"
    documents = [{"title": "Test paper", "text": "A bounded smoke input for model compatibility."}]
    encode_query(query)
    encode_titled_documents(documents)
    query_vector = encode_query(query)
    document_vector = encode_titled_documents(documents)[0]
    query_timing = _timings(lambda: encode_query(query), repeat)
    document_timing = _timings(lambda: encode_titled_documents(documents), repeat)
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() != "Darwin":
        peak_rss *= 1024
    import torch
    import transformers
    import sentence_transformers

    return {
        "status": "PASS",
        "python": platform.python_version(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "sentence_transformers": sentence_transformers.__version__,
        "device": str(model.device),
        "mps_available": bool(torch.backends.mps.is_available()),
        "load_seconds": load_seconds,
        "warmup_calls": 2,
        "repeats_per_route": repeat,
        "query": {
            "dimension": len(query_vector),
            "l2_norm": sum(value * value for value in query_vector) ** 0.5,
            **query_timing,
        },
        "document": {
            "dimension": len(document_vector),
            "l2_norm": sum(value * value for value in document_vector) ** 0.5,
            **document_timing,
        },
        "peak_rss_bytes": peak_rss,
        "manifest": model_manifest(corpus_revision=corpus_revision),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--corpus-revision", default="smoke-fixture-v1")
    args = parser.parse_args(argv)
    if not 1 <= args.repeat <= 20:
        parser.error("--repeat must be between 1 and 20")
    print(json.dumps(run(args.repeat, args.corpus_revision), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
