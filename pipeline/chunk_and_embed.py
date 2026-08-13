import time
from typing import List
import requests
import fitz 

from config.settings import (
    ARXIV_PDF_URL_TEMPLATE,
    PDF_DOWNLOAD_TIMEOUT_SECONDS,
    PDF_DOWNLOAD_DELAY_SECONDS,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF_SECONDS,
)
from shared.models import Paper, Chunk
from shared.embeddings import EmbeddingModel
from db.supabase_client import SupabaseClient


def _download_pdf(arxiv_id: str) -> bytes:
    url = ARXIV_PDF_URL_TEMPLATE.format(arxiv_id=arxiv_id)
    last_error = None

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = requests.get(url, timeout=PDF_DOWNLOAD_TIMEOUT_SECONDS)
            response.raise_for_status()
            if not response.content:
                raise ValueError("PDF download returned empty content.")
            return response.content
        except Exception as e:
            last_error = e
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise RuntimeError(
        f"Failed to download PDF for {arxiv_id} after {RETRY_ATTEMPTS} "
        f"attempts. Last error: {last_error}"
    ) from last_error


def _extract_text(pdf_bytes: bytes) -> str:
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = "\n\n".join(page.get_text() for page in doc)
        doc.close()
    except Exception as e:
        raise RuntimeError(f"PyMuPDF failed to open/parse this PDF: {e}") from e

    if not full_text.strip():
        raise ValueError(
            "No extractable text found in PDF (likely a scanned/image-only "
            "document with no text layer)."
        )
    full_text = full_text.replace("\x00", "")

    return full_text


def _chunk_text(text: str) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(para) > CHUNK_SIZE:
            if current:
                chunks.append(current)
                current = ""
            step = CHUNK_SIZE - CHUNK_OVERLAP
            min_fragment_len = CHUNK_OVERLAP  
            for i in range(0, len(para), step):
                fragment = para[i:i + CHUNK_SIZE]
                if len(fragment) < min_fragment_len and chunks:
                    chunks[-1] = f"{chunks[-1]} {fragment}".strip()
                else:
                    chunks.append(fragment)
            continue

        if len(current) + len(para) + 1 <= CHUNK_SIZE:
            current = f"{current} {para}".strip()
        else:
            chunks.append(current)
            overlap_text = current[-CHUNK_OVERLAP:] if current else ""
            current = f"{overlap_text} {para}".strip()

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]


def process_paper(paper: Paper, db: SupabaseClient) -> bool:
    try:
        db_id = db.upsert_paper(paper)
    except Exception as e:
        print(f"[chunk_and_embed] Could not upsert paper {paper.arxiv_id}: {e}")
        return False

    try:
        pdf_bytes = _download_pdf(paper.arxiv_id)
        text = _extract_text(pdf_bytes)
        chunk_texts = _chunk_text(text)

        if not chunk_texts:
            raise ValueError("Chunking produced zero chunks from extracted text.")

        model = EmbeddingModel.get()
        vectors = model.embed(chunk_texts)

        chunk_objects = [
            Chunk(paper_id=db_id, chunk_text=t, embedding=v)
            for t, v in zip(chunk_texts, vectors)
        ]

        db.insert_chunks(chunk_objects)
        print(f"[chunk_and_embed] {paper.arxiv_id}: stored {len(chunk_objects)} chunks.")
        return True

    except Exception as e:
        print(f"[chunk_and_embed] Digest failed for {paper.arxiv_id}: {e}")
        return False


def chunk_and_embed_all(papers: List[Paper], db: SupabaseClient) -> None:
    if not papers:
        print("[chunk_and_embed] No papers to process — skipping.")
        return

    succeeded = 0
    for i, paper in enumerate(papers):
        try:
            if process_paper(paper, db):
                succeeded += 1
        except Exception as e:
            print(f"[chunk_and_embed] Unexpected error on {paper.arxiv_id}: {e}")

        if i < len(papers) - 1:
            time.sleep(PDF_DOWNLOAD_DELAY_SECONDS)

    print(f"[chunk_and_embed] Done: {succeeded}/{len(papers)} papers fully digested.")