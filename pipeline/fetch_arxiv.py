import time
from datetime import datetime, timedelta, timezone
import requests
import feedparser

from config.settings import (
    ARXIV_API_BASE_URL,
    ARXIV_CATEGORIES,
    ARXIV_LOOKBACK_HOURS,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF_SECONDS,
)
from shared.models import Paper


def _build_query() -> dict:
    category_query = " OR ".join(f"cat:{cat}" for cat in ARXIV_CATEGORIES)
    return {
        "search_query": category_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": 500, 
    }


def _fetch_raw_entries() -> list:
    params = _build_query()
    last_error = None

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = requests.get(ARXIV_API_BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            feed = feedparser.parse(response.text)

            if feed.bozo and not feed.entries:
                raise ValueError(f"arXiv returned unparseable feed: {feed.bozo_exception}")

            return feed.entries

        except Exception as e:
            last_error = e
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise RuntimeError(
        f"Failed to fetch from arXiv after {RETRY_ATTEMPTS} attempts. "
        f"Last error: {last_error}"
    ) from last_error


def _extract_arxiv_id(entry_id_url: str) -> str:
    raw_id = entry_id_url.rstrip("/").split("/")[-1]
    if "v" in raw_id:
        base, _, version = raw_id.rpartition("v")
        if version.isdigit():
            return base
    return raw_id


def fetch_recent_papers() -> list:
    entries = _fetch_raw_entries()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ARXIV_LOOKBACK_HOURS)

    papers = []
    skipped = 0

    for entry in entries:
        try:
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if published < cutoff:
                break

            title = " ".join(getattr(entry, "title", "").split())
            abstract = " ".join(getattr(entry, "summary", "").split())
            link = getattr(entry, "link", "").strip()

            if not title or not abstract or not link:
                skipped += 1
                continue

            paper = Paper(
                title=title,
                abstract=abstract,
                link=link,
                arxiv_id=_extract_arxiv_id(entry.id),
                published_date=published.date(),
                match_score=None,
            )
            papers.append(paper)

        except Exception:
            skipped += 1
            continue

    if skipped:
        print(f"[fetch_arxiv] Skipped {skipped} malformed/incomplete entries.")

    if not papers:
        print(
            "[fetch_arxiv] No papers found in the lookback window. "
            "This is expected on arXiv's quiet weekend cycles — "
            "not necessarily an error."
        )
        return []

    return papers