import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

GROQ_MODEL = "qwen/qwen3.8-27b"


def _get_llm() -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set in environment")
    return ChatGroq(
        model=GROQ_MODEL,
        api_key=api_key,
        temperature=0.2,
        max_tokens=950,
    )


def _truncate(text: str, max_chars: int = 12000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... (truncated)"


def _format_file_tree(tree: dict, indent: int = 0) -> str:
    lines = []
    prefix = "  " * indent
    if tree["type"] == "directory":
        lines.append(f"{prefix}{tree['name']}/")
        for child in tree.get("children", []):
            lines.extend(_format_file_tree(child, indent + 1).splitlines())
    else:
        lines.append(f"{prefix}{tree['name']}")
    return "\n".join(lines)


def _format_dependencies(deps: list[dict]) -> str:
    lines = []
    for dep_file in deps:
        lines.append(f"\n### {dep_file['file']} ({dep_file['ecosystem']})")
        for d in dep_file["dependencies"]:
            version = d.get("version", "")
            lines.append(f"  - {d['name']} {version}".rstrip())
    return "\n".join(lines) if lines else "No dependency files found."


def _format_code_samples(chunks: list[dict], max_chunks: int = 30) -> str:
    selected = chunks[:max_chunks]
    parts = []
    for chunk in selected:
        source = chunk["metadata"]["source"]
        parts.append(f"--- {source} ---\n{chunk['text']}")
    return "\n\n".join(parts)


def generate_summary(
    file_tree: dict,
    dependencies: list[dict],
    code_chunks: list[dict],
) -> str:
    llm = _get_llm()
    tree_str = _truncate(_format_file_tree(file_tree), 4000)
    deps_str = _truncate(_format_dependencies(dependencies), 3000)
    code_str = _truncate(_format_code_samples(code_chunks), 6000)

    response = llm.invoke([
        SystemMessage(content=(
            "You are an expert software analyst. Given a repository's file tree, "
            "dependencies, and code samples, provide a concise project summary. "
            "Cover: what the project does, its main purpose, the primary programming "
            "language(s), and the target audience. Keep it under 300 words."
        )),
        HumanMessage(content=(
            f"## File Tree\n{tree_str}\n\n"
            f"## Dependencies\n{deps_str}\n\n"
            f"## Code Samples\n{code_str}"
        )),
    ])
    return response.content


def generate_architecture(
    file_tree: dict,
    code_chunks: list[dict],
) -> str:
    llm = _get_llm()
    tree_str = _truncate(_format_file_tree(file_tree), 4000)
    code_str = _truncate(_format_code_samples(code_chunks), 8000)

    response = llm.invoke([
        SystemMessage(content=(
            "You are a senior software architect. Analyze the repository structure "
            "and code to identify architectural patterns. Cover:\n"
            "1. Overall architecture style (monolith, microservices, MVC, etc.)\n"
            "2. Key modules/components and their responsibilities\n"
            "3. Data flow between components\n"
            "4. Design patterns observed\n"
            "5. Entry points (main files, API routes, CLI commands)\n"
            "Format as structured Markdown. Be specific, reference actual file paths."
        )),
        HumanMessage(content=(
            f"## File Tree\n{tree_str}\n\n"
            f"## Code Samples\n{code_str}"
        )),
    ])
    return response.content


def generate_dependency_report(dependencies: list[dict]) -> str:
    llm = _get_llm()
    deps_str = _format_dependencies(dependencies)

    response = llm.invoke([
        SystemMessage(content=(
            "You are a dependency analysis expert. Given a project's dependency list, "
            "produce a report covering:\n"
            "1. **Tech stack summary**: frameworks, libraries, and their roles\n"
            "2. **Ecosystem breakdown**: group by category (web framework, database, "
            "testing, DevOps, etc.)\n"
            "3. **Notable observations**: unusual combinations, potential version "
            "conflicts, or heavy dependencies worth noting\n"
            "Format as structured Markdown."
        )),
        HumanMessage(content=f"## Project Dependencies\n{deps_str}"),
    ])
    return response.content


SECURITY_PROMPT = (
    "You are a security auditor reviewing a codebase. Scan the code and "
    "dependencies for potential security issues. Check for:\n"
    "1. **Hardcoded secrets**: API keys, passwords, tokens in source code\n"
    "2. **SQL injection**: raw string queries without parameterization\n"
    "3. **Command injection**: unsanitized input passed to os.system or subprocess\n"
    "4. **XSS vulnerabilities**: unescaped user input rendered in HTML\n"
    "5. **Insecure dependencies**: known vulnerable library versions\n"
    "6. **Anti-patterns**: broad exception catching, debug mode in production, "
    "missing input validation\n\n"
    "For each issue found, state: severity (HIGH/MEDIUM/LOW), file path, "
    "the problem, and a recommended fix. If no issues are found in a category, "
    "say so. Format as structured Markdown."
)


def generate_security_scan(
    code_chunks: list[dict],
    dependencies: list[dict],
) -> str:
    llm = _get_llm()
    code_str = _truncate(_format_code_samples(code_chunks, max_chunks=40), 10000)
    deps_str = _truncate(_format_dependencies(dependencies), 3000)

    response = llm.invoke([
        SystemMessage(content=SECURITY_PROMPT),
        HumanMessage(content=(
            f"## Code Samples\n{code_str}\n\n"
            f"## Dependencies\n{deps_str}"
        )),
    ])
    return response.content


def generate_chat_answer(question: str, context_chunks: list[dict]) -> str:
    llm = _get_llm()
    context_str = _truncate(_format_code_samples(context_chunks), 8000)

    response = llm.invoke([
        SystemMessage(content=(
            "You are a helpful assistant that answers questions about a codebase. "
            "Use the provided code context to give accurate, specific answers. "
            "Reference file paths when relevant. If the context doesn't contain "
            "enough information to answer fully, say so and provide your best "
            "assessment based on what's available."
        )),
        HumanMessage(content=(
            f"## Relevant Code Context\n{context_str}\n\n"
            f"## Question\n{question}"
        )),
    ])
    return response.content


ONBOARDING_PROMPT = (
    "You are a technical writer creating a developer onboarding guide. "
    "Given a repository's file tree, dependencies, and code samples, "
    "generate a comprehensive Markdown onboarding document covering:\n"
    "1. **Project Overview** — what the project does and who it's for\n"
    "2. **Prerequisites** — required tools, runtimes, and accounts\n"
    "3. **Setup Instructions** — step-by-step environment setup\n"
    "4. **Project Structure** — key directories and their purpose\n"
    "5. **Environment Variables** — list any .env or config values needed\n"
    "6. **Running the Application** — how to start, build, and serve\n"
    "7. **Running Tests** — test commands and frameworks used\n"
    "8. **Key Architectural Decisions** — patterns a new dev should know\n"
    "9. **Common Tasks** — adding a feature, fixing a bug, deploying\n\n"
    "Be specific and reference actual file paths from the repository. "
    "Format the output as a clean, well-structured Markdown document."
)


def generate_onboarding(
    file_tree: dict,
    dependencies: list[dict],
    code_chunks: list[dict],
) -> str:
    llm = _get_llm()
    tree_str = _truncate(_format_file_tree(file_tree), 4000)
    deps_str = _truncate(_format_dependencies(dependencies), 3000)
    code_str = _truncate(_format_code_samples(code_chunks), 6000)

    response = llm.invoke([
        SystemMessage(content=ONBOARDING_PROMPT),
        HumanMessage(content=(
            f"## File Tree\n{tree_str}\n\n"
            f"## Dependencies\n{deps_str}\n\n"
            f"## Code Samples\n{code_str}"
        )),
    ])
    return response.content


def run_full_analysis(
    file_tree: dict,
    dependencies: list[dict],
    code_chunks: list[dict],
) -> dict:
    return {
        "summary": generate_summary(file_tree, dependencies, code_chunks),
        "architecture": generate_architecture(file_tree, code_chunks),
        "dependency_report": generate_dependency_report(dependencies),
        "security_scan": generate_security_scan(code_chunks, dependencies),
    }