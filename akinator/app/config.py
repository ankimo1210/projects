"""Filesystem paths for akinator data and DB. Single source of truth."""
from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
ENTITIES_PATH = PROCESSED_DIR / "entities.json"
QUESTIONS_PATH = PROCESSED_DIR / "questions.json"
DB_PATH = PROJECT_DIR / "akinator.db"
