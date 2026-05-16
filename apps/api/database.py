import os
from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/flashcards.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def _ensure_columns() -> None:
    with engine.begin() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(card)").fetchall()}
        if not cols:
            return
        migrations = [
            ("explanation", "ALTER TABLE card ADD COLUMN explanation TEXT"),
            ("ease_factor", "ALTER TABLE card ADD COLUMN ease_factor REAL DEFAULT 2.5"),
            ("repetitions", "ALTER TABLE card ADD COLUMN repetitions INTEGER DEFAULT 0"),
            ("interval_days", "ALTER TABLE card ADD COLUMN interval_days INTEGER DEFAULT 1"),
        ]
        for col, sql in migrations:
            if col not in cols:
                conn.execute(text(sql))


def init_db() -> None:
    if DATABASE_URL.startswith("sqlite:///"):
        path = DATABASE_URL.replace("sqlite:///", "", 1)
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    if DATABASE_URL.startswith("sqlite"):
        _ensure_columns()


def get_session():
    with Session(engine) as session:
        yield session
