from __future__ import annotations
import csv
import shutil
from pathlib import Path

from .manifest import resolve_blob_path
from .safety import confirm_output_dir, ensure_within_directory, safe_filename, unique_path
from .utils import get_logger, write_csv

logger = get_logger(__name__)

_SQLITE_EXTENSIONS = (".sqlite", ".db", ".sqlite3")


def _is_sqlite_candidate(relative_path: str) -> bool:
    rp_lower = relative_path.lower()
    if any(rp_lower.endswith(ext) for ext in _SQLITE_EXTENSIONS):
        return True
    # Also catch files without extension but named Line.sqlite etc. inside path
    if "line.sqlite" in rp_lower:
        return True
    return False


def extract_candidates(
    backup_dir: Path,
    manifest_csv: Path,
    out_dir: Path,
) -> list[dict]:
    """Copy SQLite candidate files from backup to out_dir/extracted/."""
    if not manifest_csv.exists():
        raise FileNotFoundError(f"manifest CSV not found: {manifest_csv}")

    extracted_dir = confirm_output_dir(out_dir / "extracted")
    index: list[dict] = []

    with manifest_csv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    candidates = [r for r in rows if _is_sqlite_candidate(r.get("relative_path", ""))]
    logger.info("Found %d SQLite candidate(s) in manifest CSV.", len(candidates))

    for row in candidates:
        file_id = row.get("file_id", "").strip()
        domain = row.get("domain", "").strip()
        relative_path = row.get("relative_path", "").strip()

        if not file_id:
            logger.warning("Skipping entry with empty fileID: %s", relative_path)
            continue

        src = resolve_blob_path(backup_dir, file_id)

        try:
            src = ensure_within_directory(backup_dir, src)
        except ValueError as e:
            logger.warning("Skipping unsafe path for %s: %s", file_id, e)
            continue

        if not src.exists():
            logger.warning("Blob file not found (may be absent in partial backup): %s", src)
            continue

        # Build a readable destination filename
        basename = Path(relative_path).name if relative_path else file_id
        dst_name = safe_filename(f"{domain}__{basename}")
        if not Path(dst_name).suffix:
            dst_name += ".sqlite"
        dst = unique_path(extracted_dir / dst_name)

        shutil.copy2(src, dst)
        logger.info("Copied %s → %s", src.name, dst.name)

        index.append({
            "original_relative_path": relative_path,
            "domain": domain,
            "file_id": file_id,
            "copied_to": str(dst),
        })

    # Write index CSV
    index_path = out_dir / "extracted_index.csv"
    write_csv(
        index_path,
        [[r["original_relative_path"], r["domain"], r["file_id"], r["copied_to"]] for r in index],
        ["original_relative_path", "domain", "file_id", "copied_to"],
    )
    logger.info("Wrote extraction index to %s", index_path)

    return index
