import json
from pathlib import Path
import tempfile
import unittest

from backend.vector import IndexMismatchError
from backend.vector.index import DenseIndex, build_index


class IndexTests(unittest.TestCase):
    def test_atomic_build_roundtrip_and_corpus_mismatch(self):
        papers = [{'paper_id':'P','title':'Synthetic','abstract':None}]
        vector = [1.0] + [0.0] * 767
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'index.json'
            build_index(path, papers, [], encoder=lambda docs: [vector for _ in docs])
            index = DenseIndex(path, papers, [], query_encoder=lambda q: vector)
            self.assertEqual(index('query'), ['P'])
            with self.assertRaises(IndexMismatchError):
                DenseIndex(path, [{'paper_id':'P','title':'Changed'}], [])
            before = path.read_bytes()
            with self.assertRaises(IndexMismatchError):
                build_index(path, papers, [], encoder=lambda docs: [[0.0] * 768])
            self.assertEqual(path.read_bytes(), before)
            data = json.loads(before)
            data['vectors'][0][0] = float('nan')
            path.write_text(json.dumps(data))
            with self.assertRaises(IndexMismatchError):
                DenseIndex(path, papers, [])
