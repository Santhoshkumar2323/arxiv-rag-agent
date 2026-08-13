import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
from db.supabase_client import SupabaseClient
from dashboard.components import inject_custom_css, render_grouped_papers


st.set_page_config(
    page_title="Research Radar",
    page_icon="🛰️",
    layout="wide",
)

inject_custom_css()

try:
    db = SupabaseClient.get()
    papers = db.get_recent_papers()
except Exception as e:
    st.error(
        f"Couldn't connect to the database. Check your Supabase "
        f"credentials and connection. Details: {e}"
    )
    st.stop()


st.markdown('<div class="radar-title">🛰️ Research Radar</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="radar-subtitle">Your daily arXiv signal, filtered from the noise.</div>',
    unsafe_allow_html=True,
)

if not papers:
    st.info(
        "No papers in the current window yet. The nightly pipeline runs "
        "at 3:00 AM — check back after tonight's run, or trigger it "
        "manually from GitHub Actions."
    )
    st.stop()

scores = [p.match_score or 0.0 for p in papers]
avg_score = sum(scores) / len(scores)
top_score = max(scores)
analyzed_today = sum(
    1 for k in st.session_state.keys() if k.startswith("result_")
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f'<div class="stat-pill"><div class="value">{len(papers)}</div>'
        f'<div class="label">Papers Tracked</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f'<div class="stat-pill"><div class="value">{avg_score * 100:.0f}%</div>'
        f'<div class="label">Avg Match Score</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f'<div class="stat-pill"><div class="value">{top_score * 100:.0f}%</div>'
        f'<div class="label">Top Match Today</div></div>',
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        f'<div class="stat-pill"><div class="value">{analyzed_today}</div>'
        f'<div class="label">Analyzed Today</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:22px;'></div>", unsafe_allow_html=True)


with st.sidebar:
    st.markdown("### Filters")
    min_score = st.slider("Minimum match score", 0, 100, 0, step=5) / 100
    sort_by = st.radio("Sort by", ["Match score", "Newest first"], index=0)
    search_term = st.text_input("Search title or abstract", "")

filtered = [
    p for p in papers
    if (p.match_score or 0.0) >= min_score
    and (
        not search_term
        or search_term.lower() in p.title.lower()
        or search_term.lower() in p.abstract.lower()
    )
]

if sort_by == "Newest first":
    filtered.sort(key=lambda p: p.published_date, reverse=True)
else:
    filtered.sort(key=lambda p: p.match_score or 0.0, reverse=True)

st.caption(f"Showing {len(filtered)} of {len(papers)} papers")

if not filtered:
    st.warning("No papers match the current filters. Try loosening them.")
else:
    render_grouped_papers(filtered)