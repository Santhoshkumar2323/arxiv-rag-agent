import json
import re
import time
from datetime import date, timedelta
from typing import List, Optional
from supabase import create_client, Client

from config.settings import (
    SUPABASE_URL,
    SUPABASE_KEY,
    RETENTION_DAYS,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF_SECONDS,
)
from shared.models import Paper, Chunk


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


def _with_retry(fn, description: str):
    last_error = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return fn()
        except Exception as e:
            last_error = e
            if attempt < RETRY_ATTEMPTS:
                wait = RETRY_BACKOFF_SECONDS * attempt
                time.sleep(wait)
    raise RuntimeError(
        f"{description} failed after {RETRY_ATTEMPTS} attempts. "
        f"Last error: {last_error}"
    ) from last_error


class SupabaseClient:
    _instance: Optional["SupabaseClient"] = None

    def __init__(self):
        try:
            self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            raise RuntimeError(
                f"Failed to create Supabase client. Check SUPABASE_URL and "
                f"SUPABASE_KEY are correct. Original error: {e}"
            ) from e

    @classmethod
    def get(cls) -> "SupabaseClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


    def upsert_paper(self, paper: Paper) -> str:
        row = paper.to_dict()
        row.pop("id", None)  
        def _do():
            result = (
                self.client.table("papers")
                .upsert(row, on_conflict="arxiv_id")
                .execute()
            )
            if not result.data:
                raise RuntimeError("Upsert returned no data.")
            return result.data[0]["id"]

        return _with_retry(_do, f"upsert_paper({paper.arxiv_id})")

    def get_recent_papers(self) -> List[Paper]:
        def _do():
            result = (
                self.client.table("papers")
                .select("*")
                .order("match_score", desc=True)
                .execute()
            )
            return [Paper(**row) for row in result.data]

        return _with_retry(_do, "get_recent_papers")

    def prune_old_papers(self) -> int:
        cutoff = (date.today() - timedelta(days=RETENTION_DAYS)).isoformat()

        def _do():
            result = (
                self.client.table("papers")
                .delete()
                .lt("published_date", cutoff)
                .execute()
            )
            return len(result.data)

        return _with_retry(_do, "prune_old_papers")


    def insert_chunks(self, chunks: List[Chunk]) -> int:
        if not chunks:
            return 0

        paper_id = chunks[0].paper_id
        if not _UUID_RE.match(paper_id):
            raise ValueError(
                f"Chunk.paper_id ('{paper_id}') doesn't look like a database "
                f"UUID. This usually means an arxiv_id was passed by mistake "
                f"instead of the id returned from upsert_paper(). Call "
                f"upsert_paper() first and use its returned id."
            )

        rows = []
        for c in chunks:
            row = c.to_dict()
            row.pop("id", None) 
            rows.append(row)

        def _do():
            result = self.client.table("chunks").insert(rows).execute()
            return len(result.data)

        return _with_retry(_do, f"insert_chunks(paper_id={chunks[0].paper_id})")

    def get_chunks_for_paper(self, paper_id: str) -> List[Chunk]:
        def _do():
            result = (
                self.client.table("chunks")
                .select("*")
                .eq("paper_id", paper_id)
                .execute()
            )
            
            processed_chunks = []
            for row in result.data:
                if isinstance(row.get("embedding"), str):
                    try:
                        row["embedding"] = json.loads(row["embedding"])
                    except Exception:
                        clean_str = row["embedding"].strip("[]").replace(" ", ",")
                        row["embedding"] = [float(x) for x in clean_str.split(",") if x]
                
                processed_chunks.append(Chunk(**row))
                
            return processed_chunks

        return _with_retry(_do, f"get_chunks_for_paper({paper_id})")
