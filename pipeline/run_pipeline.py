import sys
import time
from pipeline.fetch_arxiv import fetch_recent_papers
from pipeline.score_and_rank import rank_papers
from pipeline.chunk_and_embed import chunk_and_embed_all
from pipeline.prune import prune_old_papers
from db.supabase_client import SupabaseClient


def main() -> int:
    start = time.time()
    print("=" * 60)
    print("[run_pipeline] Starting nightly run.")
    print("=" * 60)
    try:
        papers = fetch_recent_papers()
    except Exception as e:
        print(f"[run_pipeline] HARD FAILURE at fetch stage: {e}")
        return 1

    print(f"[run_pipeline] Fetched {len(papers)} candidate paper(s).")

    try:
        top_papers = rank_papers(papers)
    except Exception as e:
        print(f"[run_pipeline] Scoring stage failed: {e}")
        top_papers = []

    db = SupabaseClient.get()
    try:
        chunk_and_embed_all(top_papers, db)
    except Exception as e:
        print(f"[run_pipeline] Chunk/embed stage failed unexpectedly: {e}")

    prune_old_papers(db)

    elapsed = time.time() - start
    print("=" * 60)
    print(f"[run_pipeline] Run complete in {elapsed:.1f}s.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception as e:
        print(f"[run_pipeline] UNEXPECTED CRASH: {e}")
        exit_code = 1

    sys.exit(exit_code)