import streamlit as st
import requests

API_BASE = "http://localhost:8000"


def call_analyze(repo_url: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/api/analyze",
        json={"repo_url": repo_url},
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


def render_file_tree(node: dict, indent: int = 0) -> str:
    lines = []
    prefix = "  " * indent
    if node["type"] == "directory":
        icon = "📁" if indent > 0 else "📦"
        lines.append(f"{prefix}{icon} **{node['name']}/**")
        for child in node.get("children", []):
            lines.append(render_file_tree(child, indent + 1))
    else:
        lines.append(f"{prefix}📄 {node['name']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="RepoLens",
    page_icon="🔍",
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

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🔍 RepoLens")
    st.caption("AI-powered GitHub repository analyst")
    st.divider()

    repo_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/user/repo",
    )

    analyze_clicked = st.button("Analyze Repository", type="primary", use_container_width=True)

    if analyze_clicked and repo_url:
        with st.spinner("Cloning and analyzing repository..."):
            try:
                result = call_analyze(repo_url)
                st.session_state.session_id = result["session_id"]
                st.session_state.analysis = result
                st.session_state.chat_history = []
                st.session_state.onboarding_guide = None
                st.success("Analysis complete!")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to the backend. Make sure the API server is running on port 8000.")
            except requests.exceptions.HTTPError as e:
                st.error(f"Analysis failed: {e.response.text}")
            except Exception as e:
                st.error(f"Error: {e}")
    elif analyze_clicked and not repo_url:
        st.warning("Please enter a repository URL.")

    if st.session_state.session_id:
        st.divider()
        st.info(f"Session: `{st.session_state.session_id}`")

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

if st.session_state.analysis is None:
    st.title("🔍 RepoLens")
    st.markdown(
        "Enter a public GitHub repository URL in the sidebar and click "
        "**Analyze Repository** to get started."
    )
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 📊 Codebase Analysis")
        st.markdown("Project summary, architecture overview, and dependency report.")
    with col2:
        st.markdown("#### 💬 Interactive Q&A")
        st.markdown("Ask questions about the codebase and get AI-powered answers.")
    with col3:
        st.markdown("#### 📋 Onboarding Guide")
        st.markdown("Auto-generated developer onboarding documentation.")
else:
    analysis = st.session_state.analysis

    tab_summary, tab_arch, tab_deps, tab_security, tab_tree, tab_chat, tab_onboard = st.tabs([
        "📊 Summary",
        "🏗️ Architecture",
        "📦 Dependencies",
        "🔒 Security",
        "🗂️ File Tree",
        "💬 Chat",
        "📋 Onboarding",
    ])

    # -- Summary --
    with tab_summary:
        st.header("Project Summary")
        st.markdown(analysis["summary"])

    # -- Architecture --
    with tab_arch:
        st.header("Architecture Overview")
        st.markdown(analysis["architecture"])

    # -- Dependencies --
    with tab_deps:
        st.header("Dependency Report")
        st.markdown(analysis["dependency_report"])

    # -- Security --
    with tab_security:
        st.header("Security Scan")
        st.markdown(analysis["security_scan"])

    # -- File Tree --
    with tab_tree:
        st.header("Repository File Tree")
        tree_md = render_file_tree(analysis["file_tree"])
        st.markdown(tree_md)

    # -- Chat --
    with tab_chat:
        st.header("Repository Q&A")

        for entry in st.session_state.chat_history:
            with st.chat_message("user"):
                st.markdown(entry["question"])
            with st.chat_message("assistant"):
                st.markdown(entry["answer"])
                if entry.get("sources"):
                    with st.expander("Sources"):
                        for src in entry["sources"]:
                            st.markdown(f"- `{src['file']}` (distance: {src['distance']:.4f})")

        question = st.chat_input("Ask a question about the codebase...")

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
                        })
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
                    except Exception as e:
                        st.error(f"Onboarding error: {e}")
