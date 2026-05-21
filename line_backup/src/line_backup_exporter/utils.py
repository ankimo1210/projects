from __future__ import annotations
import csv
import logging
import sys
from pathlib import Path
from typing import Iterable, Sequence


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(handler)
    return logger


def write_csv(path: Path, rows: Iterable[Sequence], headers: Sequence[str]) -> int:
    """Write rows to CSV, return number of data rows written."""
    count = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def print_table(headers: list[str], rows: list[list]) -> None:
    """Simple text table to stdout."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers))
    print("  ".join("-" * w for w in col_widths))
    for row in rows:
        print(fmt.format(*[str(c) for c in row]))
