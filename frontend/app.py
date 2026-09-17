import re
import streamlit as st
import requests
from datetime import datetime

API_BASE = "http://localhost:8000"


# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

LIGHT_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #312e81 0%, #4338ca 50%, #4f46e5 100%);
    }
    [data-testid="stSidebar"] * {
        color: #e0e7ff !important;
    }
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stSelectbox label {
        color: #c7d2fe !important;
        font-weight: 500;
    }
    [data-testid="stSidebar"] .stTextInput input {
        background: rgba(255,255,255,0.12) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        color: #ffffff !important;
        border-radius: 8px;
    }
    [data-testid="stSidebar"] .stTextInput input::placeholder {
        color: rgba(255,255,255,0.5) !important;
    }
    [data-testid="stSidebar"] .stTextInput input:focus {
        border-color: #a5b4fc !important;
        box-shadow: 0 0 0 2px rgba(165,180,252,0.3) !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.15) !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: #ffffff !important;
        color: #4338ca !important;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: #eef2ff !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    [data-testid="stSidebar"] .stButton > button:not([kind="primary"]) {
        background: rgba(255,255,255,0.1) !important;
        color: #e0e7ff !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 8px;
        transition: all 0.2s;
    }
    [data-testid="stSidebar"] .stButton > button:not([kind="primary"]):hover {
        background: rgba(255,255,255,0.2) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #ffffff;
        padding: 4px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background: #4f46e5 !important;
        color: #ffffff !important;
        border-radius: 8px;
    }

    .stChatMessage {
        border-radius: 12px !important;
        border: 1px solid #e2e8f0 !important;
        padding: 1rem !important;
    }

    .stExpander {
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        background: #ffffff;
    }

    h1 { color: #1e293b; font-weight: 700; }
    h2, h3 { color: #334155; font-weight: 600; }

    .landing-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        border: 1px solid #e2e8f0;
        height: 100%;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .landing-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.08);
    }
    .landing-card h4 { color: #4f46e5; margin-bottom: 0.5rem; }
    .landing-card p { color: #64748b; font-size: 0.95rem; }

    .history-item {
        background: rgba(255,255,255,0.1);
        border-radius: 8px;
        padding: 0.5rem 0.75rem;
        margin-bottom: 0.4rem;
        cursor: pointer;
        transition: background 0.2s;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .history-item:hover {
        background: rgba(255,255,255,0.18);
    }
    .history-item .repo-name {
        font-weight: 600;
        font-size: 0.85rem;
        color: #ffffff !important;
    }
    .history-item .repo-url {
        font-size: 0.7rem;
        color: rgba(255,255,255,0.55) !important;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-cached { background: #dcfce7; color: #166534; }
    .badge-fresh { background: #dbeafe; color: #1e40af; }

    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #4f46e5 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: #64748b !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }

    .starter-btn button {
        background: #eef2ff !important;
        color: #4338ca !important;
        border: 1px solid #c7d2fe !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        text-align: left !important;
    }
    .starter-btn button:hover {
        background: #e0e7ff !important;
        border-color: #a5b4fc !important;
    }

    .chat-timestamp {
        font-size: 0.7rem;
        color: #94a3b8;
        margin-top: 2px;
    }
</style>
"""

DARK_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #e2e8f0;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #020617 0%, #0f172a 50%, #1e1b4b 100%);
    }
    [data-testid="stSidebar"] * {
        color: #c7d2fe !important;
    }
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stSelectbox label {
        color: #a5b4fc !important;
        font-weight: 500;
    }
    [data-testid="stSidebar"] .stTextInput input {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        color: #e2e8f0 !important;
        border-radius: 8px;
    }
    [data-testid="stSidebar"] .stTextInput input::placeholder {
        color: rgba(255,255,255,0.35) !important;
    }
    [data-testid="stSidebar"] .stTextInput input:focus {
        border-color: #818cf8 !important;
        box-shadow: 0 0 0 2px rgba(129,140,248,0.25) !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.08) !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: #818cf8 !important;
        color: #0f172a !important;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        transition: all 0.2s;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: #a5b4fc !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    [data-testid="stSidebar"] .stButton > button:not([kind="primary"]) {
        background: rgba(255,255,255,0.06) !important;
        color: #c7d2fe !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 8px;
        transition: all 0.2s;
    }
    [data-testid="stSidebar"] .stButton > button:not([kind="primary"]):hover {
        background: rgba(255,255,255,0.12) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #1e293b;
        padding: 4px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
        color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        background: #818cf8 !important;
        color: #0f172a !important;
        border-radius: 8px;
    }

    .stChatMessage {
        border-radius: 12px !important;
        border: 1px solid #334155 !important;
        background: #1e293b !important;
        padding: 1rem !important;
    }

    .stExpander {
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        background: #1e293b;
    }

    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span {
        color: #cbd5e1 !important;
    }
    .stCode, code {
        background: #1e293b !important;
        color: #e2e8f0 !important;
    }

    h1 { color: #f1f5f9 !important; font-weight: 700; }
    h2, h3 { color: #e2e8f0 !important; font-weight: 600; }

    .landing-card {
        background: #1e293b;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        border: 1px solid #334155;
        height: 100%;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .landing-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    }
    .landing-card h4 { color: #818cf8 !important; margin-bottom: 0.5rem; }
    .landing-card p { color: #94a3b8 !important; font-size: 0.95rem; }

    .history-item {
        background: rgba(255,255,255,0.04);
        border-radius: 8px;
        padding: 0.5rem 0.75rem;
        margin-bottom: 0.4rem;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .history-item:hover {
        background: rgba(255,255,255,0.08);
    }
    .history-item .repo-name {
        font-weight: 600;
        font-size: 0.85rem;
        color: #e2e8f0 !important;
    }
    .history-item .repo-url {
        font-size: 0.7rem;
        color: rgba(255,255,255,0.4) !important;
    }

    .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-cached { background: #064e3b; color: #6ee7b7; }
    .badge-fresh { background: #1e3a5f; color: #93c5fd; }

    [data-testid="stStatusWidget"],
    .stAlert {
        background: #1e293b !important;
        border-color: #334155 !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #818cf8 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: #94a3b8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }

    .starter-btn button {
        background: #1e293b !important;
        color: #a5b4fc !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        text-align: left !important;
    }
    .starter-btn button:hover {
        background: #334155 !important;
        border-color: #818cf8 !important;
    }

    .chat-timestamp {
        font-size: 0.7rem;
        color: #64748b;
        margin-top: 2px;
    }
</style>
"""


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def call_clone(repo_url: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/api/clone",
        json={"repo_url": repo_url},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()


def call_run_analysis(session_id: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/api/run-analysis",
        json={"session_id": session_id},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()


def call_chat(session_id: str, question: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/api/chat",
        json={"session_id": session_id, "question": question},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def call_onboarding(session_id: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/api/onboarding",
        json={"session_id": session_id},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Tree / utility helpers
# ---------------------------------------------------------------------------

def render_file_tree(node: dict, prefix: str = "", is_last: bool = True, is_root: bool = True) -> str:
    lines = []
    if is_root:
        lines.append(f"{node['name']}/")
    else:
        connector = "└── " if is_last else "├── "
        suffix = "/" if node["type"] == "directory" else ""
        lines.append(f"{prefix}{connector}{node['name']}{suffix}")

    if node["type"] == "directory":
        children = node.get("children", [])
        for i, child in enumerate(children):
            child_is_last = i == len(children) - 1
            if is_root:
                child_prefix = ""
            else:
                child_prefix = prefix + ("    " if is_last else "│   ")
            lines.append(render_file_tree(child, child_prefix, child_is_last, False))

    return "\n".join(lines)


def _extract_repo_name(url: str) -> str:
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url.split("/")[-1] if "/" in url else url


def _filter_tree(node: dict, search: str) -> dict | None:
    search_lower = search.lower()

    if node["type"] == "file":
        if search_lower in node["name"].lower():
            return node
        return None

    filtered_children = []
    for child in node.get("children", []):
        result = _filter_tree(child, search)
        if result is not None:
            filtered_children.append(result)

    if filtered_children or search_lower in node["name"].lower():
        return {
            "name": node["name"],
            "type": "directory",
            "children": filtered_children,
        }
    return None


def _count_security_issues(scan_text: str) -> dict:
    high = len(re.findall(r'\bHIGH\b', scan_text))
    medium = len(re.findall(r'\bMEDIUM\b', scan_text))
    low = len(re.findall(r'\bLOW\b', scan_text))
    return {"high": high, "medium": medium, "low": low, "total": high + medium + low}


STARTER_QUESTIONS = [
    "What does this project do?",
    "What are the main entry points?",
    "How is the project structured?",
    "What testing framework is used?",
]


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="RepoLens",
    page_icon="\U0001f52d",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "onboarding_guide" not in st.session_state:
    st.session_state.onboarding_guide = None
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

# ---------------------------------------------------------------------------
# Inject CSS
# ---------------------------------------------------------------------------

st.markdown(DARK_CSS if st.session_state.dark_mode else LIGHT_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        "<h1 style='text-align:center; font-size:1.8rem; margin-bottom:0;'>"
        "\U0001f52d RepoLens</h1>"
        "<p style='text-align:center; font-size:0.85rem; opacity:0.7; margin-top:0.2rem;'>"
        "AI-powered repository analyst</p>",
        unsafe_allow_html=True,
    )

    col_spacer, col_toggle = st.columns([3, 1])
    with col_toggle:
        dark_mode = st.toggle(
            "\U0001f31c" if st.session_state.dark_mode else "☀️",
            value=st.session_state.dark_mode,
            key="dark_toggle",
        )
        if dark_mode != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_mode
            st.rerun()

    st.divider()

    repo_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/user/repo",
    )

    analyze_clicked = st.button("Analyze Repository", type="primary", use_container_width=True)

    if analyze_clicked and repo_url:
        with st.status("Analyzing repository...", expanded=True) as status:
            try:
                st.write("\U0001f4e6 Cloning & parsing repository...")
                clone_result = call_clone(repo_url)
                session_id = clone_result["session_id"]
                stats = clone_result["stats"]

                if clone_result.get("cached") and clone_result.get("analysis"):
                    st.write(
                        f"✅ Loaded from cache — "
                        f"**{stats['files']}** files, "
                        f"**{stats['chunks']}** code chunks, "
                        f"**{stats['dependencies']}** dependencies"
                    )
                    analysis_data = {
                        "session_id": session_id,
                        "file_tree": clone_result["file_tree"],
                        "stats": stats,
                        "cached": True,
                        **clone_result["analysis"],
                    }
                    status.update(label="Loaded from cache!", state="complete", expanded=False)
                else:
                    st.write(
                        f"✅ Parsed — "
                        f"**{stats['files']}** files, "
                        f"**{stats['chunks']}** code chunks, "
                        f"**{stats['dependencies']}** dependencies"
                    )

                    st.write("\U0001f916 Running AI analysis (this may take a minute)...")
                    analysis_result = call_run_analysis(session_id)
                    st.write("✅ AI analysis complete!")
                    analysis_data = {
                        "session_id": session_id,
                        "file_tree": clone_result["file_tree"],
                        "stats": stats,
                        "cached": False,
                        "summary": analysis_result["summary"],
                        "architecture": analysis_result["architecture"],
                        "dependency_report": analysis_result["dependency_report"],
                        "security_scan": analysis_result["security_scan"],
                    }
                    status.update(label="Analysis complete!", state="complete", expanded=False)

                st.session_state.session_id = session_id
                st.session_state.analysis = analysis_data
                st.session_state.chat_history = []
                st.session_state.onboarding_guide = None
                st.session_state.pending_question = None

                repo_name = _extract_repo_name(repo_url)
                existing = [h for h in st.session_state.analysis_history if h["repo_url"] == repo_url]
                if not existing:
                    st.session_state.analysis_history.insert(0, {
                        "repo_url": repo_url,
                        "repo_name": repo_name,
                        "session_id": session_id,
                        "analysis": analysis_data,
                        "cached": analysis_data.get("cached", False),
                    })
                else:
                    existing[0]["session_id"] = session_id
                    existing[0]["analysis"] = analysis_data

            except requests.exceptions.ConnectionError:
                status.update(label="Connection failed", state="error")
                st.error("Cannot connect to the backend. Make sure the API server is running on port 8000.")
            except requests.exceptions.HTTPError as e:
                status.update(label="Analysis failed", state="error")
                try:
                    detail = e.response.json().get("detail", e.response.text)
                except Exception:
                    detail = e.response.text
                if e.response.status_code == 429:
                    st.warning(f"Rate limited: {detail}")
                elif e.response.status_code == 422:
                    st.error(f"Invalid repository: {detail}")
                else:
                    st.error(f"Analysis failed: {detail}")
            except Exception as e:
                status.update(label="Error", state="error")
                st.error(f"Error: {e}")
    elif analyze_clicked and not repo_url:
        st.warning("Please enter a repository URL.")

    # -- Analysis History --
    if st.session_state.analysis_history:
        st.divider()
        st.markdown(
            "<p style='font-size:0.8rem; font-weight:600; text-transform:uppercase; "
            "letter-spacing:0.05em; opacity:0.7; margin-bottom:0.5rem;'>"
            "\U0001f4da Analysis History</p>",
            unsafe_allow_html=True,
        )
        for idx, entry in enumerate(st.session_state.analysis_history):
            badge = "cached" if entry.get("cached") else "fresh"
            st.markdown(
                f"<div class='history-item'>"
                f"<div class='repo-name'>{entry['repo_name']} "
                f"<span class='status-badge badge-{badge}'>{badge}</span></div>"
                f"<div class='repo-url'>{entry['repo_url']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if st.button(f"Load", key=f"history_{idx}", use_container_width=True):
                st.session_state.session_id = entry["session_id"]
                st.session_state.analysis = entry["analysis"]
                st.session_state.chat_history = []
                st.session_state.onboarding_guide = None
                st.session_state.pending_question = None
                st.rerun()

    if st.session_state.session_id:
        st.divider()
        st.markdown(
            f"<p style='font-size:0.75rem; opacity:0.6;'>"
            f"Session: <code>{st.session_state.session_id}</code></p>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

if st.session_state.analysis is None:
    st.markdown(
        "<h1 style='text-align:center; margin-top:2rem;'>\U0001f52d RepoLens</h1>"
        "<p style='text-align:center; font-size:1.1rem; opacity:0.7; margin-bottom:2.5rem;'>"
        "Enter a public GitHub repository URL in the sidebar to get started.</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            "<div class='landing-card'>"
            "<h4>\U0001f4ca Codebase Analysis</h4>"
            "<p>Project summary, architecture overview, and dependency report "
            "powered by AI.</p></div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            "<div class='landing-card'>"
            "<h4>\U0001f4ac Interactive Q&A</h4>"
            "<p>Ask questions about the codebase and get AI-powered answers "
            "with source citations.</p></div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            "<div class='landing-card'>"
            "<h4>\U0001f4cb Onboarding Guide</h4>"
            "<p>Auto-generated developer onboarding documentation ready to "
            "download and share.</p></div>",
            unsafe_allow_html=True,
        )
else:
    analysis = st.session_state.analysis
    stats = analysis.get("stats", {})
    sec_counts = _count_security_issues(analysis.get("security_scan", ""))

    # -- Tab labels with badges --
    file_count = stats.get("files", 0)
    dep_count = stats.get("dependencies", 0)
    sec_total = sec_counts["total"]
    chat_count = len(st.session_state.chat_history)

    tab_labels = [
        "\U0001f4ca Summary",
        "\U0001f3d7️ Architecture",
        f"\U0001f4e6 Dependencies ({dep_count})" if dep_count else "\U0001f4e6 Dependencies",
        f"\U0001f512 Security ({sec_total})" if sec_total else "\U0001f512 Security",
        f"\U0001f5c2️ Files ({file_count})" if file_count else "\U0001f5c2️ File Tree",
        f"\U0001f4ac Chat ({chat_count})" if chat_count else "\U0001f4ac Chat",
        "\U0001f4cb Onboarding",
    ]

    tab_summary, tab_arch, tab_deps, tab_security, tab_tree, tab_chat, tab_onboard = st.tabs(tab_labels)

    # -- Summary --
    with tab_summary:
        st.header("Project Summary")

        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            st.metric("Files Analyzed", stats.get("files", "—"))
        with mc2:
            st.metric("Code Sections", stats.get("chunks", "—"))
        with mc3:
            st.metric("Dependencies", stats.get("dependencies", "—"))
        with mc4:
            st.metric("Security Issues", sec_total)

        st.divider()
        st.markdown(analysis["summary"])
        st.download_button(
            "\U0001f4cb Download Summary",
            data=analysis["summary"],
            file_name="summary.md",
            mime="text/markdown",
            key="dl_summary",
        )

    # -- Architecture --
    with tab_arch:
        st.header("Architecture Overview")
        st.markdown(analysis["architecture"])
        st.download_button(
            "\U0001f4cb Download Architecture Report",
            data=analysis["architecture"],
            file_name="architecture.md",
            mime="text/markdown",
            key="dl_arch",
        )

    # -- Dependencies --
    with tab_deps:
        st.header("Dependency Report")
        st.markdown(analysis["dependency_report"])
        st.download_button(
            "\U0001f4cb Download Dependency Report",
            data=analysis["dependency_report"],
            file_name="dependencies.md",
            mime="text/markdown",
            key="dl_deps",
        )

    # -- Security --
    with tab_security:
        st.header("Security Scan")

        if sec_total > 0:
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.metric("HIGH", sec_counts["high"])
            with sc2:
                st.metric("MEDIUM", sec_counts["medium"])
            with sc3:
                st.metric("LOW", sec_counts["low"])
            st.divider()

        st.markdown(analysis["security_scan"])
        st.download_button(
            "\U0001f4cb Download Security Report",
            data=analysis["security_scan"],
            file_name="security_scan.md",
            mime="text/markdown",
            key="dl_security",
        )

    # -- File Tree --
    with tab_tree:
        st.header("Repository File Tree")

        search_term = st.text_input(
            "Search files",
            placeholder="Filter by file or folder name...",
            key="tree_search",
        )

        if search_term:
            filtered = _filter_tree(analysis["file_tree"], search_term)
            if filtered:
                tree_text = render_file_tree(filtered)
                st.code(tree_text, language=None)
            else:
                st.info(f'No files or folders matching "{search_term}".')
        else:
            tree_text = render_file_tree(analysis["file_tree"])
            st.code(tree_text, language=None)

    # -- Chat --
    with tab_chat:
        col_chat_title, col_chat_clear = st.columns([8, 2])
        with col_chat_title:
            st.header("Repository Q&A")
        with col_chat_clear:
            if st.session_state.chat_history:
                if st.button("Clear Chat", key="clear_chat", use_container_width=True):
                    st.session_state.chat_history = []
                    st.rerun()

        # Starter questions when chat is empty
        if not st.session_state.chat_history and not st.session_state.pending_question:
            st.markdown("**Suggested questions to get started:**")
            sq1, sq2 = st.columns(2)
            for i, q in enumerate(STARTER_QUESTIONS):
                with (sq1 if i % 2 == 0 else sq2):
                    st.markdown("<div class='starter-btn'>", unsafe_allow_html=True)
                    if st.button(q, key=f"starter_{i}", use_container_width=True):
                        st.session_state.pending_question = q
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            st.divider()

        for entry in st.session_state.chat_history:
            with st.chat_message("user"):
                st.markdown(entry["question"])
                if entry.get("timestamp"):
                    st.markdown(
                        f"<div class='chat-timestamp'>{entry['timestamp']}</div>",
                        unsafe_allow_html=True,
                    )
            with st.chat_message("assistant"):
                st.markdown(entry["answer"])
                if entry.get("sources"):
                    with st.expander("Sources"):
                        for src in entry["sources"]:
                            st.markdown(f"- `{src['file']}` (distance: {src['distance']:.4f})")

        question = st.chat_input("Ask a question about the codebase...")

        if st.session_state.pending_question:
            question = st.session_state.pending_question
            st.session_state.pending_question = None

        if question:
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        result = call_chat(st.session_state.session_id, question)
                        st.markdown(result["answer"])
                        if result.get("sources"):
                            with st.expander("Sources"):
                                for src in result["sources"]:
                                    st.markdown(f"- `{src['file']}` (distance: {src['distance']:.4f})")
                        st.session_state.chat_history.append({
                            "question": question,
                            "answer": result["answer"],
                            "sources": result.get("sources", []),
                            "timestamp": datetime.now().strftime("%I:%M %p"),
                        })
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 404:
                            st.error("Session expired (server was restarted). Please click **Analyze Repository** again in the sidebar.")
                        elif e.response.status_code == 429:
                            st.warning("Rate limited by the LLM provider. Please wait a moment and try again.")
                        else:
                            try:
                                detail = e.response.json().get("detail", str(e))
                            except Exception:
                                detail = e.response.text or str(e)
                            st.error(f"Chat error: {detail}")
                    except Exception as e:
                        st.error(f"Chat error: {e}")

    # -- Onboarding --
    with tab_onboard:
        st.header("Developer Onboarding Guide")

        if st.session_state.onboarding_guide:
            st.markdown(st.session_state.onboarding_guide)
            st.download_button(
                "Download as Markdown",
                data=st.session_state.onboarding_guide,
                file_name="ONBOARDING.md",
                mime="text/markdown",
            )
        else:
            st.markdown("Generate a comprehensive onboarding guide for new developers joining this project.")
            if st.button("Generate Onboarding Guide", type="primary"):
                with st.spinner("Generating onboarding guide..."):
                    try:
                        result = call_onboarding(st.session_state.session_id)
                        st.session_state.onboarding_guide = result["onboarding_guide"]
                        st.rerun()
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 404:
                            st.error("Session expired (server was restarted). Please click **Analyze Repository** again in the sidebar.")
                        elif e.response.status_code == 429:
                            st.warning("Rate limited by the LLM provider. Please wait a moment and try again.")
                        else:
                            try:
                                detail = e.response.json().get("detail", str(e))
                            except Exception:
                                detail = e.response.text or str(e)
                            st.error(f"Onboarding error: {detail}")
                    except Exception as e:
                        st.error(f"Onboarding error: {e}")
