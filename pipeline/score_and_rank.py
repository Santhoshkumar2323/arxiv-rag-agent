from typing import List
from config.settings import TOP_N_PAPERS, RESEARCH_INTERESTS
from shared.embeddings import EmbeddingModel, cosine_similarity
from shared.models import Paper


def rank_papers(papers: List[Paper]) -> List[Paper]:
    if not papers:
        print("[score_and_rank] No papers to score — skipping.")
        return []

    model = EmbeddingModel.get()

    try:
        interest_vector = model.embed(RESEARCH_INTERESTS)
    except Exception as e:
        raise RuntimeError(
            f"Failed to embed RESEARCH_INTERESTS from settings.py. "
            f"Check that it's set to a non-empty string. Original error: {e}"
        ) from e

    abstracts = [p.abstract for p in papers]
    try:
        abstract_vectors = model.embed(abstracts)
    except Exception as e:
        raise RuntimeError(
            f"Failed to embed the batch of {len(abstracts)} abstracts. "
            f"Original error: {e}"
        ) from e

    scored = 0
    failed = 0
    for paper, vector in zip(papers, abstract_vectors):
        try:
            paper.match_score = cosine_similarity(interest_vector, vector)
            scored += 1
        except Exception as e:
            paper.match_score = 0.0
            failed += 1
            print(f"[score_and_rank] Failed to score '{paper.title[:60]}...': {e}")

    if failed:
        print(f"[score_and_rank] {failed}/{len(papers)} papers failed scoring "
              f"and were scored 0.0 (excluded from realistic ranking).")

    papers.sort(key=lambda p: p.match_score, reverse=True)
    top_papers = papers[:TOP_N_PAPERS]

    if top_papers:
        print(
            f"[score_and_rank] Kept top {len(top_papers)}/{len(papers)} papers. "
            f"Score range: {top_papers[-1].match_score:.3f} - "
            f"{top_papers[0].match_score:.3f}."
        )

    return top_papers