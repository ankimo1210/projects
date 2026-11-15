"""Start the user-authorized Fable high job with a persistent conversation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent / "_data" / "sauna-design"
SESSION_DIR = DATA / "sessions"
MANIFEST = SESSION_DIR / "fable-high-manifest.json"


def display_path(value: str) -> str:
    return value.replace(
        "/home/kazumasa/projects", r"\\wsl.localhost\Ubuntu\home\kazumasa\projects"
    )


def main() -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    recover_bootstrap = "--recover-unstarted-bootstrap" in sys.argv
    previous = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None
    if previous and not recover_bootstrap:
        raise SystemExit(
            "A preserved Fable manifest already exists. Resume it; do not launch a duplicate."
        )
    conversation_id = previous["conversation_id"] if previous else str(uuid.uuid4())
    cli = subprocess.check_output(["bash", "-lc", "command -v claude"], text=True).strip()
    if not cli.startswith("/home/kazumasa/"):
        raise SystemExit(
            "Expected the validated native WSL Claude executable; refusing ambiguous PATH resolution."
        )
    if recover_bootstrap:
        candidate = (
            Path.home()
            / ".claude/projects/-home-kazumasa-projects-sauna-design"
            / f"{conversation_id}.jsonl"
        )
        if candidate.exists():
            raise SystemExit(
                "The conversation already exists. Resume it instead of recovering the bootstrap."
            )
        (SESSION_DIR / "failed-bootstrap-manifest.json").write_text(
            json.dumps(previous, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    name = "sauna-3d-fable-high"
    manifest = {
        "conversation_id": conversation_id,
        "name": name,
        "model_requested": "fable",
        "effort": "high",
        "persistence": True,
        "delete_session": False,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "source_root": str(ROOT),
        "data_root": str(DATA),
        "launch_state": "starting",
        "cli_executable": cli,
        "previous_bootstrap_preserved": bool(previous),
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args = [
        cli,
        "--bg",
        "--model",
        "fable",
        "--effort",
        "high",
        "--session-id",
        conversation_id,
        "--name",
        name,
        "--safe-mode",
        "--strict-mcp-config",
        "--no-chrome",
        "--permission-mode",
        "acceptEdits",
        "--permission-prompts",
        "none",
        "--tools",
        "Read,Write,Edit,Glob,Grep,Bash,WebFetch,WebSearch",
        "--allowedTools",
        "Read,Write,Edit,Glob,Grep,Bash,WebFetch,WebSearch",
        "--add-dir",
        str(DATA),
        "--",
        (ROOT / "docs" / "BRIEF.md").read_text(encoding="utf-8"),
    ]
    try:
        environment = dict(os.environ)
        environment["PATH"] = "/home/kazumasa/.local/bin:" + environment.get("PATH", "")
        result = subprocess.run(
            args, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=45, check=False
        )
        response = result.stdout + result.stderr
        manifest["launcher_exit_code"] = result.returncode
        manifest["launch_state"] = (
            "launcher-returned" if result.returncode == 0 else "launcher-error"
        )
    except subprocess.TimeoutExpired as exc:
        response = (
            "Launcher timed out; inspect the existing agent before taking any retry action.\n"
        )
        for value in (exc.stdout, exc.stderr):
            response += (
                value.decode(errors="replace") if isinstance(value, bytes) else (value or "")
            )
        manifest["launch_state"] = "launcher-timeout-check-existing"
    (SESSION_DIR / "launch-response.txt").write_text(response, encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    note = f"""# Fable / high セッション

- 会話ID（起動指定）: `{conversation_id}`
- 名前: `{name}`
- モデル指定: `fable`、effort: `high`
- 保存: 有効。削除・purge・cleanup禁止。
- 制作ソース: `{display_path(str(ROOT))}`
- マニフェストと会話の保全先: `{display_path(str(SESSION_DIR))}`

WSLのこのプロジェクト内から再開するコマンド:

```bash
claude --resume {conversation_id} --model fable --effort high
```

実行中は同じIDを重複起動しない。状態は `claude agents --json --all` と
`claude logs sauna-3d-fable-high` で確認する。
現在のセッション状態と実際の会話ファイルの保存確認は、納品前に追記する。
"""
    (ROOT / "docs" / "FABLE_SESSION.md").write_text(note, encoding="utf-8")
    print(
        json.dumps(
            {
                "conversation_id": conversation_id,
                "name": name,
                "model": "fable",
                "effort": "high",
                "persistence": True,
                "launch_state": manifest["launch_state"],
                "launcher_response": display_path(response[-5000:]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
