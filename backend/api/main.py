import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

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

sessions: dict[str, dict] = {}


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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_repository(request: AnalyzeRequest):
    repo_url = str(request.repo_url)
    repo_path: Optional[str] = None

    try:
        repo_path = clone_repository(repo_url)
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

        return AnalyzeResponse(
            session_id=session_id,
            file_tree=file_tree,
            **analysis,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if repo_path:
            cleanup_repository(repo_path)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found. Run /api/analyze first.")

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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/onboarding", response_model=OnboardingResponse)
async def onboarding(request: OnboardingRequest):
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found. Run /api/analyze first.")

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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
