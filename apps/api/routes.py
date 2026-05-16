from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from .database import get_session
from .models import Card, utcnow
from .schemas import CardCreate, CardOut, CardUpdate, ReviewIn
from .review import schedule_next

router = APIRouter(prefix="/api")


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _to_out(card: Card) -> CardOut:
    return CardOut(
        id=card.id,
        topics=card.topics or [],
        question=card.question,
        options=card.options or [],
        correct_answer=card.correct_answer,
        explanation=card.explanation,
        difficulty=card.difficulty,
        next_review=_ensure_aware(card.next_review),
        last_reviewed=_ensure_aware(card.last_reviewed) if card.last_reviewed else None,
        created_at=_ensure_aware(card.created_at),
        ease_factor=card.ease_factor if card.ease_factor is not None else 2.5,
        repetitions=card.repetitions or 0,
        interval_days=card.interval_days or 1,
    )


@router.get("/cards", response_model=list[CardOut])
def list_cards(
    session: Session = Depends(get_session),
    topic_path: Optional[str] = Query(None, description="slash-separated topic prefix, e.g. frontend/vue"),
    due_only: bool = False,
):
    stmt = select(Card)
    cards = session.exec(stmt).all()

    if topic_path:
        prefix = [p for p in topic_path.split("/") if p]
        cards = [c for c in cards if (c.topics or [])[: len(prefix)] == prefix]

    if due_only:
        now = utcnow()
        cards = [c for c in cards if _ensure_aware(c.next_review) <= now]

    cards.sort(key=lambda c: _ensure_aware(c.next_review))
    return [_to_out(c) for c in cards]


@router.get("/cards/due", response_model=list[CardOut])
def due_cards(session: Session = Depends(get_session), topic_path: Optional[str] = None):
    return list_cards(session=session, topic_path=topic_path, due_only=True)


@router.get("/cards/{card_id}", response_model=CardOut)
def get_card(card_id: int, session: Session = Depends(get_session)):
    card = session.get(Card, card_id)
    if not card:
        raise HTTPException(404, "card not found")
    return _to_out(card)


@router.post("/cards", response_model=CardOut, status_code=201)
def create_card(payload: CardCreate, session: Session = Depends(get_session)):
    card = Card(
        topics=payload.topics,
        question=payload.question.strip(),
        options=payload.options,
        correct_answer=payload.correct_answer,
        explanation=payload.explanation,
        difficulty=payload.difficulty,
    )
    session.add(card)
    session.commit()
    session.refresh(card)
    return _to_out(card)


@router.put("/cards/{card_id}", response_model=CardOut)
def update_card(card_id: int, payload: CardUpdate, session: Session = Depends(get_session)):
    card = session.get(Card, card_id)
    if not card:
        raise HTTPException(404, "card not found")

    data = payload.model_dump(exclude_unset=True)
    if "options" in data or "correct_answer" in data:
        new_options = data.get("options", card.options)
        new_correct = data.get("correct_answer", card.correct_answer)
        if len(new_options) < 2:
            raise HTTPException(400, "at least 2 options required")
        if not (0 <= new_correct < len(new_options)):
            raise HTTPException(400, "correct_answer index out of range")

    for k, v in data.items():
        setattr(card, k, v)

    session.add(card)
    session.commit()
    session.refresh(card)
    return _to_out(card)


@router.delete("/cards/{card_id}", status_code=204)
def delete_card(card_id: int, session: Session = Depends(get_session)):
    card = session.get(Card, card_id)
    if not card:
        raise HTTPException(404, "card not found")
    session.delete(card)
    session.commit()


@router.post("/cards/{card_id}/review", response_model=CardOut)
def review_card(card_id: int, payload: ReviewIn, session: Session = Depends(get_session)):
    card = session.get(Card, card_id)
    if not card:
        raise HTTPException(404, "card not found")

    next_review, last_reviewed, ef, reps, interval = schedule_next(
        payload.difficulty,
        payload.correct,
        card.ease_factor if card.ease_factor is not None else 2.5,
        card.repetitions or 0,
        card.interval_days or 1,
    )
    card.next_review = next_review
    card.last_reviewed = last_reviewed
    card.difficulty = payload.difficulty
    card.ease_factor = ef
    card.repetitions = reps
    card.interval_days = interval

    session.add(card)
    session.commit()
    session.refresh(card)
    return _to_out(card)


@router.get("/export")
def export_cards(session: Session = Depends(get_session)):
    cards = session.exec(select(Card)).all()
    return [
        {
            "topics": card.topics or [],
            "question": card.question,
            "options": card.options or [],
            "correct_answer": card.correct_answer,
            "explanation": card.explanation,
            "difficulty": card.difficulty,
        }
        for card in cards
    ]


@router.get("/stats")
def get_stats(session: Session = Depends(get_session)):
    cards = session.exec(select(Card)).all()
    now = utcnow()

    def _stats(card_list):
        total = len(card_list)
        due = sum(1 for c in card_list if _ensure_aware(c.next_review) <= now)
        new = sum(1 for c in card_list if c.last_reviewed is None)
        mature = sum(1 for c in card_list if (c.interval_days or 1) >= 21)
        avg_ef = round(sum(c.ease_factor or 2.5 for c in card_list) / total, 2) if total else 0.0
        return {"total": total, "due": due, "new": new, "mature": mature, "avg_ease": avg_ef}

    by_topic: dict[str, list] = {}
    for card in cards:
        path = "/".join(card.topics or []) or "(sem tópico)"
        by_topic.setdefault(path, []).append(card)

    return {
        **_stats(cards),
        "topics": [{"path": p, **_stats(cl)} for p, cl in sorted(by_topic.items())],
    }


@router.get("/topics")
def topics_tree(session: Session = Depends(get_session)):
    cards = session.exec(select(Card)).all()
    tree: dict = {}
    for card in cards:
        node = tree
        for part in card.topics or []:
            node = node.setdefault(part, {"_count": 0, "_children": {}})["_children"]
        # bump counts up the path
        node = tree
        for part in card.topics or []:
            node[part]["_count"] += 1
            node = node[part]["_children"]
    return tree
