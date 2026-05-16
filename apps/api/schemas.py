from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator

Difficulty = Literal["easy", "medium", "hard"]
CardType = Literal["multiple_choice", "reveal"]


class CardCreate(BaseModel):
    topics: list[str] = Field(default_factory=list)
    question: str
    card_type: CardType = "multiple_choice"
    options: list[str] = Field(default_factory=list)
    correct_answer: Optional[int] = None
    explanation: Optional[str] = None
    difficulty: Optional[Difficulty] = None

    @model_validator(mode="after")
    def _check(self):
        if not self.question.strip():
            raise ValueError("question is required")
        if self.card_type == "multiple_choice":
            if len(self.options) < 2:
                raise ValueError("at least 2 options required")
            if self.correct_answer is None or not (0 <= self.correct_answer < len(self.options)):
                raise ValueError("correct_answer index out of range")
        return self


class CardUpdate(BaseModel):
    topics: Optional[list[str]] = None
    question: Optional[str] = None
    card_type: Optional[CardType] = None
    options: Optional[list[str]] = None
    correct_answer: Optional[int] = None
    explanation: Optional[str] = None
    difficulty: Optional[Difficulty] = None


class CardOut(BaseModel):
    id: int
    topics: list[str]
    question: str
    card_type: str
    options: list[str]
    correct_answer: Optional[int]
    explanation: Optional[str]
    difficulty: Optional[str]
    next_review: datetime
    last_reviewed: Optional[datetime]
    created_at: datetime
    ease_factor: float
    repetitions: int
    interval_days: int


class ReviewIn(BaseModel):
    difficulty: Difficulty
    correct: Optional[bool] = None
