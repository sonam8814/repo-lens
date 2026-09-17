import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from groq import RateLimitError

from backend.core.git_loader import (
    clone_repository,
    cleanup_repository,
    get_file_tree,
)
from backend.core.parser import parse_dependencies, get_code_chunks
from backend.core.vector_store import (
    build_vector_store,
    query_vector_store,
    delete_collection,
)
from backend.core.analyzer import (
    run_full_analysis,
    generate_chat_answer,
    generate_onboarding,
)

logger = logging.getLogger(__name__)

sessions: dict[str, dict] = {}
analysis_cache: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for sid, data in sessions.items():
        try:
            delete_collection(sid)
        except Exception:
            pass
    sessions.clear()


app = FastAPI(
    title="RepoLens API",
    description="AI-powered GitHub repository analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    repo_url: HttpUrl


class AnalyzeResponse(BaseModel):
    session_id: str
    summary: str
    architecture: str
    dependency_report: str
    security_scan: str
    file_tree: dict
    cached: bool = False


class ChatRequest(BaseModel):
    session_id: str
    question: str


class ChatResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    sources: list[dict]


class OnboardingRequest(BaseModel):
    session_id: str


class OnboardingResponse(BaseModel):
    session_id: str
    onboarding_guide: str


class CloneResponse(BaseModel):
    session_id: str
    file_tree: dict
    stats: dict
    cached: bool = False
    analysis: Optional[dict] = None


class RunAnalysisRequest(BaseModel):
    session_id: str


class RunAnalysisResponse(BaseModel):
    session_id: str
    summary: str
    architecture: str
    dependency_report: str
    security_scan: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_files(tree: dict) -> int:
    if tree["type"] == "file":
        return 1
    return sum(_count_files(c) for c in tree.get("children", []))


def _normalize_repo_url(url: str) -> str:
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url.lower()


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_repository(request: AnalyzeRequest):
    repo_url = str(request.repo_url)
    cache_key = _normalize_repo_url(repo_url)
    repo_path: Optional[str] = None

    if cache_key in analysis_cache:
        cached = analysis_cache[cache_key]
        session_id = uuid.uuid4().hex[:12]
        build_vector_store(session_id, cached["code_chunks"])
        sessions[session_id] = {
            "repo_url": repo_url,
            "file_tree": cached["file_tree"],
            "dependencies": cached["dependencies"],
            "code_chunks": cached["code_chunks"],
        }
        return AnalyzeResponse(
            session_id=session_id,
            file_tree=cached["file_tree"],
            summary=cached["analysis"]["summary"],
            architecture=cached["analysis"]["architecture"],
            dependency_report=cached["analysis"]["dependency_report"],
            security_scan=cached["analysis"]["security_scan"],
            cached=True,
        )

    try:
        repo_path = clone_repository(repo_url)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to clone repository: {exc}")

    try:
        file_tree = get_file_tree(repo_path)
        dependencies = parse_dependencies(repo_path)
        code_chunks = get_code_chunks(repo_path)

        session_id = uuid.uuid4().hex[:12]
        build_vector_store(session_id, code_chunks)
        analysis = run_full_analysis(file_tree, dependencies, code_chunks)

        sessions[session_id] = {
            "repo_url": repo_url,
            "file_tree": file_tree,
            "dependencies": dependencies,
            "code_chunks": code_chunks,
        }

        analysis_cache[cache_key] = {
            "file_tree": file_tree,
            "dependencies": dependencies,
            "code_chunks": code_chunks,
            "analysis": analysis,
        }

        return AnalyzeResponse(
            session_id=session_id,
            file_tree=file_tree,
            **analysis,
        )
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=f"LLM rate limit exceeded. Please try again shortly. ({exc})")
    except Exception as exc:
        logger.exception("Analysis failed for %s", repo_url)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if repo_path:
            cleanup_repository(repo_path)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question cannot be empty.")
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session expired or not found. Please re-analyze the repository.")

    try:
        relevant = query_vector_store(request.session_id, request.question, n_results=5)
        answer = generate_chat_answer(request.question, relevant)

        sources = [
            {"file": r["metadata"]["source"], "distance": r["distance"]}
            for r in relevant
        ]

        return ChatResponse(
            session_id=request.session_id,
            question=request.question,
            answer=answer,
            sources=sources,
        )
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=f"LLM rate limit exceeded. Please try again shortly. ({exc})")
    except Exception as exc:
        logger.exception("Chat failed for session %s", request.session_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/onboarding", response_model=OnboardingResponse)
async def onboarding(request: OnboardingRequest):
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session expired or not found. Please re-analyze the repository.")

    session = sessions[request.session_id]

    try:
        guide = generate_onboarding(
            session["file_tree"],
            session["dependencies"],
            session["code_chunks"],
        )
        return OnboardingResponse(
            session_id=request.session_id,
            onboarding_guide=guide,
        )
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=f"LLM rate limit exceeded. Please try again shortly. ({exc})")
    except Exception as exc:
        logger.exception("Onboarding generation failed for session %s", request.session_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/clone", response_model=CloneResponse)
async def clone_and_parse(request: AnalyzeRequest):
    repo_url = str(request.repo_url)
    cache_key = _normalize_repo_url(repo_url)
    repo_path: Optional[str] = None

    if cache_key in analysis_cache:
        cached = analysis_cache[cache_key]
        session_id = uuid.uuid4().hex[:12]
        build_vector_store(session_id, cached["code_chunks"])
        sessions[session_id] = {
            "repo_url": repo_url,
            "file_tree": cached["file_tree"],
            "dependencies": cached["dependencies"],
            "code_chunks": cached["code_chunks"],
            "cache_key": cache_key,
        }
        return CloneResponse(
            session_id=session_id,
            file_tree=cached["file_tree"],
            stats={
                "files": _count_files(cached["file_tree"]),
                "chunks": len(cached["code_chunks"]),
                "dependencies": sum(len(d["dependencies"]) for d in cached["dependencies"]),
            },
            cached=True,
            analysis=cached["analysis"],
        )

    try:
        repo_path = clone_repository(repo_url)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to clone repository: {exc}")

    try:
        file_tree = get_file_tree(repo_path)
        dependencies = parse_dependencies(repo_path)
        code_chunks = get_code_chunks(repo_path)

        session_id = uuid.uuid4().hex[:12]
        build_vector_store(session_id, code_chunks)

        sessions[session_id] = {
            "repo_url": repo_url,
            "file_tree": file_tree,
            "dependencies": dependencies,
            "code_chunks": code_chunks,
            "cache_key": cache_key,
        }

        return CloneResponse(
            session_id=session_id,
            file_tree=file_tree,
            stats={
                "files": _count_files(file_tree),
                "chunks": len(code_chunks),
                "dependencies": sum(len(d["dependencies"]) for d in dependencies),
            },
            cached=False,
        )
    except Exception as exc:
        logger.exception("Clone/parse failed for %s", repo_url)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if repo_path:
            cleanup_repository(repo_path)


@app.post("/api/run-analysis", response_model=RunAnalysisResponse)
async def run_analysis_endpoint(request: RunAnalysisRequest):
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found. Please clone the repository first.")

    session = sessions[request.session_id]

    try:
        analysis = run_full_analysis(
            session["file_tree"],
            session["dependencies"],
            session["code_chunks"],
        )

        cache_key = session.get("cache_key")
        if cache_key:
            analysis_cache[cache_key] = {
                "file_tree": session["file_tree"],
                "dependencies": session["dependencies"],
                "code_chunks": session["code_chunks"],
                "analysis": analysis,
            }

        return RunAnalysisResponse(
            session_id=request.session_id,
            **analysis,
        )
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=f"LLM rate limit exceeded. Please try again shortly. ({exc})")
    except Exception as exc:
        logger.exception("Analysis failed for session %s", request.session_id)
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (disable if venv installs cause restarts)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(
        "backend.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        reload_dirs=["backend"] if args.reload else None,
    )
