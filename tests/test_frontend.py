import unittest
from unittest.mock import patch, MagicMock

from frontend.app import call_clone, call_run_analysis, call_chat, call_onboarding, render_file_tree, _extract_repo_name


MOCK_TREE = {
    "name": "repo",
    "type": "directory",
    "children": [
        {
            "name": "src",
            "type": "directory",
            "children": [
                {"name": "main.py", "type": "file", "path": "src/main.py"},
            ],
        },
        {"name": "README.md", "type": "file", "path": "README.md"},
    ],
}


class TestRenderFileTree(unittest.TestCase):
    def test_root_node(self):
        result = render_file_tree(MOCK_TREE)
        self.assertIn("repo", result)

    def test_contains_directory(self):
        result = render_file_tree(MOCK_TREE)
        self.assertIn("src", result)

    def test_contains_files(self):
        result = render_file_tree(MOCK_TREE)
        self.assertIn("main.py", result)
        self.assertIn("README.md", result)

    def test_single_file_node(self):
        node = {"name": "index.js", "type": "file", "path": "index.js"}
        result = render_file_tree(node)
        self.assertIn("index.js", result)

    def test_empty_directory(self):
        node = {"name": "empty", "type": "directory", "children": []}
        result = render_file_tree(node)
        self.assertIn("empty", result)


class TestExtractRepoName(unittest.TestCase):
    def test_basic_url(self):
        self.assertEqual(_extract_repo_name("https://github.com/user/my-repo"), "my-repo")

    def test_trailing_slash(self):
        self.assertEqual(_extract_repo_name("https://github.com/user/my-repo/"), "my-repo")

    def test_git_suffix(self):
        self.assertEqual(_extract_repo_name("https://github.com/user/my-repo.git"), "my-repo")


class TestCallClone(unittest.TestCase):
    @patch("frontend.app.requests.post")
    def test_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "session_id": "abc123",
            "file_tree": MOCK_TREE,
            "stats": {"files": 2, "chunks": 1, "dependencies": 1},
            "cached": False,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = call_clone("https://github.com/user/repo")
        self.assertEqual(result["session_id"], "abc123")
        self.assertFalse(result["cached"])
        args, kwargs = mock_post.call_args
        self.assertIn("/api/clone", args[0])

    @patch("frontend.app.requests.post")
    def test_http_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("500 Server Error")
        mock_post.return_value = mock_resp

        with self.assertRaises(Exception):
            call_clone("https://github.com/user/repo")


class TestCallRunAnalysis(unittest.TestCase):
    @patch("frontend.app.requests.post")
    def test_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "session_id": "abc123",
            "summary": "A project.",
            "architecture": "Monolith.",
            "dependency_report": "Uses Flask.",
            "security_scan": "Clean.",
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = call_run_analysis("abc123")
        self.assertEqual(result["summary"], "A project.")
        args, kwargs = mock_post.call_args
        self.assertIn("/api/run-analysis", args[0])
        self.assertEqual(kwargs["json"]["session_id"], "abc123")


class TestCallChat(unittest.TestCase):
    @patch("frontend.app.requests.post")
    def test_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "session_id": "abc123",
            "question": "What does this do?",
            "answer": "It does X.",
            "sources": [{"file": "main.py", "distance": 0.1}],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = call_chat("abc123", "What does this do?")
        self.assertEqual(result["answer"], "It does X.")
        args, kwargs = mock_post.call_args
        self.assertIn("/api/chat", args[0])
        self.assertEqual(kwargs["json"]["session_id"], "abc123")
        self.assertEqual(kwargs["json"]["question"], "What does this do?")


class TestCallOnboarding(unittest.TestCase):
    @patch("frontend.app.requests.post")
    def test_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "session_id": "abc123",
            "onboarding_guide": "# Welcome\nSetup guide here.",
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = call_onboarding("abc123")
        self.assertIn("Welcome", result["onboarding_guide"])
        args, kwargs = mock_post.call_args
        self.assertIn("/api/onboarding", args[0])
        self.assertEqual(kwargs["json"]["session_id"], "abc123")


if __name__ == "__main__":
    unittest.main()
