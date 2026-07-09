from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ContentItem:
    id: str
    source: str
    source_type: str
    title: str
    url: str
    content: str
    author: str | None = None
    author_followers: int = 0
    published_at: datetime = field(default_factory=datetime.now)
    score: float = 0.0
    comment_count: int = 0
    comments: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class ScoredIdea:
    item: ContentItem
    overall_score: float
    dimensions: dict[str, float]
    analysis: str
    spam_flag: bool = False
    spam_reason: str = ""
