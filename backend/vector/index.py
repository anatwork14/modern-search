"""Atomic, versioned exact-cosine index for the small local MVP corpus."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Callable

from backend.embeddings import encode_query, encode_titled_documents
from .manifest import IndexMismatchError, assert_compatible, make_index_manifest


def corpus_revision(papers: list[dict], tags: list[dict]) -> str:
    content = {'papers': sorted(papers, key=lambda p: p['paper_id']),
               'tags': sorted(tags, key=lambda t: t['tag_id'])}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def _validate_vector(vector):
    if not isinstance(vector, list) or len(vector) != 768:
        raise IndexMismatchError('Dense vector dimension mismatch')
    if any(type(v) not in (float, int) or not math.isfinite(v) for v in vector):
        raise IndexMismatchError('Dense vector contains invalid values')
    if abs(math.sqrt(sum(v * v for v in vector)) - 1.0) > 1e-3:
        raise IndexMismatchError('Dense vector normalization mismatch')


def build_index(path: Path, papers: list[dict], tags: list[dict],
                encoder: Callable = encode_titled_documents) -> dict:
    rows = sorted(papers, key=lambda p: p['paper_id'])
    ids = [p['paper_id'] for p in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate paper IDs')
    vectors = []
    for offset in range(0, len(rows), 16):
        batch = rows[offset:offset + 16]
        encoded = encoder([{'title': p['title'], 'text': p.get('abstract') or ''} for p in batch])
        if len(encoded) != len(batch):
            raise IndexMismatchError('Dense encoder row count mismatch')
        for vector in encoded:
            _validate_vector(vector)
        vectors.extend(encoded)
    manifest = make_index_manifest(corpus_revision=corpus_revision(papers, tags))
    data = {'manifest': manifest, 'paper_ids': ids, 'vectors': vectors,
            'content_policy': 'title-and-source-abstract-v1'}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.dense-', delete=False) as stream:
            temporary = stream.name
            json.dump(data, stream, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)
    return {'paper_count': len(ids), 'manifest': manifest, 'bytes': path.stat().st_size}


class DenseIndex:
    def __init__(self, path: Path, papers: list[dict], tags: list[dict],
                 query_encoder: Callable = encode_query):
        path = Path(path)
        if path.stat().st_size > 256 * 1024 * 1024:
            raise IndexMismatchError('Dense index exceeds MVP resource limit')
        with path.open() as stream:
            data = json.load(stream)
        assert_compatible(data['manifest'], expected_corpus_revision=corpus_revision(papers, tags))
        self.ids, self.vectors = data['paper_ids'], data['vectors']
        if data.get('content_policy') != 'title-and-source-abstract-v1':
            raise IndexMismatchError('Dense content policy mismatch')
        if self.ids != sorted(p['paper_id'] for p in papers) or len(self.vectors) != len(self.ids):
            raise IndexMismatchError('Dense index paper identity mismatch')
        for vector in self.vectors:
            _validate_vector(vector)
        self.query_encoder = query_encoder

    def __call__(self, query: str) -> list[str]:
        vector = self.query_encoder(query)
        _validate_vector(vector)
        scored = [(sum(a * b for a, b in zip(vector, row)), pid)
                  for pid, row in zip(self.ids, self.vectors)]
        # Scan the complete small corpus so downstream strict filters cannot lose
        # candidates through a pre-filter top-K cutoff. No relevance guarantee.
        return [pid for _, pid in sorted(scored, key=lambda pair: (-pair[0], pair[1]))]
