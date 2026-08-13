import time
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from config.settings import (
    GEMINI_API_KEY,
    LLM_MODEL_NAME,
    MAX_CHUNKS_PER_QUERY,
    MAX_OUTPUT_TOKENS,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF_SECONDS,
)
from agent.prompts import QUESTION_VECTOR, PROMPT_TEMPLATE
from shared.embeddings import cosine_similarity
from db.supabase_client import SupabaseClient

genai.configure(api_key=GEMINI_API_KEY)
_llm = genai.GenerativeModel(LLM_MODEL_NAME)

def retrieve_chunks(state: dict) -> dict:
    db = SupabaseClient.get()

    try:
        chunks = db.get_chunks_for_paper(state["paper_id"])
    except Exception as e:
        state["chunks"] = []
        state["error"] = f"Failed to fetch chunks: {e}"
        return state

    scored = []
    skipped = 0
    for chunk in chunks:
        try:
            score = cosine_similarity(QUESTION_VECTOR, chunk.embedding)
            scored.append((score, chunk))
        except Exception:
            skipped += 1
            continue

    if skipped:
        print(f"[retrieve_chunks] Skipped {skipped} chunk(s) with invalid embeddings.")

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top_chunks = [c for _, c in scored[:MAX_CHUNKS_PER_QUERY]]

    state["chunks"] = top_chunks
    if top_chunks:
        state["context"] = "\n\n".join(c.chunk_text for c in top_chunks)
    return state


def should_use_fallback(state: dict) -> str:
    if state.get("chunks"):
        return "generate"
    return "fallback"


def fallback_to_abstract(state: dict) -> dict:
    state["context"] = state["abstract"]
    state["used_fallback"] = True
    return state


_thinking_disabled = False

def _build_generation_config():
    global _thinking_disabled
    try:
        config = genai.types.GenerationConfig(
            max_output_tokens=MAX_OUTPUT_TOKENS,
            thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
        )
        _thinking_disabled = True
        return config
    except (AttributeError, TypeError) as e:
        if not _thinking_disabled:
            print(
                f"[generate_explanation] NOTICE: thinking_config is not "
                f"supported by the installed google-generativeai SDK "
                f"version ({e}). Falling back to MAX_OUTPUT_TOKENS="
                f"{MAX_OUTPUT_TOKENS} alone — thinking tokens will still "
                f"consume part of this budget, so output length may vary."
            )
        return genai.types.GenerationConfig(max_output_tokens=MAX_OUTPUT_TOKENS)


def _extract_text(response) -> str:
    try:
        if response.text:
            return response.text
    except Exception:
        pass 

    try:
        candidate = response.candidates[0]
        parts = candidate.content.parts
        visible = [
            p.text for p in parts
            if getattr(p, "text", None) and not getattr(p, "thought", False)
        ]
        return "".join(visible)
    except Exception:
        return ""


DEFAULT_RATE_LIMIT_RETRY_SECONDS = 60


def _extract_retry_delay_seconds(e: Exception) -> int:
    """Google's 429 errors sometimes carry their own suggested wait time
    (e.retry_delay, a timedelta). Use it when present; otherwise fall back
    to a sane default so the UI always has something concrete to show."""
    retry_delay = getattr(e, "retry_delay", None)
    if retry_delay is not None:
        try:
            seconds = int(retry_delay.total_seconds())
            if seconds > 0:
                return seconds
        except Exception:
            pass
    return DEFAULT_RATE_LIMIT_RETRY_SECONDS


def generate_explanation(state: dict) -> dict:
    prompt = PROMPT_TEMPLATE.format(context=state["context"])
    generation_config = _build_generation_config()
    last_error = None

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = _llm.generate_content(
                prompt,
                generation_config=generation_config,
            )

            finish_reason = None
            if response.candidates:
                finish_reason = str(response.candidates[0].finish_reason)
                usage = getattr(response, "usage_metadata", None)
                print(
                    f"[generate_explanation] finish_reason={finish_reason} "
                    f"thinking_disabled={_thinking_disabled} "
                    f"usage={usage}"
                )
                if "MAX_TOKENS" in finish_reason:
                    print(
                        f"[generate_explanation] WARNING: response hit the "
                        f"token limit. Output may be truncated. Consider "
                        f"raising MAX_OUTPUT_TOKENS in settings.py."
                    )

            text = _extract_text(response)
            if not text:
                raise ValueError(
                    f"Gemini returned no visible text (finish_reason="
                    f"{finish_reason})."
                )

            state["explanation"] = text
            return state
        except ResourceExhausted as e:
            # Free-tier quota/rate limit hit. Retrying immediately won't
            # help — surface a clear, actionable wait time instead.
            retry_after = _extract_retry_delay_seconds(e)
            print(
                f"[generate_explanation] Rate limited (ResourceExhausted). "
                f"Suggested retry_after={retry_after}s."
            )
            state["rate_limited"] = True
            state["retry_after_seconds"] = retry_after
            state["explanation"] = (
                f"⏳ We've hit the free-tier limit for the LLM right now. "
                f"Try again in about {retry_after} seconds."
            )
            state["error"] = "rate_limited"
            return state
        except Exception as e:
            last_error = e
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    state["explanation"] = (
        "⚠️ Analysis failed after multiple attempts. This is usually a "
        "temporary issue with the LLM service — try clicking the button "
        f"again shortly. (Details: {last_error})"
    )
    state["error"] = str(last_error)
    return state