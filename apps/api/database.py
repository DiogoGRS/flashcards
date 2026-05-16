import os
from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/flashcards.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def _ensure_columns() -> None:
    with engine.begin() as conn:
        col_info = conn.exec_driver_sql("PRAGMA table_info(card)").fetchall()
        if not col_info:
            return
        cols = {row[1] for row in col_info}

        migrations = [
            ("explanation", "ALTER TABLE card ADD COLUMN explanation TEXT"),
            ("ease_factor", "ALTER TABLE card ADD COLUMN ease_factor REAL DEFAULT 2.5"),
            ("repetitions", "ALTER TABLE card ADD COLUMN repetitions INTEGER DEFAULT 0"),
            ("interval_days", "ALTER TABLE card ADD COLUMN interval_days INTEGER DEFAULT 1"),
            ("card_type", "ALTER TABLE card ADD COLUMN card_type TEXT DEFAULT 'multiple_choice'"),
        ]
        for col, sql in migrations:
            if col not in cols:
                conn.execute(text(sql))

        # Make correct_answer nullable if it still has NOT NULL constraint
        correct_notnull = next((row[3] for row in col_info if row[1] == "correct_answer"), 0)
        if correct_notnull:
            conn.execute(text("""
                CREATE TABLE card_new (
                    id INTEGER PRIMARY KEY,
                    topics JSON DEFAULT '[]',
                    question TEXT NOT NULL,
                    card_type TEXT DEFAULT 'multiple_choice',
                    options JSON DEFAULT '[]',
                    correct_answer INTEGER,
                    explanation TEXT,
                    difficulty TEXT,
                    next_review DATETIME NOT NULL,
                    last_reviewed DATETIME,
                    created_at DATETIME NOT NULL,
                    ease_factor REAL DEFAULT 2.5,
                    repetitions INTEGER DEFAULT 0,
                    interval_days INTEGER DEFAULT 1
                )
            """))
            conn.execute(text("""
                INSERT INTO card_new
                SELECT id, topics, question,
                       COALESCE(card_type, 'multiple_choice'),
                       options, correct_answer, explanation, difficulty,
                       next_review, last_reviewed, created_at,
                       COALESCE(ease_factor, 2.5),
                       COALESCE(repetitions, 0),
                       COALESCE(interval_days, 1)
                FROM card
            """))
            conn.execute(text("DROP TABLE card"))
            conn.execute(text("ALTER TABLE card_new RENAME TO card"))


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
