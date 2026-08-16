# Research Radar 🛰️

I read arXiv the way most researchers do: badly. New papers land daily across half a dozen categories I care about, and by the time I've skimmed titles I've lost the afternoon. So I built a system that does the skimming for me — and, for the handful of papers that actually matter, reads the full PDF and explains what's technically new before I click through.

This isn't a wrapper around a single API call. It's two systems working together: a nightly collector that never talks to an LLM, and an on-demand agent that only spins up when I actually want a deep read.


**Live dashboard:** https://arxiv-rag-agent.streamlit.app/


## How it works

```
┌─────────────────┐      every 5 days       ┌──────────────┐
│  arXiv API       │ ───────────────────▶   │  Collector   │
│  (8 categories)  │                         │  (GH Action) │
└─────────────────┘                         └──────┬───────┘
                                                     │ embed + score + rank
                                                     ▼
                                            ┌─────────────────┐
                                            │ Supabase         │
                                            │ (Postgres +      │
                                            │  pgvector)        │
                                            └────────┬────────┘
                                                     │ read
                                                     ▼
                                            ┌─────────────────┐        on click        ┌──────────────┐
                                            │ Streamlit        │ ─────────────────────▶ │ LangGraph    │
                                            │ Dashboard         │                        │ Agent + Gemini│
                                            └─────────────────┘ ◀───────────────────── └──────────────┘
                                                                    explanation
```

**Collector** (runs unattended, every 5 days via GitHub Actions): pulls new papers from 8 arXiv categories, embeds each abstract locally with `sentence-transformers`, scores it against my research interests by cosine similarity, and keeps the top 30. For those 30, it downloads the full PDF, chunks the text, and embeds every chunk — all before an LLM is ever involved. Old papers get pruned after 7 days.

**Dashboard**: a Streamlit app reading straight from Supabase. Papers are grouped into match tiers, filterable and searchable, with the day's top match pinned at the top.

**Agent** (on demand, one paper at a time): a small LangGraph graph — retrieve the most relevant chunks for the paper you clicked, fall back to the abstract if none exist, then ask Gemini for a structured five-part technical breakdown. Nothing gets analyzed until a human asks for it.

## Why it's built this way

**The agent is opt-in, not automatic.** Running 30 papers through an LLM every cycle would burn through free-tier quota fast and analyze plenty of papers nobody reads. Scoring is free and automatic; deep analysis costs a real API call, so it only happens when I click.

**Scoring is embeddings, not keywords.** A keyword filter for "transformer" or "robotics" misses papers that are relevant in substance but phrased differently, and lets through papers that just happen to share vocabulary. Cosine similarity between my research-interest text and each abstract captures meaning, not string matches.

**Supabase over local storage.** Earlier versions of this kept everything in a flat JSON file — cheap and dependency-free, but it meant the dashboard could only ever be "whatever the last GitHub Action run produced," with nowhere to persist chunk embeddings for the agent to query later. Moving to Postgres + pgvector cost a little in "fully free and local," but bought a real queryable store the agent can read from independently of the pipeline run.

**The agent handles rate limits as a first-class case, not an afterthought.** Free-tier Gemini quota gets hit. Rather than a generic error, the dashboard shows a countdown and disables the button until the quota window resets.

## Running it

You'll need a Supabase project (with the `vector` extension enabled) and a Gemini API key.

```bash
pip install -r requirements.txt
# set SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY (.env or environment)
python -m pipeline.run_pipeline   # populate the database once
streamlit run app.py              # launch the dashboard
```

The GitHub Actions workflow (`trigger.yml`) handles the recurring pipeline run — just add the same three secrets to your repo.

## Known limitations

- PDF text extraction is text-layer only — scanned/image-only PDFs fail silently and fall back to abstract-only analysis.
- The lookback window is fixed at 24 hours; a quiet arXiv cycle (e.g. weekends) can mean a thin or empty pull.
- Deep analysis is gated by whatever quota the free Gemini tier allows that day.
- `schema.sql` currently has a syntax error in the `chunks` table definition (missing closing paren) — fix before running it fresh.
