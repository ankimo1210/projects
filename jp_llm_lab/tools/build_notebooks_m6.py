"""Generate (and execute) the final report notebook 24.

Usage: uv run --no-sync python jp_llm_lab/tools/build_notebooks_m6.py --execute
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from nbcommon import SETUP
from nbkit import build_notebook, code, md

REPO = Path(__file__).resolve().parents[1]
NB_DIR = REPO / "notebooks"


def nb24() -> list:
    return [
        md(r'''
# 24. Final Report — jp_llm_lab 総括

> **This project is not designed to build a competitive large language model.**
> **It is designed to make the internal mechanics, training dynamics, architectural
> trade-offs, probability calibration, and limitations of language models
> observable and understandable.**

本 Notebook は全マイルストーンの実測結果を横断的にまとめる。すべて保存済み成果物から読み込み、
再学習は不要。
'''),
        code(SETUP),
        code(r'''
# 3モデルの要約
runs = {
    "Model S (M1, char)": "experiments/runs/m1_model_s_smoke_seed42",
    "Model M (M2, BPE)": "experiments/runs/m2_model_m_classical_seed42",
    "Model L (M4, Modern)": "experiments/runs/m4_model_l_modern_seed42",
}
rows = []
for name, rel in runs.items():
    s = load_json(ROOT / rel / "summary.json")
    c = load_json(ROOT / rel / "config.json")
    rows.append({
        "model": name,
        "params": c["param_breakdown"]["total"],
        "tokens_seen": s["tokens_seen"],
        "val_loss": round(s["final_eval"]["loss"], 3),
        "val_ppl": round(s["final_eval"]["ppl"], 1),
        "wallclock_s": round(s["wallclock_sec"], 1),
    })
pd.DataFrame(rows)
'''),
        md(r'''
**注意**: Model S は char トークナイザ（vocab 2068, ln V=7.63）、M/L は BPE（vocab 8192, ln V=9.01）。
**loss と ppl は単位が異なり直接比較できない**。同一トークナイザ内（M vs L）のみ比較可。
'''),
        code(r'''
# 横断的な主要発見
findings = {
    "アブレーション": load_json(ROOT / "experiments/comparisons/ablation_chain.json"),
    "スケーリング": load_json(ROOT / "experiments/comparisons/scaling.json"),
    "較正": load_json(ROOT / "experiments/analysis_m5/calibration.json"),
    "暗記": load_json(ROOT / "experiments/analysis_m5/memorization.json"),
}
ab = findings["アブレーション"]["results"]
print("● アブレーション（Classical→Modern, 3 seeds）:")
for c in findings["アブレーション"]["chain"]:
    print(f"    {c:10s} val {ab[c]['val_loss_mean']:.3f} ± {ab[c]['val_loss_std']:.3f}")
print(f"    → 改善のほぼ全ては RoPE 由来（−0.34 nats, >>2σ）")

sc = findings["スケーリング"]["points"]
best = min(sc, key=lambda p: p["val_loss"])
print(f"\n● スケーリング（固定トークン予算）: 最良は {best['name']}({best['n_params']:,}), "
      f"最大 l は非最良 → データ枯渇（Chinchilla）")

cal = findings["較正"]
print(f"\n● 較正: Model L は T={cal['fitted_T']:.2f}（ほぼ1）で良較正, ECE {cal['raw']['ece_equal_width']:.3f}")
print(f"    → 次トークン較正は良好だが、生成は事実的に誤る（較正≠正しさ）")

mem = findings["暗記"]
print(f"\n● 暗記: train exact-match {mem['train']['mean_exact_match']:.1f} ≈ "
      f"val {mem['validation']['mean_exact_match']:.1f} → <1epoch の Model L は暗記が弱い")
'''),
        code(r'''
# 受入基準（spec §29）チェックリスト — すべて成果物で裏付け
criteria = [
    ("text→logits forward を追跡できる", "NB06, site/architecture"),
    ("各 tensor の shape と意味を確認できる", "NB06 (§8.4 表), test_shapes"),
    ("attention を数式と実値で確認できる", "NB05, NB14"),
    ("学習前後の attention 変化を確認できる", "NB05, NB14, site/attention"),
    ("各層の activation と gradient を観察できる", "NB16, NB17"),
    ("loss 悪化時にどの層が不安定か調査できる", "NB11 (LR range), grad_stats"),
    ("モデル間を統制実験として比較できる", "NB18 (ablation), NB19 (scaling)"),
    ("params/compute/速度/精度の trade-off を理解できる", "NB08, NB19"),
    ("reliability diagram から過信/過小を判断できる", "NB20, site/calibration"),
    ("temperature scaling の効果と限界を確認できる", "NB20"),
    ("生成の token 確率と sampling を追跡できる", "NB21"),
    ("pretraining と SFT を同じ prompt で比較できる", "NB23"),
    ("各図に解釈と注意点がある", "全 NB + site の7項目ブロック"),
    ("主要結果を NB と HTML で閲覧できる", "notebooks/ + reports/site/"),
    ("config から再実行できる", "configs/ + scripts/"),
]
pd.DataFrame(criteria, columns=["受入基準 (§29)", "対応する成果物"])
'''),
        md(r'''
## 総括

本ラボは、日本語小型 Transformer をゼロから実装し、その内部を段階的に観測可能にした。
最重要の教訓は**方法論**にある。

1. **統制実験の規律**: 効果量を必ず seed 変動と比較する（NB18）。RoPE のように本物の効果もあれば、
   RMSNorm のようにノイズ内の「変更」もある。
2. **軸の選択が結論を変える**: バッチサイズ（NB12）やスケーリング（NB19）は、step / token /
   wall-clock のどの軸で見るかで印象が反転する。
3. **もっともらしさ ≠ 能力**: Model L は流暢な日本語を生成し、次トークン較正も良好だが、
   事実は誤り、算術数列も解けない（NB19, NB20, NB22, 評価）。較正の良さは正しさを意味しない。
4. **暗記 vs 汎化**: エポック数が暗記を決める（M1 45ep は暗記、M4 <1ep は汎化）。
   低い val loss だけでは汎化を証明できない。

## 限界と次の実験
`reports/site/conclusions.html` および `LIMITATIONS.md` を参照。主なもの: 小規模・少 seed・
BPEとcharの非可比性・attention≠説明・較正≠事実性・torch.compile 不可・near-dup 未除去。

**再現**: `README.md` の Reproduction guide、または `make -C jp_llm_lab <milestone>` を参照。
'''),
    ]


NOTEBOOKS = {"24_final_report.ipynb": nb24}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    for name, fn in NOTEBOOKS.items():
        path = build_notebook(fn(), NB_DIR / name, execute=args.execute, cwd=REPO)
        print(f"built{' + executed' if args.execute else ''}: {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
