from datetime import timedelta
from .models import utcnow

INTERVALS = {
    "easy": timedelta(days=7),
    "medium": timedelta(days=3),
    "hard": timedelta(days=1),
}


def schedule_next(difficulty: str, correct: bool | None):
    now = utcnow()
    if correct is False:
        return now + timedelta(hours=4), now
    return now + INTERVALS[difficulty], now
