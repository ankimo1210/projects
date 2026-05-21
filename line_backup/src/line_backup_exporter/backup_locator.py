from __future__ import annotations

import os
import platform
import plistlib
from datetime import datetime
from pathlib import Path

from .models import BackupInfo
from .utils import get_logger

logger = get_logger(__name__)


def _candidate_dirs() -> list[Path]:
    candidates: list[Path] = []
    system = platform.system()

    if system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        userprofile = os.environ.get("USERPROFILE", "")
        localappdata = os.environ.get("LOCALAPPDATA", "")

        if appdata:
            candidates.append(Path(appdata) / "Apple Computer" / "MobileSync" / "Backup")
        if userprofile:
            candidates.append(Path(userprofile) / "Apple" / "MobileSync" / "Backup")
        if localappdata:
            # iTunes Store app (UWP) — wildcard for package name
            (
                Path(localappdata)
                / "Packages"
                / "AppleInc.iTunes_*"
                / "LocalCache"
                / "Roaming"
                / "Apple Computer"
                / "MobileSync"
                / "Backup"
            )
            candidates.extend(
                Path(localappdata).glob(
                    "Packages/AppleInc.iTunes_*/LocalCache/Roaming/Apple Computer/MobileSync/Backup"
                )
            )
    elif system == "Darwin":
        candidates.append(Path.home() / "Library" / "Application Support" / "MobileSync" / "Backup")
    else:
        # Linux / WSL — check Windows paths via /mnt/c as fallback
        win_user = os.environ.get("WIN_USERPROFILE", "")
        if win_user:
            win_path = Path(win_user)
            candidates.append(
                win_path / "AppData" / "Roaming" / "Apple Computer" / "MobileSync" / "Backup"
            )
            candidates.append(win_path / "Apple" / "MobileSync" / "Backup")

    return candidates


def _read_is_encrypted(backup_dir: Path) -> bool:
    plist_path = backup_dir / "Manifest.plist"
    if not plist_path.exists():
        return False
    try:
        with plist_path.open("rb") as f:
            data = plistlib.load(f)
        return bool(data.get("IsEncrypted", False))
    except Exception as e:
        logger.warning("Could not read Manifest.plist at %s: %s", plist_path, e)
        return False


def _mtime_str(path: Path) -> str:
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except OSError:
        return "unknown"


def list_backups() -> list[BackupInfo]:
    results: list[BackupInfo] = []
    seen: set[Path] = set()

    for base in _candidate_dirs():
        if not base.exists():
            continue
        # Each subdirectory directly under the backup root is one backup
        try:
            entries = list(base.iterdir())
        except PermissionError as e:
            logger.warning("Cannot read %s: %s", base, e)
            continue

        for entry in entries:
            if not entry.is_dir():
                continue
            resolved = entry.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)

            has_db = (entry / "Manifest.db").exists()
            has_plist = (entry / "Manifest.plist").exists()
            encrypted = _read_is_encrypted(entry)
            updated = _mtime_str(entry / "Manifest.db") if has_db else _mtime_str(entry)

            results.append(
                BackupInfo(
                    backup_id=entry.name,
                    path=entry,
                    updated_at=updated,
                    has_manifest_db=has_db,
                    has_manifest_plist=has_plist,
                    likely_encrypted=encrypted,
                )
            )

    return results
