import unittest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from backend.api.main import app, sessions, analysis_cache


client = TestClient(app)

MOCK_FILE_TREE = {
    "name": "repo",
    "type": "directory",
    "children": [
        {"name": "main.py", "type": "file", "path": "main.py"},
    ],
}

MOCK_DEPS = [
    {
        "file": "requirements.txt",
        "ecosystem": "python",
        "dependencies": [{"name": "flask", "version": "==2.3.0"}],
    }
]

MOCK_CHUNKS = [
    {
        "text": "def hello():\n    return 'world'",
        "metadata": {"source": "main.py", "chunk_index": 0, "language": "python"},
    },
]

MOCK_ANALYSIS = {
    "summary": "A test project.",
    "architecture": "Simple monolith.",
    "dependency_report": "Uses Flask.",
    "security_scan": "No issues found.",
}

MOCK_QUERY_RESULTS = [
    {
        "text": "def hello():\n    return 'world'",
        "metadata": {"source": "main.py", "chunk_index": 0, "language": "python"},
        "distance": 0.12,
    },
]


class TestAnalyzeEndpoint(unittest.TestCase):
    def setUp(self):
        sessions.clear()
        analysis_cache.clear()

    @patch("backend.api.main.cleanup_repository")
    @patch("backend.api.main.run_full_analysis", return_value=MOCK_ANALYSIS)
    @patch("backend.api.main.build_vector_store", return_value="repolens_abc")
    @patch("backend.api.main.get_code_chunks", return_value=MOCK_CHUNKS)
    @patch("backend.api.main.parse_dependencies", return_value=MOCK_DEPS)
    @patch("backend.api.main.get_file_tree", return_value=MOCK_FILE_TREE)
    @patch("backend.api.main.clone_repository", return_value="/tmp/fake_repo")
    def test_analyze_success(self, mock_clone, mock_tree, mock_deps,
                             mock_chunks, mock_vs, mock_analysis, mock_cleanup):
        response = client.post(
            "/api/analyze",
            json={"repo_url": "https://github.com/user/repo"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("session_id", data)
        self.assertEqual(data["summary"], "A test project.")
        self.assertEqual(data["architecture"], "Simple monolith.")
        self.assertIn("file_tree", data)
        mock_clone.assert_called_once()
        mock_cleanup.assert_called_once_with("/tmp/fake_repo")

    @patch("backend.api.main.cleanup_repository")
    @patch("backend.api.main.clone_repository", side_effect=Exception("clone failed"))
    def test_analyze_clone_failure(self, mock_clone, mock_cleanup):
        response = client.post(
            "/api/analyze",
            json={"repo_url": "https://github.com/user/repo"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("clone failed", response.json()["detail"])

    def test_analyze_invalid_url(self):
        response = client.post(
            "/api/analyze",
            json={"repo_url": "not-a-url"},
        )
        self.assertEqual(response.status_code, 422)


class TestChatEndpoint(unittest.TestCase):
    def setUp(self):
        sessions.clear()
        sessions["test-session"] = {
            "repo_url": "https://github.com/user/repo",
            "file_tree": MOCK_FILE_TREE,
            "dependencies": MOCK_DEPS,
            "code_chunks": MOCK_CHUNKS,
        }

    def test_chat_session_not_found(self):
        response = client.post(
            "/api/chat",
            json={"session_id": "nonexistent", "question": "What does this do?"},
        )
        self.assertEqual(response.status_code, 404)

    @patch("backend.api.main.generate_chat_answer", return_value="It returns 'world'.")
    @patch("backend.api.main.query_vector_store", return_value=MOCK_QUERY_RESULTS)
    def test_chat_success(self, mock_query, mock_answer):
        response = client.post(
            "/api/chat",
            json={"session_id": "test-session", "question": "What does hello do?"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["answer"], "It returns 'world'.")
        self.assertEqual(data["session_id"], "test-session")
        self.assertEqual(len(data["sources"]), 1)
        self.assertEqual(data["sources"][0]["file"], "main.py")
        mock_query.assert_called_once_with("test-session", "What does hello do?", n_results=5)

    def test_chat_missing_question(self):
        response = client.post(
            "/api/chat",
            json={"session_id": "test-session"},
        )
        self.assertEqual(response.status_code, 422)


class TestOnboardingEndpoint(unittest.TestCase):
    def setUp(self):
        sessions.clear()
        sessions["test-session"] = {
            "repo_url": "https://github.com/user/repo",
            "file_tree": MOCK_FILE_TREE,
            "dependencies": MOCK_DEPS,
            "code_chunks": MOCK_CHUNKS,
        }

    def test_onboarding_session_not_found(self):
        response = client.post(
            "/api/onboarding",
            json={"session_id": "nonexistent"},
        )
        self.assertEqual(response.status_code, 404)

    @patch("backend.api.main.generate_onboarding", return_value="# Onboarding Guide\nWelcome!")
    def test_onboarding_success(self, mock_onboard):
        response = client.post(
            "/api/onboarding",
            json={"session_id": "test-session"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("Onboarding Guide", data["onboarding_guide"])
        self.assertEqual(data["session_id"], "test-session")
        mock_onboard.assert_called_once_with(
            MOCK_FILE_TREE, MOCK_DEPS, MOCK_CHUNKS,
        )


class TestAnalyzerNewFunctions(unittest.TestCase):
    @patch("backend.core.analyzer._get_llm")
    def test_generate_chat_answer(self, mock_llm_fn):
        from backend.core.analyzer import generate_chat_answer

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "The hello function returns 'world'."
        mock_llm.invoke.return_value = mock_response
        mock_llm_fn.return_value = mock_llm

        result = generate_chat_answer("What does hello do?", MOCK_CHUNKS)
        self.assertEqual(result, "The hello function returns 'world'.")
        mock_llm.invoke.assert_called_once()

    @patch("backend.core.analyzer._get_llm")
    def test_generate_onboarding(self, mock_llm_fn):
        from backend.core.analyzer import generate_onboarding

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "# Onboarding\nSetup instructions here."
        mock_llm.invoke.return_value = mock_response
        mock_llm_fn.return_value = mock_llm

        result = generate_onboarding(MOCK_FILE_TREE, MOCK_DEPS, MOCK_CHUNKS)
        self.assertIn("Onboarding", result)
        mock_llm.invoke.assert_called_once()


if __name__ == "__main__":
    unittest.main()
