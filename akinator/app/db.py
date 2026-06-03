"""SQLite persistence for game history and corrections (future training data).
Entities/questions are NOT stored here — they load from JSON."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'active',
    guessed_entity_id TEXT,
    was_correct INTEGER
);
CREATE TABLE IF NOT EXISTS game_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id),
    question_id TEXT NOT NULL,
    answer TEXT NOT NULL,
    asked_order INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id),
    correct_entity TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    with closing(_connect(db_path)) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


def create_game(db_path: Path) -> int:
    with closing(_connect(db_path)) as conn:
        cur = conn.execute("INSERT INTO games DEFAULT VALUES")
        conn.commit()
        return int(cur.lastrowid)


def save_answer(db_path: Path, game_id: int, question_id: str, answer: str,
                asked_order: int) -> None:
    with closing(_connect(db_path)) as conn:
        conn.execute(
            "INSERT INTO game_answers (game_id, question_id, answer, asked_order) "
            "VALUES (?, ?, ?, ?)",
            (game_id, question_id, answer, asked_order),
        )
        conn.commit()


def finish_game(db_path: Path, game_id: int, guessed_entity_id: str,
                was_correct: bool) -> None:
    with closing(_connect(db_path)) as conn:
        conn.execute(
            "UPDATE games SET status='finished', guessed_entity_id=?, was_correct=? "
            "WHERE id=?",
            (guessed_entity_id, 1 if was_correct else 0, game_id),
        )
        conn.commit()


def save_correction(db_path: Path, game_id: int, correct_entity: str) -> None:
    with closing(_connect(db_path)) as conn:
        conn.execute(
            "INSERT INTO corrections (game_id, correct_entity) VALUES (?, ?)",
            (game_id, correct_entity),
        )
        conn.commit()


def get_game_answers(db_path: Path, game_id: int) -> list[dict]:
    with closing(_connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT question_id, answer, asked_order FROM game_answers "
            "WHERE game_id=? ORDER BY asked_order",
            (game_id,),
        ).fetchall()
        return [dict(r) for r in rows]
