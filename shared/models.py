from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import List, Optional, Union

@dataclass
class Paper:
    title: str
    abstract: str
    link: str
    arxiv_id: str
    published_date: Union[date, str]
    match_score: Optional[float] = None
    id: Optional[str] = None 

    def __post_init__(self):
        if not self.arxiv_id:
            raise ValueError("Paper requires a non-empty arxiv_id.")

        if self.match_score is not None and not (0.0 <= self.match_score <= 1.0):
            raise ValueError(
                f"match_score must be between 0 and 1, got {self.match_score}."
            )

        if isinstance(self.published_date, str):
            try:
                self.published_date = datetime.fromisoformat(
                    self.published_date
                ).date()
            except ValueError as e:
                raise ValueError(
                    f"published_date string '{self.published_date}' is not a "
                    f"valid ISO date/datetime."
                ) from e

    def to_dict(self) -> dict:
        d = asdict(self)
        d["published_date"] = self.published_date.isoformat()
        return d


@dataclass
class Chunk:
    paper_id: str
    chunk_text: str
    embedding: List[float] = field(default_factory=list)
    id: Optional[str] = None  

    def __post_init__(self):
        if not self.chunk_text.strip():
            raise ValueError("Chunk cannot be created from empty text.")

        if self.embedding and not isinstance(self.embedding, list):
            raise TypeError(
                f"Chunk.embedding must be a list, got "
                f"{type(self.embedding).__name__}. Call EmbeddingModel.embed() "
                f"(which returns plain lists) rather than passing a raw "
                f"numpy array."
            )

    def to_dict(self) -> dict:
        return asdict(self)