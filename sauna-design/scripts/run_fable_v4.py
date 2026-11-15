"""Continue the preserved Fable high conversation for a versioned design revision."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from dispatch_fable import DATA, MANIFEST, ROOT, SESSION_DIR


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--followup-file", type=Path)
    parser.add_argument("--iteration", choices=("v4", "v5", "v6", "v7", "v8"), default="v4")
    options = parser.parse_args()
    if options.iteration != "v4" and not options.followup_file:
        parser.error("A new iteration requires its concrete follow-up brief.")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    existing = manifest.get("foreground_run", {})
    if existing.get("state") == "running":
        try:
            os.kill(existing["pid"], 0)
        except ProcessLookupError:
            pass
        else:
            raise SystemExit("A preserved Fable run is still active; no duplicate was launched.")
    iteration = options.iteration
    run_root = DATA / f"fable-{iteration}"
    run_root.mkdir(parents=True, exist_ok=True)
    baselines = {
        "v4": ("v3",),
        "v5": ("v3", "v4"),
        "v6": ("v3", "v4", "v5"),
        "v7": ("v3", "v4", "v5", "v6"),
        "v8": ("v3", "v4", "v5", "v6", "v7"),
    }
    for baseline in baselines[iteration]:
        frozen = {}
        baseline_root = DATA / f"fable-{baseline}"
        for path in baseline_root.rglob("*"):
            if path.is_file():
                with path.open("rb") as stream:
                    frozen[str(path.relative_to(baseline_root))] = hashlib.file_digest(
                        stream, "sha256"
                    ).hexdigest()
        frozen_path = SESSION_DIR / f"{iteration}-preserve-{baseline}.json"
        if not frozen_path.exists():
            frozen_path.write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")
        elif json.loads(frozen_path.read_text(encoding="utf-8")) != frozen:
            raise SystemExit(f"Preserved baseline {baseline} changed; no continuation launched.")
    prompt = (
        "前回と同じ保存済みFable highの会話を継続します。ユーザーはv3の画質と改善した配置を評価しました。"
        "今回は休憩の視線・暗い照明・サ室を暗く・1室にTV・浴室の造り付け席を反映してください。"
        f"最初に {ROOT / 'AGENTS.md'} と {ROOT / 'docs/V4_BRIEF.md'} をReadし、実モデルと最終描画まで仕上げてください。"
        "作業場所はすでに隔離済みです。EnterWorktree/ExitWorktreeは呼ばず、このworktree内の通常Write/Editで編集します。"
        "共有側の原本を編集せず、ガード拒否はシェルで回避しません。"
        f"生成物は {run_root} の1ルートです。v3と参照画像・会話は変更も削除もしません。"
        "最終描画の直前にV4_BRIEFを再読し、親が追記したユーザー回答を反映してください。"
        "ブラウザ操作やheadless screenshotは親がmcp__cua_replで担当するので実行しません。"
        "TVや造り付け席の実機安全・施工成立や法適合は未検証と明示します。"
        "計画や説明だけで止めず、モデル、描画、平面の視線検討図と検証記録を完成してください。"
    )
    if options.followup_file:
        prompt = options.followup_file.read_text(encoding="utf-8")
    prompt += "\nBashのcwdをworktree外へ移さない。外部データは絶対パスで参照し、cdしない。"
    args = [
        manifest["cli_executable"],
        "-p",
        "--resume",
        manifest["conversation_id"],
        "--model",
        "fable",
        "--effort",
        "high",
        "--safe-mode",
        "--strict-mcp-config",
        "--no-chrome",
        "--tools",
        "default",
        "--disallowedTools",
        "Agent",
        "--allowedTools",
        "Read,Write,Edit,Glob,Grep,Bash,WebFetch,WebSearch,EnterWorktree,TaskOutput,TaskStop",
        "--permission-mode",
        "acceptEdits",
        "--permission-prompts",
        "none",
        "--add-dir",
        str(DATA),
        "--output-format",
        "json",
        prompt,
    ]
    environment = dict(os.environ)
    environment["SAUNA_DATA_ROOT"] = str(run_root)
    raw = SESSION_DIR / f"{iteration}-result-raw.json"
    error = SESSION_DIR / f"{iteration}-stderr.txt"
    with raw.open("w", encoding="utf-8") as stdout, error.open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(
            args, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr, text=True
        )
        manifest.update(
            active_output_root=str(run_root),
            current_iteration=iteration,
            foreground_run={
                "pid": process.pid,
                "state": "running",
                "started_at_utc": datetime.now(UTC).isoformat(),
            },
        )
        MANIFEST.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        exit_code = process.wait()
    latest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    latest["foreground_run"].update(
        state="finished", exit_code=exit_code, finished_at_utc=datetime.now(UTC).isoformat()
    )
    MANIFEST.write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        events = json.loads(raw.read_text(encoding="utf-8"))
        events = events if isinstance(events, list) else [events]
        result = next((item for item in reversed(events) if item.get("type") == "result"), {})
        initialization = next(
            (
                item
                for item in events
                if item.get("type") == "system" and item.get("subtype") == "init"
            ),
            {},
        )
        report = {
            "exit_code": exit_code,
            "session_id": result.get("session_id"),
            "same_conversation": result.get("session_id") == manifest["conversation_id"],
            "model": initialization.get("model"),
            "effort": "high",
            "is_error": result.get("is_error"),
            "result": result.get("result", ""),
        }
    except (json.JSONDecodeError, StopIteration) as exc:
        report = {"exit_code": exit_code, "parse_error": str(exc)}
    (SESSION_DIR / f"{iteration}-result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    from monitor_fable import normalize_paths

    print(normalize_paths(json.dumps(report, ensure_ascii=False)))


if __name__ == "__main__":
    main()
