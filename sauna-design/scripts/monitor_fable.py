"""Inspect only this Fable job and preserve its real conversation."""

from __future__ import annotations

import hashlib
import json
import os
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
        subprocess.check_output([cli, "agents", "--json", "--all"], text=True, timeout=20)
    )
    expected_id = manifest["conversation_id"]
    job = next(
        (
            item
            for item in agents
            if item.get("id") == manifest.get("native_background_id")
            and item.get("sessionId") == expected_id
        ),
        None,
    )
    if job is None:
        job = next(
            (
                item
                for item in agents
                if item.get("name") == manifest["name"] and item.get("sessionId") == expected_id
            ),
            None,
        )
    if job is None:
        job = {
            "id": manifest.get("native_background_id", ""),
            "sessionId": manifest["conversation_id"],
            "status": "idle",
            "state": "preserved",
        }
    foreground = manifest.get("foreground_run", {})
    foreground_live = False
    if foreground.get("state") == "running":
        try:
            os.kill(foreground["pid"], 0)
            foreground_live = True
        except ProcessLookupError:
            pass
    if foreground_live:
        job = {**job, "status": "busy", "state": "working", "pid": foreground["pid"]}
    elif foreground.get("state") == "finished":
        result_file = SESSION_DIR / f"{manifest.get('current_iteration', 'v4')}-result.json"
        if result_file.exists():
            result = json.loads(result_file.read_text(encoding="utf-8"))
            complete = (
                result.get("session_id") == expected_id
                and result.get("exit_code") == 0
                and result.get("is_error") is False
            )
            job = {
                **job,
                "status": "completed" if complete else "stopped",
                "state": "complete" if complete else "preserved",
            }
    actual_id = expected_id
    manifest.update(native_background_id=job["id"])
    worktree_root = manifest.get("linked_worktree_root")
    session = (
        Path(manifest["session_file"])
        if manifest.get("session_file")
        else Path.home()
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
- 元バックグラウンドID: `{job["id"]}`（停止済み。会話は専用worktreeで継続）
- 名前: `{manifest["name"]}`
- モデル指定: `fable`、effort: `high`
- 実メッセージで確認したモデル: `{", ".join(sorted(models)) or "確認待ち"}`
- 会話原本の存在確認: `{session.exists()}`
- バックアップ: `{data_windows}\\{actual_id}.jsonl`
- 制作ソース: `{source_windows}`
- 直近の実行状態: `{job.get("status")}` / `{job.get("state")}`（{manifest.get("current_iteration", "v3")}）
- 削除・purge・cleanup禁止。進行中のバックアップは作業中スナップショット。

WSLの専用worktree内の制作ソースから再開:

```bash
cd {ROOT}
{cli} --resume {actual_id} --model fable --effort high
```

専用worktree: `{normalize_paths(worktree_root) if worktree_root else "マニフェスト参照"}`
元の背景タスクのcwdは共有側なので、今後は上記の専用worktreeから再開する。
背景実行の継続にモデル等のフラグを加えると別コピーになるCLI仕様にも注意する。
出力フォルダを参照するときもBashのcwdをworktree外へ移さず、絶対パスを指定する。

実行中に同じIDを重複起動しない。状態確認と最新会話のバックアップ:

```bash
python3 scripts/monitor_fable.py
```

EnterWorktreeに伴い会話原本は専用worktree用のClaudeプロジェクト保存先へ移動された。
会話IDは同じであり、最新の原本を外部データルートへバックアップしている。
""",
        encoding="utf-8",
    )
    active_output = Path(manifest.get("active_output_root", str(DATA / "fable-v3")))
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
        "iteration": manifest.get("current_iteration", "v3"),
        "status_note": normalize_paths(status_text[-5000:]) if status_changed else "unchanged",
        "generated_files": [
            {
                "path": subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip(),
                "bytes": path.stat().st_size,
            }
            for path in sorted(active_output.rglob("*"))
            if path.is_file()
            and path.suffix.lower() in {".blend", ".glb", ".png", ".jpg", ".json"}
            and "assets" not in path.relative_to(active_output).parts
            and "tests" not in path.relative_to(active_output).parts
        ][-24:],
    }
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
