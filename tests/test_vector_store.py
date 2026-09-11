import os
import shutil
import tempfile
import unittest

from backend.core.vector_store import (
    _collection_name,
    build_vector_store,
    delete_collection,
    get_chroma_client,
    get_embeddings,
    query_vector_store,
)


class TestCollectionNaming(unittest.TestCase):
    def test_deterministic(self):
        name1 = _collection_name("session-abc")
        name2 = _collection_name("session-abc")
        self.assertEqual(name1, name2)

    def test_different_sessions_differ(self):
        name1 = _collection_name("session-abc")
        name2 = _collection_name("session-xyz")
        self.assertNotEqual(name1, name2)

    def test_valid_collection_name(self):
        name = _collection_name("session-abc")
        self.assertTrue(name.startswith("repolens_"))
        self.assertLessEqual(len(name), 63)


SAMPLE_CHUNKS = [
    {
        "text": "def hello():\n    return 'Hello, world!'",
        "metadata": {"source": "main.py", "chunk_index": 0, "language": "python"},
    },
    {
        "text": "def add(a, b):\n    return a + b",
        "metadata": {"source": "math_utils.py", "chunk_index": 0, "language": "python"},
    },
    {
        "text": "class UserModel:\n    def __init__(self, name):\n        self.name = name",
        "metadata": {"source": "models.py", "chunk_index": 0, "language": "python"},
    },
]


class TestBuildAndQuery(unittest.TestCase):
    session_id = "test-session-001"

    @classmethod
    def setUpClass(cls):
        build_vector_store(cls.session_id, SAMPLE_CHUNKS)

    @classmethod
    def tearDownClass(cls):
        delete_collection(cls.session_id)

    def test_query_returns_results(self):
        results = query_vector_store(self.session_id, "greeting function")
        self.assertGreater(len(results), 0)

    def test_result_structure(self):
        results = query_vector_store(self.session_id, "add numbers", n_results=1)
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertIn("text", result)
        self.assertIn("metadata", result)
        self.assertIn("distance", result)

    def test_relevance_ranking(self):
        results = query_vector_store(self.session_id, "addition math", n_results=3)
        top_source = results[0]["metadata"]["source"]
        self.assertEqual(top_source, "math_utils.py")

    def test_n_results_capped(self):
        results = query_vector_store(self.session_id, "code", n_results=100)
        self.assertLessEqual(len(results), len(SAMPLE_CHUNKS))


class TestBuildEdgeCases(unittest.TestCase):
    def test_empty_chunks_raises(self):
        with self.assertRaises(ValueError):
            build_vector_store("empty-session", [])

    def test_rebuild_replaces_collection(self):
        sid = "rebuild-test"
        build_vector_store(sid, SAMPLE_CHUNKS[:1])
        build_vector_store(sid, SAMPLE_CHUNKS)
        results = query_vector_store(sid, "user model", n_results=10)
        self.assertEqual(len(results), len(SAMPLE_CHUNKS))
        delete_collection(sid)


if __name__ == "__main__":
    unittest.main()
