from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Card(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    topics: list[str] = Field(sa_column=Column(JSON), default_factory=list)
    question: str
    card_type: str = Field(default="multiple_choice")
    options: list[str] = Field(sa_column=Column(JSON), default_factory=list)
    correct_answer: Optional[int] = Field(default=None)
    explanation: Optional[str] = Field(default=None)
    difficulty: Optional[str] = Field(default=None)
    next_review: datetime = Field(default_factory=utcnow, index=True)
    last_reviewed: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)
    ease_factor: float = Field(default=2.5)
    repetitions: int = Field(default=0)
    interval_days: int = Field(default=1)
