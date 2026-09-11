import unittest
from unittest.mock import patch, MagicMock

from backend.core.analyzer import (
    _truncate,
    _format_file_tree,
    _format_dependencies,
    _format_code_samples,
    generate_summary,
    generate_architecture,
    generate_dependency_report,
    generate_security_scan,
    run_full_analysis,
)


SAMPLE_TREE = {
    "name": "my-repo",
    "type": "directory",
    "children": [
        {"name": "src", "type": "directory", "children": [
            {"name": "main.py", "type": "file", "path": "src/main.py"},
        ]},
        {"name": "README.md", "type": "file", "path": "README.md"},
    ],
}

SAMPLE_DEPS = [
    {
        "file": "requirements.txt",
        "ecosystem": "python",
        "dependencies": [
            {"name": "flask", "version": "==2.3.0"},
            {"name": "requests", "version": ">=2.28"},
        ],
    }
]

SAMPLE_CHUNKS = [
    {
        "text": "def hello():\n    return 'world'",
        "metadata": {"source": "main.py", "chunk_index": 0, "language": "python"},
    },
    {
        "text": "class App:\n    pass",
        "metadata": {"source": "app.py", "chunk_index": 0, "language": "python"},
    },
]


class TestHelpers(unittest.TestCase):
    def test_truncate_short(self):
        self.assertEqual(_truncate("hello", 100), "hello")

    def test_truncate_long(self):
        result = _truncate("a" * 200, 50)
        self.assertIn("(truncated)", result)
        self.assertTrue(len(result) < 200)

    def test_format_file_tree(self):
        result = _format_file_tree(SAMPLE_TREE)
        self.assertIn("my-repo/", result)
        self.assertIn("src/", result)
        self.assertIn("main.py", result)
        self.assertIn("README.md", result)

    def test_format_dependencies(self):
        result = _format_dependencies(SAMPLE_DEPS)
        self.assertIn("requirements.txt", result)
        self.assertIn("flask", result)
        self.assertIn("requests", result)

    def test_format_dependencies_empty(self):
        result = _format_dependencies([])
        self.assertEqual(result, "No dependency files found.")

    def test_format_code_samples(self):
        result = _format_code_samples(SAMPLE_CHUNKS)
        self.assertIn("main.py", result)
        self.assertIn("def hello", result)

    def test_format_code_samples_limit(self):
        result = _format_code_samples(SAMPLE_CHUNKS, max_chunks=1)
        self.assertIn("main.py", result)
        self.assertNotIn("app.py", result)


MOCK_RESPONSE = MagicMock()
MOCK_RESPONSE.content = "Mocked LLM analysis result."


class TestGenerators(unittest.TestCase):
    @patch("backend.core.analyzer._get_llm")
    def test_generate_summary(self, mock_llm_fn):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MOCK_RESPONSE
        mock_llm_fn.return_value = mock_llm

        result = generate_summary(SAMPLE_TREE, SAMPLE_DEPS, SAMPLE_CHUNKS)
        self.assertEqual(result, "Mocked LLM analysis result.")
        mock_llm.invoke.assert_called_once()

    @patch("backend.core.analyzer._get_llm")
    def test_generate_architecture(self, mock_llm_fn):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MOCK_RESPONSE
        mock_llm_fn.return_value = mock_llm

        result = generate_architecture(SAMPLE_TREE, SAMPLE_CHUNKS)
        self.assertEqual(result, "Mocked LLM analysis result.")

    @patch("backend.core.analyzer._get_llm")
    def test_generate_dependency_report(self, mock_llm_fn):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MOCK_RESPONSE
        mock_llm_fn.return_value = mock_llm

        result = generate_dependency_report(SAMPLE_DEPS)
        self.assertEqual(result, "Mocked LLM analysis result.")

    @patch("backend.core.analyzer._get_llm")
    def test_generate_security_scan(self, mock_llm_fn):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MOCK_RESPONSE
        mock_llm_fn.return_value = mock_llm

        result = generate_security_scan(SAMPLE_CHUNKS, SAMPLE_DEPS)
        self.assertEqual(result, "Mocked LLM analysis result.")

    @patch("backend.core.analyzer._get_llm")
    def test_run_full_analysis(self, mock_llm_fn):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MOCK_RESPONSE
        mock_llm_fn.return_value = mock_llm

        result = run_full_analysis(SAMPLE_TREE, SAMPLE_DEPS, SAMPLE_CHUNKS)
        self.assertIn("summary", result)
        self.assertIn("architecture", result)
        self.assertIn("dependency_report", result)
        self.assertIn("security_scan", result)
        self.assertEqual(mock_llm.invoke.call_count, 4)


class TestLLMNotConfigured(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key_raises(self):
        with self.assertRaises(RuntimeError):
            generate_summary(SAMPLE_TREE, SAMPLE_DEPS, SAMPLE_CHUNKS)


if __name__ == "__main__":
    unittest.main()
