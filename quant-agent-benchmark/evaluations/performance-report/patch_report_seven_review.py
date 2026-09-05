#!/usr/bin/env python3
"""Reviewed follow-up edits to the seven-model artifact (2026-09-05 re-review).

Runs after update_report_seven.py. Edits only artifact.json, refreshes the
validated artifact hash in validation.json, and records its own checks there.
"""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
MODELS = ["fable", "opus", "luna", "terra", "sol", "astra", "sonnet"]
NAMES = {m: m.title() for m in MODELS}
CATS = [("numerical", "数値精度", 30), ("model_quality", "モデル品質", 20), ("robustness", "頑健性", 15),
        ("software_engineering", "ソフトウェア", 15), ("data_quality", "データ品質", 10), ("report", "レポート", 5), ("completion", "完遂", 5)]
CHECKS = []


def check(ok, label):
    if not ok:
        raise AssertionError(label)
    CHECKS.append(label)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


artifact = json.loads((HERE / "artifact.json").read_text())
validation = json.loads((HERE / "validation.json").read_text())
check(digest(HERE / "artifact.json") == validation["artifact_sha256"], "Patch starts from the validated seven-model artifact")
summary = {r["model"]: r for r in json.loads((BASE / "evaluations/combined_summary.json").read_text())}
check(set(summary) == set(MODELS), "Seven models in combined_summary.json")
manifest, data = artifact["manifest"], artifact["snapshot"]["datasets"]
blocks = {b["id"]: b for b in manifest["blocks"]}

# 1. Score-gap table: Sonnet was missing although the narrative quotes its 20.071-point core gap.
others = ["astra", "sol", "terra", "luna", "sonnet"]
rows = []
for i, (key, label, maximum) in enumerate(CATS):
    rows.append({"category": f"{i + 1}. {label} /{maximum}", **{f"vs_{m}": f"{summary['fable'][key] - summary[m][key]:.3f}" for m in others}})
data["score-gaps"] = rows
table = next(t for t in manifest["tables"] if t["id"] == "score-gaps")
table["columns"] = [{"field": "category", "label": "カテゴリ /満点", "type": "text"}] + \
                   [{"field": f"vs_{m}", "label": f"Fable − {NAMES[m]}", "type": "text"} for m in others]
table["defaultSort"] = {"field": "category", "direction": "asc"}
table["subtitle"] = "単位は点。正の値はFableが上回り、負の値は比較相手が上回る。列=比較相手（既存4モデルと追加3モデルを1表にまとめた）。"
core = {m: sum(summary["fable"][k] - summary[m][k] for k, _, _ in CATS[:3]) for m in others}
check(abs(core["sonnet"] - 20.071) < 5e-4 and abs(core["luna"] - 4.271) < 5e-4 and abs(core["terra"] - 11.209) < 5e-4,
      "Score-gap table reproduces the narrative core gaps (Luna 4.271, Terra 11.209, Sonnet 20.071)")
check(len(table["columns"]) == 6 and len(rows) == 7, "Score-gap table: 6 columns, 7 category rows")

# 2. Cross-model pattern the seven-model text did not state.
p = blocks["precision"]
extra = ("\n\n7モデルを並べると、内部ホールドアウトで単純な基準モデルを採用した2つ（Sol：バケット集約、Sonnet：区分線形ゼロ）が短期誤差の上位2つ（20.223bp・20.906bp）で、スプラインやフォワード表現の高度モデルを採用した5つは短期1.6〜4.0bp（最大はTerra 3.956bp）に収まった。"
         "1回ずつの観測での相関であり、基準モデルの選択が原因だと断定はできないが、次回の対照実験で最初に固定すべき要因である。")
short = {m: json.loads((BASE / f"evaluations/{m}.json").read_text())["quantitative_diagnostics"]["short_end_zero_rmse_bps"] for m in MODELS}
check(sorted(short, key=short.get)[-2:] == ["sol", "sonnet"] and max(v for m, v in short.items() if m not in ("sol", "sonnet")) < 4.0 and abs(short["terra"] - 3.956) < 5e-4,
      "Short-end RMSE: Sol and Sonnet are the two worst, all others below 4.0bp (max Terra 3.956)")
if "基準モデルを採用した2つ" not in p["body"]:
    p["body"] += extra

# 3. Isolation attestation is not on record for any run; Terra also lives outside the benchmark tree.
lim = blocks["rubric-limitations-notes"]
bullet = ("\n- 優先：13 · 論点：隔離プリフライトの記録 · 対象：全モデル · 確認した事実：READMEが要求する `verify_isolation.py` の付与パス一覧は、7実行の監査ファイルのどこにも保存されていない。Terraの提出先はベンチマーク外の `Documents/terra` で、`results/<model>` を前提とした付与形式にも当てはまらない。 "
          "· 解釈への影響：静的スキャン（4名固定）と合わせ、他モデル出力への非アクセスは今回いずれのモデルについても証明されていない。点数には影響しないが、次回は付与一覧を成果物として保存する。")
audit_dir = BASE / "analysis/final-review-20260905"
found = [p for p in audit_dir.rglob("*.json") if ".venv" not in p.parts and "isolation" in p.read_text(encoding="utf-8", errors="ignore")]
check(not found, "No isolation attestation record among the audit JSON files")
if "隔離プリフライトの記録" not in lim["body"]:
    lim["body"] = lim["body"].rstrip("\n") + bullet + "\n"

serialized = json.dumps(artifact, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
check("/Users/" not in serialized, "Patched artifact still carries no private paths")
(HERE / "artifact.json").write_text(serialized, encoding="utf-8")
validation["artifact_sha256"] = digest(HERE / "artifact.json")
validation["checks"] = [c for c in validation["checks"] if not c.startswith("review-patch:")] + [f"review-patch: {c}" for c in CHECKS]
validation["checks_passed"] = len(validation["checks"])
validation["review_patch"] = "patch_report_seven_review.py: score-gap table covers all six comparisons incl. Sonnet; baseline-model short-end pattern stated; isolation-record limitation added."
(HERE / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"checks": len(validation["checks"]), "patch_checks": CHECKS}, ensure_ascii=False))
