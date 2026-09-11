import os
import shutil
import tempfile

from git import Repo

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "target",
    ".idea",
    ".vscode",
    ".gradle",
    ".settings",
    "vendor",
    "Pods",
    ".eggs",
    "*.egg-info",
    "coverage",
    ".coverage",
    "htmlcov",
    ".terraform",
}

IGNORED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".wav",
    ".zip", ".tar", ".gz", ".bz2", ".rar", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pyc", ".pyo", ".class", ".o", ".obj",
    ".lock",
}


def clone_repository(repo_url: str) -> str:
    """Clone a public GitHub repository into a temporary directory."""
    tmp_dir = tempfile.mkdtemp(prefix="repolens_")
    Repo.clone_from(repo_url, tmp_dir, depth=1)
    return tmp_dir


def cleanup_repository(repo_path: str) -> None:
    """Remove the cloned repository directory."""
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path, ignore_errors=True)


def _should_ignore_dir(dirname: str) -> bool:
    return dirname in IGNORED_DIRS or dirname.endswith(".egg-info")


def get_file_tree(repo_path: str) -> dict:
    """Recursively traverse the repository and return a nested dict of the file tree.

    Returns a structure like:
    {
        "name": "repo-root",
        "type": "directory",
        "children": [
            {"name": "src", "type": "directory", "children": [...]},
            {"name": "README.md", "type": "file", "path": "README.md"},
        ]
    }
    """
    root_name = os.path.basename(repo_path) or "repo"
    return _build_tree(repo_path, root_name, "")


def _build_tree(abs_path: str, name: str, rel_path: str) -> dict:
    node = {"name": name, "type": "directory", "children": []}

    try:
        entries = sorted(os.listdir(abs_path))
    except PermissionError:
        return node

    for entry in entries:
        entry_abs = os.path.join(abs_path, entry)
        entry_rel = os.path.join(rel_path, entry) if rel_path else entry

        if os.path.isdir(entry_abs):
            if _should_ignore_dir(entry):
                continue
            child = _build_tree(entry_abs, entry, entry_rel)
            node["children"].append(child)
        elif os.path.isfile(entry_abs):
            _, ext = os.path.splitext(entry)
            if ext.lower() in IGNORED_EXTENSIONS:
                continue
            node["children"].append({
                "name": entry,
                "type": "file",
                "path": entry_rel,
            })

    return node


def get_all_file_paths(repo_path: str) -> list[str]:
    """Return a flat list of relative paths for all non-ignored files."""
    paths = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [
            d for d in dirnames if not _should_ignore_dir(d)
        ]
        for filename in filenames:
            _, ext = os.path.splitext(filename)
            if ext.lower() in IGNORED_EXTENSIONS:
                continue
            abs_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(abs_path, repo_path)
            paths.append(rel_path)
    return sorted(paths)
