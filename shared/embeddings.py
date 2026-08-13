from typing import List, Union
import numpy as np
from config.settings import EMBEDDING_MODEL_NAME


class EmbeddingModel:
    _instance = None  

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers"
            ) from e

        try:
            self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load embedding model '{EMBEDDING_MODEL_NAME}'. "
                f"Check your internet connection (first run downloads the "
                f"model) and that the model name is correct. "
                f"Original error: {e}"
            ) from e

    @classmethod
    def get(cls) -> "EmbeddingModel":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def embed(
        self, text: Union[str, List[str]]
    ) -> Union[List[float], List[List[float]]]:
        if isinstance(text, str):
            if not text.strip():
                raise ValueError("Cannot embed an empty or blank string.")
            try:
                vector = self.model.encode(text)
                return self._to_list(vector)
            except Exception as e:
                raise RuntimeError(f"Embedding failed for input text: {e}") from e

        if isinstance(text, list):
            if len(text) == 0:
                raise ValueError("Cannot embed an empty list.")
            if any(not t.strip() for t in text):
                raise ValueError(
                    "One or more items in the list are empty/blank — "
                    "filter these out before calling embed()."
                )
            try:
                vectors = self.model.encode(text)
                return [self._to_list(v) for v in vectors]
            except Exception as e:
                raise RuntimeError(f"Embedding failed for input batch: {e}") from e

        raise TypeError(
            f"embed() expects a str or List[str], got {type(text).__name__}."
        )

    @staticmethod
    def _to_list(vector) -> List[float]:
        if isinstance(vector, np.ndarray):
            return vector.tolist()
        return list(vector)


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    a = np.array(vec_a)
    b = np.array(vec_b)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        raise ValueError(
            "Cannot compute cosine similarity against a zero-vector "
            "(likely an embedding that failed silently upstream)."
        )

    raw_score = float(np.dot(a, b) / (norm_a * norm_b))
    return max(0.0, min(1.0, raw_score))