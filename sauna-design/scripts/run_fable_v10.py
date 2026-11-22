"""Resume the one preserved Fable/high session for new compact-plan sources only."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path("/home/kazumasa/projects/_data/sauna-design")
OUT = DATA / "fable-v10"
MANIFEST = DATA / "sessions/fable-high-manifest.json"
SESSION = "68de4adc-db0a-4644-a3a5-9be5012127a3"


def sha(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def unc(p):
    return "\\\\wsl.localhost\\Ubuntu" + str(p).replace("/", "\\")


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    m = json.loads(MANIFEST.read_text())
    assert m["conversation_id"] == SESSION and Path(m["session_file"]).is_file()
    if m.get("foreground_run", {}).get("state") == "running":
        try:
            os.kill(m["foreground_run"]["pid"], 0)
        except ProcessLookupError:
            pass
        else:
            raise SystemExit("Preserved session is already running; no duplicate launched")
    jobs = json.loads(
        subprocess.check_output(
            [m["cli_executable"], "agents", "--json", "--all"], text=True, timeout=20
        )
    )
    if any(
        j.get("sessionId") == SESSION
        and j.get("state") not in ("done", "stopped", "completed", "failed", None)
        for j in jobs
    ):
        raise SystemExit("Matching native job is not finished; inspect without launching")
    result_file = OUT / "verification/fable_source_result.json"
    if result_file.exists():
        raise SystemExit("This authoring run already has a result; do not duplicate it")
    OUT.mkdir(parents=True, exist_ok=True)
    for folder in ("verification", "model", "renders", "diagrams", "viewer", "logs"):
        (OUT / folder).mkdir(exist_ok=True)
    before = {}
    families = [f"fable-v{i}" for i in range(3, 10)] + [
        "architecture-v1",
        "cost-v1",
        "property-v1",
        "candidate-search-v1",
        "candidate-search-v2",
        "candidate-detail-v1",
        "candidate-search-v3",
        "one-ginza-detail-v1",
        "reference-v2",
    ]
    for family in families:
        for p in sorted((DATA / family).rglob("*")):
            if p.is_file():
                before[p.relative_to(DATA).as_posix()] = {
                    "sha256": sha(p),
                    "bytes": p.stat().st_size,
                }
    z = DATA / "chatgpt-handoff-v1/sauna-chatgpt-handoff-2026-11-15.zip"
    before[z.relative_to(DATA).as_posix()] = {"sha256": sha(z), "bytes": z.stat().st_size}
    save(OUT / "verification/preserved_before.json", before)
    prompt = f"""同じ保存済み会話を継続。ユーザーの最新依頼は「fableとチェックして画像と3Dを更新して」。
今回は元案を保持し、貼り付けの1億円案（170㎡24人2サ室/冷水1＋炭酸/16休憩）を比較候補V10として具体化します。
まず {ROOT}/AGENTS.md と {ROOT}/docs/V10_BRIEF.md をRead。既存 docs/V8_DESIGN.md、blender/sauna/geo.py,materials.py,scene.py,furniture.py、blender/build.py、plan/plan_a.json を必要な範囲でReadし、V8と同じ材質品質の独立モデルを作ってください。
既存の一様縮小は不可。浴槽70cmでも支持下端/床下が必要な点、主室の演者床、16席満席/冷槽待機、170㎡の区画重複を先に吟味してください。
あなたの仕事は新規ソース作成と設計のチェックです。親がソース全体を監査してWindows Blenderのbuild/verify/GPU render/glbとCUA表示を独立に実行します。あなたはBash/ブラウザ/Agentを実行しません。過去の権限拒否を再試行・別手段で迂回しません。Read/Write/Editだけで可能な資料を用い、拒否資料や未確認は不足として報告。
すでに隔離済み。EnterWorktree/ExitWorktree不要。新規 {ROOT}/plan/compact_v10.json、{ROOT}/blender/compact_v10.py（必要な新規compact専用ヘルパー可）、{ROOT}/docs/V10_DESIGN.md にだけWrite/Edit。他の既存ソースを変えない。旧成果・セッションを削除/変更しない。
compact_v10.py は既存sauna.geo/materials/furniture/sceneを読み、単独実行の --step estimate|build|verify|render|glb --out-root <Windows UNC> --view <view> --res --samples 等を実装。canonical fable-v10以外への保存を拒否し、既存出力の上書きは明示 --replace のみ。Blender5.2環境、sourceをsys.pathに追加、Windowsパスを使う。新規依存不可。
材質はV8のassetsをRead-only参照（親がV10へ複製しても可）、外部依存が切れないよう保存。細かい木板/目地/タイル/柔らかい面取り/間接光、濡れ床と波形水面、機器の実体、ベンチ脚/ガード/排水/壁を作る。廉価な箱だけ/既存画像貼付で済ませない。
JSONの実寸配置を正本にして、人体CHECK_・CEIL_・STUDY_別コレクション、元案を継承した暗さ/視線配慮、外周/室内/真上/断面のカメラを定義。保存後に同じモデルから描画/GLB。GLBはCyclesと材質差があると明記。GLBの検査用人体/天井は名前で切替可能。
geometryやverifyは実座標から測り、定数をそのまま再出力して『検証成功』としない。少なくとも区画面積/重複、席/シャワー/ロッカー数、浴槽水面/底/支持、出入口/主通路の幅、演者床を実物体でチェック。未測定・不成立はfailuresと別にopen_issuesへ残す。法令/機器選定/費用成立は認定しない。
完了したら新規ファイルと実行コマンド、あなた自身が行ったこと/親に残したこと、未解決の配置問題を簡潔に報告。計画だけで止めず新規ソースまで完成してください。"""
    args = [
        m["cli_executable"],
        "-p",
        "--resume",
        SESSION,
        "--model",
        "fable",
        "--effort",
        "high",
        "--safe-mode",
        "--strict-mcp-config",
        "--no-chrome",
        "--tools",
        "Read,Write,Edit,Glob,Grep",
        "--allowedTools",
        "Read,Write,Edit,Glob,Grep",
        "--permission-mode",
        "acceptEdits",
        "--permission-prompts",
        "none",
        "--add-dir",
        str(DATA),
        "--output-format",
        "stream-json",
        "--verbose",
        prompt,
    ]
    process = subprocess.Popen(
        args,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "SAUNA_DATA_ROOT": str(OUT)},
    )
    m.update(
        current_iteration="v10",
        active_output_root=str(OUT),
        foreground_run={
            "pid": process.pid,
            "state": "running",
            "started_at_utc": datetime.now(UTC).isoformat(),
        },
    )
    save(MANIFEST, m)
    print(
        json.dumps(
            {
                "state": "started",
                "pid": process.pid,
                "session_id": SESSION,
                "model_requested": "fable",
                "effort": "high",
                "output": unc(OUT),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    result, model, denials = {}, None, []
    with (OUT / "logs/fable_events.jsonl").open("w") as log:
        for line in process.stdout:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = event.get("type")
            rec = {"type": kind, "at": datetime.now(UTC).isoformat()}
            if kind == "system":
                rec.update(
                    subtype=event.get("subtype"),
                    session_id=event.get("session_id"),
                    model=event.get("model"),
                )
                model = event.get("model", model)
            elif kind == "assistant":
                message = event.get("message", {})
                model = message.get("model", model)
                rec["actions"] = [
                    {
                        "tool": b.get("name"),
                        "file": unc(Path(b.get("input", {}).get("file_path", "")))
                        if b.get("input", {}).get("file_path", "").startswith("/")
                        else b.get("input", {}).get("file_path", ""),
                    }
                    for b in message.get("content", [])
                    if b.get("type") == "tool_use"
                ]
                rec["text_tail"] = "\n".join(
                    b.get("text", "") for b in message.get("content", []) if b.get("type") == "text"
                )[-1200:]
            elif kind == "result":
                result = event
                rec.update(
                    subtype=event.get("subtype"),
                    is_error=event.get("is_error"),
                    session_id=event.get("session_id"),
                )
                denials = event.get("permission_denials", [])
            log.write(json.dumps(rec, ensure_ascii=False) + "\n")
            log.flush()
    code = process.wait()
    error = process.stderr.read()
    (OUT / "logs/fable_stderr.txt").write_text(error)
    report = {
        "exit_code": code,
        "session_id": result.get("session_id"),
        "same_conversation": result.get("session_id") == SESSION,
        "model": model,
        "effort": "high",
        "is_error": result.get("is_error", True),
        "permission_denials": denials,
        "result": result.get("result", ""),
        "new_sources": {
            str(p.relative_to(ROOT)): {"bytes": p.stat().st_size, "sha256": sha(p)}
            for p in [
                ROOT / "blender/compact_v10.py",
                ROOT / "plan/compact_v10.json",
                ROOT / "docs/V10_DESIGN.md",
            ]
            if p.exists()
        },
    }
    save(result_file, report)
    save(DATA / "sessions/v10-result.json", report)
    m = json.loads(MANIFEST.read_text())
    m["foreground_run"].update(
        state="finished", exit_code=code, finished_at_utc=datetime.now(UTC).isoformat()
    )
    backup = DATA / "sessions" / (SESSION + ".jsonl")
    shutil.copyfile(Path(m["session_file"]), backup)
    m.update(
        session_backup=str(backup),
        session_saved=True,
        session_snapshot_is_live=False,
        session_snapshot_at_utc=datetime.now(UTC).isoformat(),
    )
    save(MANIFEST, m)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
