#!/usr/bin/env python3
"""Compare measured cold-spawn vs warm persistent local search latency.

The benchmark never imports, changes or sends catalog data over the network.
Use on an existing local database. Timings include IPC and Python worker work.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import select
import statistics
import subprocess
import sys
import time


def percentile(data: list[float], percent: float) -> float:
    points = sorted(data)
    scaled = (len(points) - 1) * percent / 100
    low = int(scaled)
    high = min(len(points) - 1, low + 1)
    return points[low] + (points[high] - points[low]) * (scaled - low)


def make_request(query: str, mode: str) -> bytes:
    return (json.dumps({
        "version": 1, "id": "bench", "command": "search",
        "payload": {"query": query, "mode": mode, "scope": "LOCAL_ONLY",
                    "limit": 10, "cursor": None, "hard_filters": {
                        "eligibility": ["unknown"], "facets": [],
                        "review_state": ["discovered", "abstract-screened",
                                         "fulltext-indexed", "manually-verified"],
                        "exclude_paper_ids": [],
                    }},
    }) + "\n").encode("utf-8")


def check_response(raw: bytes) -> None:
    result = json.loads(raw)
    if not result["ok"]:
        raise RuntimeError("Search worker returned an error: " + result["error"]["code"])


SUITE_QUERIES = [
    ("exact_title", "Attention Is All You Need", "STRICT"),
    ("doi_identifier", "10.18653/v1/2026.acl-long.930", "STRICT"),
    ("arxiv_identifier", "1706.03762", "STRICT"),
    ("short_keyword", "federated", "STRICT"),
    ("multi_keyword", "federated continual learning intrusion detection", "STRICT"),
    ("vietnamese_query", "học máy phân tán", "STRICT"),
    ("natural_language", "mitigate catastrophic forgetting in decentralized systems", "STRICT"),
    ("no_match_empty", "xyznonexistentquery987654321", "STRICT"),
    ("broad_hybrid_semantic", "transformer attention mechanisms", "BROAD"),
    ("repeated_identical", "attention", "STRICT"),
]


def run_benchmark(db: Path, query: str, mode: str, iterations: int) -> dict:
    env = {**os.environ, "RESEARCHOS_DB_PATH": str(db.resolve())}
    payload = make_request(query, mode)
    command = [sys.executable, "-m", "backend.service"]
    cold: list[float] = []
    warm: list[float] = []

    for _ in range(iterations):
        start = time.perf_counter()
        response = subprocess.run(command, input=payload, capture_output=True,
                                  env=env, timeout=45, check=True)
        cold.append((time.perf_counter() - start) * 1000)
        check_response(response.stdout)

    process = subprocess.Popen(command, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=env, bufsize=0)
    try:
        assert process.stdin is not None and process.stdout is not None
        for index in range(iterations + 2):
            start = time.perf_counter()
            process.stdin.write(payload)
            process.stdin.flush()
            readable, _, _ = select.select([process.stdout], [], [], 45)
            if not readable:
                raise TimeoutError("Persistent local worker did not respond in 45 seconds")
            check_response(process.stdout.readline())
            if index >= 2:  # Exclude initial worker warm-up.
                warm.append((time.perf_counter() - start) * 1000)
        process.stdin.close()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()

    cold_p50, warm_p50 = statistics.median(cold), statistics.median(warm)
    return {
        "sample_count": iterations, "query": query, "mode": mode,
        "cold_spawn": {"p50_ms": round(cold_p50, 2),
                       "p95_ms": round(percentile(cold, 95), 2)},
        "persistent": {"p50_ms": round(warm_p50, 2),
                       "p95_ms": round(percentile(warm, 95), 2)},
        "p50_speedup": round(cold_p50 / warm_p50, 2) if warm_p50 else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True, help="Existing catalog.sqlite3")
    parser.add_argument("--query", default="attention")
    parser.add_argument("--mode", choices=("STRICT", "BROAD"), default="STRICT")
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--suite", action="store_true", help="Run comprehensive query suite across all 10 categories")
    args = parser.parse_args()
    if not args.db.is_file():
        parser.error("Database must exist. Import your catalog before benchmarking.")
    if not 5 <= args.iterations <= 200:
        parser.error("iterations must be between 5 and 200")

    if args.suite:
        results = {}
        for category, q, m in SUITE_QUERIES:
            results[category] = run_benchmark(args.db, q, m, min(args.iterations, 10))
        all_warm_p50 = [r["persistent"]["p50_ms"] for r in results.values()]
        all_warm_p95 = [r["persistent"]["p95_ms"] for r in results.values()]
        report = {
            "suite_results": results,
            "overall_warm_p50_median": round(statistics.median(all_warm_p50), 2),
            "overall_warm_p95_max": round(max(all_warm_p95), 2),
            "note": "Host-specific offline measurements across representative query taxonomy",
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    result = run_benchmark(args.db, args.query, args.mode, args.iterations)
    result["note"] = "Host-specific offline measurements, not a retrieval relevance benchmark"
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

