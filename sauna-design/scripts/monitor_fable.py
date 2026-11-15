"""Inspect only this Fable job and preserve its real conversation."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from dispatch_fable import DATA, MANIFEST, ROOT, SESSION_DIR


def normalize_paths(text: str) -> str:
    def convert(match: re.Match[str]) -> str:
        return subprocess.check_output(["wslpath", "-w", match.group(0)], text=True).strip()

    return re.sub(r"/(?:home/kazumasa|mnt/[a-z])/[^\s`'\"<>()]*", convert, text)


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cli = manifest["cli_executable"]
    agents = json.loads(
        subprocess.check_output(
            [cli, "agents", "--json", "--cwd", str(ROOT), "--all"], text=True, timeout=20
        )
    )
    job = next(
        (item for item in agents if item.get("id") == manifest.get("native_background_id")), None
    )
    if job is None:
        job = next((item for item in agents if item.get("name") == manifest["name"]), None)
    if job is None:
        raise SystemExit(
            "The scoped Fable agent was not found. Preserved files were left unchanged."
        )
    actual_id = job["sessionId"]
    if manifest["conversation_id"] != actual_id:
        manifest["bootstrap_requested_conversation_id"] = manifest["conversation_id"]
    manifest.update(conversation_id=actual_id, native_background_id=job["id"])
    session = (
        Path.home()
        / ".claude"
        / "projects"
        / "-home-kazumasa-projects-sauna-design"
        / f"{actual_id}.jsonl"
    )
    models: set[str] = set()
    tools: list[str] = []
    actions: list[dict] = []
    visible: list[str] = []
    if session.exists():
        for line in session.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "assistant":
                continue
            message = event.get("message", {})
            if message.get("model") and not message["model"].startswith("<"):
                models.add(message["model"])
            for block in message.get("content", []):
                if block.get("type") == "tool_use":
                    tools.append(block.get("name", "unknown"))
                    payload = block.get("input", {})
                    actions.append(
                        {
                            "tool": block.get("name"),
                            "description": payload.get("description", "")[:250],
                            "file": normalize_paths(payload.get("file_path", "")),
                        }
                    )
                elif block.get("type") == "text":
                    visible.append(block.get("text", ""))
        backup = SESSION_DIR / f"{actual_id}.jsonl"
        shutil.copy2(session, backup)
        manifest.update(
            session_file=str(session),
            session_backup=str(backup),
            session_snapshot_at_utc=datetime.now(UTC).isoformat(),
            session_saved=True,
            session_snapshot_is_live=job.get("status") in {"busy", "running"},
        )
    manifest["last_agent_state"] = {key: job.get(key) for key in ("status", "state", "pid")}
    manifest["models_seen"] = sorted(models)
    status_path = ROOT / "docs" / "STATUS.md"
    status_text = status_path.read_text(encoding="utf-8") if status_path.exists() else ""
    status_hash = hashlib.sha256(status_text.encode()).hexdigest()
    status_changed = status_hash != manifest.get("status_doc_sha256")
    manifest["status_doc_sha256"] = status_hash
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_windows = subprocess.check_output(["wslpath", "-w", str(ROOT)], text=True).strip()
    data_windows = subprocess.check_output(["wslpath", "-w", str(SESSION_DIR)], text=True).strip()
    (ROOT / "docs" / "FABLE_SESSION.md").write_text(
        f"""# Fable / high セッション

- 実際の会話ID: `{actual_id}`
- バックグラウンドID: `{job["id"]}`
- 名前: `{manifest["name"]}`
- モデル指定: `fable`、effort: `high`
- 実メッセージで確認したモデル: `{", ".join(sorted(models)) or "確認待ち"}`
- 会話原本の存在確認: `{session.exists()}`
- バックアップ: `{data_windows}\\{actual_id}.jsonl`
- 制作ソース: `{source_windows}`
- 削除・purge・cleanup禁止。進行中のバックアップは作業中スナップショット。

WSLのこのプロジェクト内から再開:

```bash
claude attach {job["id"]}
```

背景実行で同じ会話を継続:

```bash
claude --bg --resume {actual_id}
```

背景継続ではモデル等の追加フラグを付けない。保存済みの fable / high 設定を使う。
このCLIでは背景継続にフラグを足すと別コピーになるため、元の会話を継続する時は上記を使う。

実行中に同じIDを重複起動しない。状態確認と最新会話のバックアップ:

```bash
python3 scripts/monitor_fable.py
```

ネイティブの背景実行は会話IDを管理するため、初期起動で要求したIDとは異なる。
原本を保持したまま、実IDで管理・再開する。
""",
        encoding="utf-8",
    )
    report = {
        "agent_id": job["id"],
        "conversation_id": actual_id,
        "status": job.get("status"),
        "state": job.get("state"),
        "models_seen": sorted(models),
        "effort_requested": manifest["effort"],
        "session_saved": session.exists(),
        "session_bytes": session.stat().st_size if session.exists() else None,
        "backup_saved": bool(manifest.get("session_backup")),
        "latest_tools": tools[-6:],
        "latest_actions": actions[-4:],
        "latest_visible_message": normalize_paths(visible[-1][-2000:]) if visible else "",
        "status_note": normalize_paths(status_text[-5000:]) if status_changed else "unchanged",
        "generated_files": [
            {
                "path": subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip(),
                "bytes": path.stat().st_size,
            }
            for path in sorted((DATA / "fable-v3").rglob("*"))
            if path.is_file()
            and path.suffix.lower() in {".blend", ".glb", ".png", ".jpg", ".json"}
            and "assets" not in path.relative_to(DATA / "fable-v3").parts
        ][-15:],
    }
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
