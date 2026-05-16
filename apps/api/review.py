from datetime import timedelta
from .models import utcnow

# SM-2 quality mapping
_QUALITY = {"easy": 5, "medium": 3, "hard": 2}


def schedule_next(
    difficulty: str,
    correct: bool | None,
    ease_factor: float,
    repetitions: int,
    interval_days: int,
) -> tuple:
    now = utcnow()
    quality = 0 if correct is False else _QUALITY.get(difficulty, 3)

    if quality >= 3:
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(interval_days * ease_factor)
        new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ef = max(1.3, new_ef)
        new_reps = repetitions + 1
    else:
        new_interval = 1
        new_ef = max(1.3, ease_factor - 0.2)
        new_reps = 0

    return now + timedelta(days=new_interval), now, round(new_ef, 4), new_reps, new_interval
