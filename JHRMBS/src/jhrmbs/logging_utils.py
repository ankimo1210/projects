from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from jhrmbs.util import timestamp_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(log_directory: Path, *, verbose: bool = False) -> Path:
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / f"jhrmbs-{timestamp_id()}.jsonl"
    root = logging.getLogger("jhrmbs")
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    root.addHandler(console)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())
    root.addHandler(file_handler)
    return log_path
