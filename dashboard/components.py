import textwrap
import time
import streamlit as st

from agent.graph import run_agent

def _html(raw: str) -> str:
    return textwrap.dedent(raw).strip()


def inject_custom_css():
    st.markdown(
        _html("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap');

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .stApp {
            background: radial-gradient(circle at 20% 0%, #101826 0%, #0a0e17 45%, #060810 100%);
        }
        h1, h2, h3, .radar-title { font-family: 'Space Grotesk', sans-serif !important; }

        .radar-title {
            font-size: 2.4rem; font-weight: 700;
            background: linear-gradient(90deg, #22d3ee, #a78bfa);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 0; letter-spacing: -0.5px;
        }
        .radar-subtitle { color: #7d8aa3; font-size: 0.95rem; margin: 0.2rem 0 1.4rem 0; }

        .stat-pill {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px; padding: 14px 18px; text-align: center;
        }
        .stat-pill .value { font-family: 'Space Grotesk', sans-serif; font-size: 1.6rem; font-weight: 700; color: #e5e9f0; }
        .stat-pill .label { font-size: 0.75rem; color: #7d8aa3; text-transform: uppercase; letter-spacing: 0.06em; }

        .tier-heading {
            font-family: 'Space Grotesk', sans-serif; font-size: 1.05rem; font-weight: 700;
            color: #cfd6e4; margin: 22px 0 8px 2px;
            display: flex; align-items: center; gap: 8px;
        }
        .tier-count { color: #7d8aa3; font-weight: 500; font-size: 0.85rem; }

        .top-pick {
            background: linear-gradient(135deg, rgba(245,158,11,0.10), rgba(255,255,255,0.03));
            border: 1px solid rgba(245,158,11,0.4);
            border-radius: 18px; padding: 22px 26px; margin-bottom: 18px;
        }
        .top-pick-label {
            display: inline-block; font-size: 0.72rem; font-weight: 700;
            letter-spacing: 0.08em; text-transform: uppercase; color: #f59e0b;
            margin-bottom: 8px;
        }
        .top-pick-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.3rem; font-weight: 700; color: #f5f2ea; margin-bottom: 8px; }
        .top-pick-abstract { color: #b9ad96; font-size: 0.92rem; line-height: 1.55; margin-bottom: 10px; }

        .paper-abstract { color: #9aa5b8; font-size: 0.87rem; line-height: 1.55; margin: 10px 0 12px 0; }
        .paper-link a { color: #22d3ee; text-decoration: none; font-size: 0.82rem; font-weight: 500; }
        .paper-link a:hover { text-decoration: underline; }

        .tier-badge {
            display: inline-block; padding: 3px 10px; border-radius: 20px;
            font-size: 0.72rem; font-weight: 600; letter-spacing: 0.03em; text-transform: uppercase;
        }
        .ring-wrap { display: flex; align-items: center; gap: 10px; }
        .ring-score-text { font-family: 'Space Grotesk', sans-serif; font-size: 0.95rem; font-weight: 700; }

        @keyframes shimmer {
            0% { background-position: -400px 0; }
            100% { background-position: 400px 0; }
        }
        .shimmer-box {
            height: 70px; border-radius: 12px; margin-top: 10px;
            background: linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.08) 37%, rgba(255,255,255,0.03) 63%);
            background-size: 800px 100%;
            animation: shimmer 1.4s linear infinite;
            display: flex; align-items: center; justify-content: center;
        }
        @keyframes pulse-text {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.35; }
        }
        .analyzing-label {
            color: #22d3ee; font-weight: 600; font-size: 0.9rem;
            animation: pulse-text 1.1s ease-in-out infinite;
        }

        /* Fix: the agent's generated explanation had no color rule
           at all, so it rendered in Streamlit's dim default text
           color — this was the real bug, not a rendering timing
           issue. */
        .agent-explanation, .agent-explanation p, .agent-explanation li, .agent-explanation strong {
            color: #dde3ee !important;
            line-height: 1.6;
        }
        .agent-explanation {
            background: rgba(255,255,255,0.03);
            border-left: 3px solid #22d3ee;
            border-radius: 8px;
            padding: 14px 18px;
            margin-top: 8px;
        }

        div[data-testid="stExpander"] {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
        }

        /* Fix: Streamlit's default caption/expander text is too dim
           against our dark background — override explicitly using
           stable data-testid selectors (not internal class names,
           which change across Streamlit versions). */
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p {
            color: #b6c0d1 !important;
        }
        div[data-testid="stExpander"] summary,
        div[data-testid="stExpander"] summary p,
        div[data-testid="stExpander"] summary span {
            color: #e5e9f0 !important;
            font-weight: 500 !important;
        }
        /* Fix: Streamlit applies its own light hover/active background
           to the expander summary bar — our bright text above became
           invisible against that light background once clicked/expanded.
           Force the background to stay dark in every interaction state. */
        div[data-testid="stExpander"] summary,
        div[data-testid="stExpander"] summary:hover,
        div[data-testid="stExpander"] summary:focus,
        div[data-testid="stExpander"] summary:active {
            background-color: #0d1420 !important;
        }
        div[data-testid="stExpander"] summary svg {
            fill: #7d8aa3 !important;
        }
        </style>
        """),
        unsafe_allow_html=True,
    )


def score_tier(score: float) -> dict:
    if score >= 0.35:
        return {"label": "Strong Match", "color": "#22d3ee", "bg": "rgba(34,211,238,0.14)", "dot": "🔵"}
    if score >= 0.25:
        return {"label": "Good Match", "color": "#a78bfa", "bg": "rgba(167,139,250,0.14)", "dot": "🟣"}
    return {"label": "Fair Match", "color": "#7d8aa3", "bg": "rgba(125,138,163,0.14)", "dot": "⚪"}


def render_score_ring(score: float, color: str, size: int = 50) -> str:
    radius = 22
    circumference = 2 * 3.14159 * radius
    offset = circumference * (1 - score)
    pct = int(round(score * 100))
    return _html(f"""
        <div class="ring-wrap">
            <svg width="{size}" height="{size}" viewBox="0 0 54 54">
                <circle cx="27" cy="27" r="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="5"/>
                <circle cx="27" cy="27" r="{radius}" fill="none" stroke="{color}" stroke-width="5"
                        stroke-linecap="round" stroke-dasharray="{circumference:.1f}"
                        stroke-dashoffset="{offset:.1f}" transform="rotate(-90 27 27)"/>
            </svg>
            <span class="ring-score-text" style="color:{color};">{pct}%</span>
        </div>
    """)


def _run_analysis_block(paper) -> None: 
    result_key = f"result_{paper.id}"
    button_key = f"analyze_{paper.id}"
    retry_at_key = f"retry_at_{paper.id}"

    retry_at = st.session_state.get(retry_at_key)
    cooling_down = retry_at is not None and time.time() < retry_at

    col1, col2 = st.columns([5, 2])
    with col2:
        clicked = st.button(
            "🔍 Run Agent Analysis",
            key=button_key,
            use_container_width=True,
            disabled=cooling_down,
        )

    if cooling_down:
        remaining = int(retry_at - time.time())
        st.caption(f"⏳ Free-tier LLM quota reached — try again in {remaining}s.")

    if clicked and not cooling_down:
        placeholder = st.empty()
        placeholder.markdown(
            _html('<div class="shimmer-box"><span class="analyzing-label">🔎 Analyzing paper…</span></div>'),
            unsafe_allow_html=True,
        )
        try:
            result = run_agent(paper.id, paper.abstract)
        except Exception as e:
            result = {"explanation": f"⚠️ Unexpected error: {e}", "error": str(e)}
        st.session_state[result_key] = result

        if result.get("rate_limited"):
            wait = result.get("retry_after_seconds") or 60
            st.session_state[retry_at_key] = time.time() + wait
        else:
            st.session_state.pop(retry_at_key, None)

        placeholder.empty()

    if result_key in st.session_state:
        result = st.session_state[result_key]

        if result.get("rate_limited"):
            wait = result.get("retry_after_seconds") or 60
            st.warning(
                f"⏳ We've hit the free-tier LLM limit right now. "
                f"Try again in about {wait} seconds."
            )
            return

        if result.get("used_fallback"):
            st.caption("ℹ️ Based on the abstract only — full-text digest wasn't available for this paper.")
        explanation = result.get("explanation", "No explanation generated.")
        st.markdown(
            f'<div class="agent-explanation">\n\n{explanation}\n\n</div>',
            unsafe_allow_html=True,
        )


def render_top_pick(paper) -> None:
    st.markdown(
        _html(f"""
        <div class="top-pick">
            <span class="top-pick-label">⭐ Top Match Today — {int((paper.match_score or 0) * 100)}%</span>
            <div class="top-pick-title">{paper.title}</div>
            <div class="top-pick-abstract">{paper.abstract[:320]}{"…" if len(paper.abstract) > 320 else ""}</div>
            <div class="paper-link"><a href="{paper.link}" target="_blank">View on arXiv →</a></div>
        </div>
        """),
        unsafe_allow_html=True,
    )
    _run_analysis_block(paper)


def render_paper_row(paper) -> None:
    tier = score_tier(paper.match_score or 0.0)
    pct = int(round((paper.match_score or 0.0) * 100))
    label = f"{tier['dot']} {pct}%  ·  {paper.title}"

    with st.expander(label, expanded=False):
        st.markdown(
            _html(f"""
            <span class="tier-badge" style="color:{tier['color']}; background:{tier['bg']};">
                {tier['label']}
            </span>
            <div class="paper-abstract">{paper.abstract}</div>
            <div class="paper-link"><a href="{paper.link}" target="_blank">View on arXiv →</a></div>
            """),
            unsafe_allow_html=True,
        )
        _run_analysis_block(paper)


def render_grouped_papers(papers: list) -> None:
    if not papers:
        return

    sorted_papers = sorted(papers, key=lambda p: p.match_score or 0.0, reverse=True)
    top_pick, rest = sorted_papers[0], sorted_papers[1:]

    render_top_pick(top_pick)

    groups = {"Strong Match": [], "Good Match": [], "Fair Match": []}
    for p in rest:
        groups[score_tier(p.match_score or 0.0)["label"]].append(p)

    icons = {"Strong Match": "🔵", "Good Match": "🟣", "Fair Match": "⚪"}
    for tier_label, group in groups.items():
        if not group:
            continue
        st.markdown(
            _html(f"""
            <div class="tier-heading">{icons[tier_label]} {tier_label}
                <span class="tier-count">({len(group)})</span>
            </div>
            """),
            unsafe_allow_html=True,
        )
        for paper in group:
            render_paper_row(paper)