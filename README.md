# RepoLens — AI GitHub Repository Analyst

RepoLens is an AI-powered developer tool that clones a public GitHub repository, analyzes its codebase, and provides an interactive Q&A interface along with an automated developer onboarding guide. Understand any unfamiliar codebase in minutes instead of days.

## Features

- **Repository Ingestion** — Input a public GitHub URL; the system clones it, analyzes it, and cleans up after processing.
- **Automated Codebase Summary & Architecture Analysis** — Explains what the project does, maps the folder structure, and identifies core architectural patterns.
- **Tech Stack & Dependency Scanner** — Extracts `package.json`, `requirements.txt`, `Cargo.toml`, etc., listing frameworks and third-party services.
- **Code Quality & Security Scan** — Scans for hardcoded secrets, outdated/vulnerable dependencies, and basic anti-patterns.
- **Interactive Repository Q&A** — Chat interface to ask questions about authentication, database connections, function logic, and impact analysis.
- **Developer Onboarding Guide Generator** — Auto-generates a Markdown document covering setup, environment variables, running tests, and project layout.

## Tech Stack

| Layer              | Technology                                      |
| ------------------ | ----------------------------------------------- |
| Backend            | FastAPI (Python)                                |
| Frontend           | Streamlit (Python)                              |
| AI / Orchestration | LangChain + Hugging Face Embeddings + Groq API  |
| Embeddings Model   | `sentence-transformers/all-MiniLM-L6-v2`        |
| LLM                | Llama 3 (via Groq)                              |
| Vector Store       | ChromaDB (embedded local)                       |
| Git Operations     | GitPython                                       |

## Project Structure

```
repolens/
├── backend/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── git_loader.py       # Cloning and file tree traversal
│   │   ├── parser.py           # Dependency and code chunking logic
│   │   ├── vector_store.py     # ChromaDB / embedding setup
│   │   └── analyzer.py         # LLM prompts for summary, architecture, security
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py             # FastAPI application and routes
│   └── requirements.txt
├── frontend/
│   ├── app.py                  # Streamlit UI
│   └── requirements.txt
├── tests/
│   └── test_parser.py
├── .env.example
├── README.md
└── prd.md
```

## Prerequisites

- Python 3.10+
- Git
- A [Groq API key](https://console.groq.com/)

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/repo-lens.git
   cd repo-lens
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate   # macOS/Linux
   venv\Scripts\activate      # Windows
   ```

3. **Install backend dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Install frontend dependencies:**
   ```bash
   pip install -r frontend/requirements.txt
   ```

5. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your Groq API key.

## Running the Application

### Start the Backend

```bash
uvicorn backend.api.main:app --reload --port 8000
```

### Start the Frontend

```bash
streamlit run frontend/app.py
```

Open your browser to `http://localhost:8501` to use the application.

## API Endpoints

| Method | Endpoint          | Description                                                  |
| ------ | ----------------- | ------------------------------------------------------------ |
| POST   | `/api/analyze`    | Accepts `{ "repo_url": "..." }`, clones the repo, runs all scans, and returns the summary. |
| POST   | `/api/chat`       | Accepts `{ "session_id": "...", "question": "..." }`, queries the vector store and returns an LLM answer. |
| POST   | `/api/onboarding` | Generates and returns the developer onboarding Markdown guide. |

### Example: Analyze a Repository

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/fastapi/fastapi"}'
```

### Example: Ask a Question

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123", "question": "How does authentication work?"}'
```

## How It Works

1. **Clone** — The user provides a GitHub URL. RepoLens clones the repository into a temporary directory.
2. **Parse** — The codebase is traversed, dependency files are extracted, and source files are split into semantic chunks.
3. **Embed** — Code chunks are embedded using `all-MiniLM-L6-v2` and stored in a ChromaDB collection.
4. **Analyze** — LLM prompts (via Groq/Llama 3) generate a project summary, architecture overview, dependency report, and security scan.
5. **Query** — Users ask questions through the chat interface; a RAG pipeline retrieves relevant chunks and generates answers.
6. **Onboard** — A complete developer onboarding guide is auto-generated as Markdown.

## License

MIT
