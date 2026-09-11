import json
import os
import re

from langchain.text_splitter import RecursiveCharacterTextSplitter, Language

from backend.core.git_loader import get_all_file_paths

DEPENDENCY_FILES = {
    "requirements.txt": "python",
    "Pipfile": "python",
    "setup.py": "python",
    "setup.cfg": "python",
    "pyproject.toml": "python",
    "package.json": "javascript",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "Gemfile": "ruby",
    "pom.xml": "java",
    "build.gradle": "java",
    "composer.json": "php",
}

EXTENSION_TO_LANGUAGE = {
    ".py": Language.PYTHON,
    ".js": Language.JS,
    ".jsx": Language.JS,
    ".ts": Language.TS,
    ".tsx": Language.TS,
    ".java": Language.JAVA,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".rb": Language.RUBY,
    ".php": Language.PHP,
    ".scala": Language.SCALA,
    ".swift": Language.SWIFT,
    ".md": Language.MARKDOWN,
    ".html": Language.HTML,
    ".sol": Language.SOL,
}

MAX_FILE_SIZE = 100_000  # skip files larger than 100KB


def detect_dependency_files(repo_path: str) -> list[dict]:
    """Find all dependency/manifest files in the repository."""
    found = []
    for dirpath, _, filenames in os.walk(repo_path):
        for filename in filenames:
            if filename in DEPENDENCY_FILES:
                abs_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(abs_path, repo_path)
                found.append({
                    "file": rel_path,
                    "ecosystem": DEPENDENCY_FILES[filename],
                    "abs_path": abs_path,
                })
    return found


def parse_dependencies(repo_path: str) -> list[dict]:
    """Extract dependencies from all detected manifest files."""
    dep_files = detect_dependency_files(repo_path)
    results = []

    for dep_file in dep_files:
        filename = os.path.basename(dep_file["file"])
        abs_path = dep_file["abs_path"]
        ecosystem = dep_file["ecosystem"]

        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            continue

        deps = []
        if filename == "requirements.txt":
            deps = _parse_requirements_txt(content)
        elif filename == "package.json":
            deps = _parse_package_json(content)
        elif filename == "go.mod":
            deps = _parse_go_mod(content)
        elif filename == "Cargo.toml":
            deps = _parse_cargo_toml(content)
        elif filename == "Gemfile":
            deps = _parse_gemfile(content)
        elif filename in ("pyproject.toml", "setup.cfg", "Pipfile"):
            deps = _parse_generic_python(content)

        results.append({
            "file": dep_file["file"],
            "ecosystem": ecosystem,
            "dependencies": deps,
        })

    return results


def _parse_requirements_txt(content: str) -> list[dict]:
    deps = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*([><=!~]+.+)?", line)
        if match:
            deps.append({
                "name": match.group(1),
                "version": (match.group(2) or "").strip(),
            })
    return deps


def _parse_package_json(content: str) -> list[dict]:
    deps = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return deps
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        for name, version in data.get(section, {}).items():
            deps.append({"name": name, "version": version})
    return deps


def _parse_go_mod(content: str) -> list[dict]:
    deps = []
    in_require = False
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("require ("):
            in_require = True
            continue
        if in_require and line == ")":
            in_require = False
            continue
        if in_require:
            parts = line.split()
            if len(parts) >= 2:
                deps.append({"name": parts[0], "version": parts[1]})
        elif line.startswith("require "):
            parts = line.replace("require ", "").split()
            if len(parts) >= 2:
                deps.append({"name": parts[0], "version": parts[1]})
    return deps


def _parse_cargo_toml(content: str) -> list[dict]:
    deps = []
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if re.match(r"^\[.*dependencies.*\]", stripped):
            in_deps = True
            continue
        if stripped.startswith("[") and in_deps:
            in_deps = False
            continue
        if in_deps and "=" in stripped:
            name = stripped.split("=")[0].strip()
            version_part = stripped.split("=", 1)[1].strip().strip('"').strip("'")
            deps.append({"name": name, "version": version_part})
    return deps


def _parse_gemfile(content: str) -> list[dict]:
    deps = []
    for line in content.splitlines():
        match = re.match(r"""^\s*gem\s+['"]([^'"]+)['"](?:\s*,\s*['"]([^'"]+)['"])?""", line)
        if match:
            deps.append({
                "name": match.group(1),
                "version": match.group(2) or "",
            })
    return deps


def _parse_generic_python(content: str) -> list[dict]:
    """Best-effort extraction from pyproject.toml, setup.cfg, or Pipfile."""
    deps = []
    for line in content.splitlines():
        match = re.match(r"""^\s*['"]?([A-Za-z0-9_.-]+)['"]?\s*[=><~!]""", line)
        if match:
            name = match.group(1)
            if name and not name.startswith("[") and name not in ("python", "name", "version"):
                deps.append({"name": name, "version": ""})
    return deps


def get_code_chunks(repo_path: str) -> list[dict]:
    """Read all code files and split them into semantic chunks with metadata."""
    file_paths = get_all_file_paths(repo_path)
    chunks = []

    for rel_path in file_paths:
        abs_path = os.path.join(repo_path, rel_path)

        try:
            size = os.path.getsize(abs_path)
            if size > MAX_FILE_SIZE or size == 0:
                continue
        except OSError:
            continue

        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            continue

        if not content.strip():
            continue

        _, ext = os.path.splitext(rel_path)
        language = EXTENSION_TO_LANGUAGE.get(ext.lower())

        if language:
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=language,
                chunk_size=1500,
                chunk_overlap=200,
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1500,
                chunk_overlap=200,
            )

        split_texts = splitter.split_text(content)

        for i, text in enumerate(split_texts):
            chunks.append({
                "text": text,
                "metadata": {
                    "source": rel_path,
                    "chunk_index": i,
                    "language": language.value if language else "text",
                },
            })

    return chunks
