import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import init_db, engine
from .models import Card
from .routes import router
from sqlmodel import Session, select

app = FastAPI(title="flashCards", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


SNAPSHOT = Path(__file__).resolve().parent.parent.parent / "seeds" / "snapshot.json"


def _seed_if_empty() -> None:
    if not SNAPSHOT.exists():
        return
    with Session(engine) as session:
        if session.exec(select(Card)).first():
            return
        cards = json.loads(SNAPSHOT.read_text())
        for data in cards:
            session.add(Card(
                topics=data.get("topics", []),
                question=data["question"],
                card_type=data.get("card_type", "multiple_choice"),
                options=data.get("options", []),
                correct_answer=data.get("correct_answer"),
                explanation=data.get("explanation"),
                difficulty=data.get("difficulty"),
            ))
        session.commit()
        print(f"[seed] imported {len(cards)} cards from snapshot.json")


@app.on_event("startup")
def _startup():
    init_db()
    _seed_if_empty()


@app.get("/healthz")
def health():
    return {"ok": True}


app.include_router(router)


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store"
        return response


WEB_DIR = Path(__file__).resolve().parent.parent / "web"
if WEB_DIR.exists():
    app.mount("/static", NoCacheStaticFiles(directory=WEB_DIR), name="static")

    @app.get("/")
    def index():
        response = FileResponse(WEB_DIR / "index.html")
        response.headers["Cache-Control"] = "no-store"
        return response
