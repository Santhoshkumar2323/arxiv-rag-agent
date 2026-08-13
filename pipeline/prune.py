from config.settings import RETENTION_DAYS
from db.supabase_client import SupabaseClient

def prune_old_papers(db: SupabaseClient) -> int:
    try:
        deleted_count = db.prune_old_papers()
        print(
            f"[prune] Removed {deleted_count} paper(s) older than "
            f"{RETENTION_DAYS} days (chunks cascaded automatically)."
        )
        return deleted_count
    except Exception as e:
        print(
            f"[prune] Failed to prune old papers — will retry on the next "
            f"nightly run. Error: {e}"
        )
        return 0