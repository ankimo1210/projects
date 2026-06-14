"""
build_advanced_numerics_notebook.py
===================================
nbformat-dict pattern to generate advanced_numerics.ipynb
(A3 deep-dive — variance reduction, QMC, LSM, FD stability, AAD Greeks).

Plotly figures (``fig.show()``) render in the static Jupyter Book HTML.
Numerical-verification cells assert against closed forms.
References: Glasserman, *Monte Carlo Methods in Financial Engineering*;
Longstaff & Schwartz (2001); Giles & Glasserman (2006).

Usage:
    uv run python build_advanced_numerics_notebook.py
"""

import json
import os


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.split("\n")}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "source": source.split("\n"),
        "outputs": [],
        "execution_count": None,
    }


cells = []

cells.append(
    md(r"""# 高度な数値手法（A3 深掘り）

`johnhull` 深掘りシリーズ第3巻。Hull の二項木/MC/有限差分の**基礎**の先、実務の精度と速度を
支える技法を扱う：**分散減少**（アンチセティック・制御変量・重点サンプリング）、
**準モンテカルロ**（Sobol 低食い違い列）、**アメリカン型の LSM**、**有限差分の安定性**
（陽/陰/Crank-Nicolson）、そして **AAD/pathwise グリークス**。

| 節 | 内容 | 主参照 |
|---|---|---|
| 1 | MC 誤差と分散減少 | Glasserman Ch.4 |
| 2 | 準モンテカルロ（Sobol） | Glasserman Ch.5 |
| 3 | アメリカン型と LSM | Longstaff-Schwartz (2001) |
| 4 | 有限差分の安定性（θスキーム） | Wilmott; Duffy |
| 5 | グリークス：pathwise / LR / AAD | Giles-Glasserman (2006) |

> Hull 該当章: Ch.21（数値手続き）、Ch.27（モデルと数値手法の発展）。本巻はその高速・高精度化。""")
)
cells.append(
    md(r"""> **核心** — MC を速く・正確にする技術群——分散減少、QMC、LSM、AAD。<br>
> **直感** — 1/√N の壁を、賢い乱数・回帰・自動微分で突破する。<br>
> **実務** — XVA・大規模ポートフォリオの計算を現実的にする。実務の計算基盤。""")
)

cells.append(
    code(r"""# --- imports ---
import numpy as np
import plotly.graph_objects as go

from hullkit import aad, bsm, fd, mc, trees
from hullkit import fd_advanced as fda
from hullkit import mc_advanced as mca
from hullkit import plotly_viz as pv

np.set_printoptions(precision=4, suppress=True)""")
)

cells.append(
    md(r"""### 記号と単位

- $S,K$=価格、$r$=無リスク金利(連続複利・年率)、$\sigma$=ボラ(年率)、$T$=満期(年)、$q$=配当利回り(年率)。
- $N$=サンプル数(MC)/ ステップ数、$\mathrm{SE}=\sigma_{\text{payoff}}/\sqrt N$=標準誤差、$\Delta t,\Delta x$=有限差分の時間・空間刻み。
- グリークス: $\Delta=\partial V/\partial S$、ベガ $=\partial V/\partial\sigma$。""")
)

# 1. variance reduction
cells.append(
    md(r"""## 1. モンテカルロ誤差と分散減少

MC 価格の標準誤差は $\mathrm{SE}=\sigma_{\text{payoff}}/\sqrt{N}$ で**遅い**（$N$ を100倍で誤差1/10）。
分散を下げれば同じ $N$ で精度が上がる：
- **アンチセティック**: $z$ と $-z$ を対にし、負相関で分散を削る。
- **制御変量**: 既知の期待値を持つ相関量 $C$（例 $\mathbb E[e^{-rT}S_T]=S_0$）で
  $\hat V=\bar Y-\beta(\bar C-\mathbb E[C])$、最適 $\beta=\mathrm{Cov}(Y,C)/\mathrm{Var}(C)$。
- **重点サンプリング**: ドリフトをずらして稀な ITM 領域を多く引き、尤度比で補正（深い OTM に有効）。""")
)
cells.append(
    md(r"""> **核心** — 誤差は 1/√N。制御変量・対称変量で水準を下げる。<br>
> **直感** — 推定量の分散を構造的に削る。乱数をただ増やすより効率的。<br>
> **実務** — あらゆる本番 MC の標準装備。計算コストを桁で削減。""")
)

cells.append(
    code(r"""# 価格誤差 vs N（手法別・両対数）: 制御変量は水準を、QMC は傾きを改善
pv.plotly_mc_variance_reduction().show()

S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0
n = 2**14
_, p_se = mca.plain_price(S0, K, r, sigma, T, n, np.random.default_rng(0))
_, c_se = mca.control_variate_price(S0, K, r, sigma, T, n, np.random.default_rng(0))
print(f"プレーン SE={p_se:.4f}  制御変量 SE={c_se:.4f}  (削減率 {c_se / p_se:.0%})")
# deep-OTM での重点サンプリング
Kd = 150.0
_, ps = mca.plain_price(S0, Kd, r, sigma, T, n, np.random.default_rng(1))
ip, is_ = mca.importance_sampling_price(S0, Kd, r, sigma, T, n, np.random.default_rng(1))
print(f"深いOTM K=150: プレーン SE={ps:.4f}  重点 SE={is_:.4f}  価格={ip:.4f}(BSM={bsm.call_price(S0, Kd, r, sigma, T):.4f})")""")
)

# 2. QMC
cells.append(
    md(r"""## 2. 準モンテカルロ（QMC）

擬似乱数は確率1で**むら（クラスタ）と隙間**を作る。**低食い違い列**（Sobol, Halton）は
点を一様に配置し、滑らかな被積分関数では **Koksma–Hlawka 不等式**
$|\,\hat I-I\,|\le V(f)\,D_N^*$ により収束が $O((\log N)^d/N)$ ——実質 $N^{-1}$ に近い
（プレーン MC の $N^{-1/2}$ より速い）。スクランブルで誤差推定も可能。""")
)
cells.append(
    md(r"""> **核心** — Sobol 等の低食い違い列は空間を均等に埋め、収束が ~1/N に近づく。<br>
> **直感** — 擬似乱数のムラ・隙間を排し、次元を賢く充填する。<br>
> **実務** — 高次元(多資産・多時点)の値付けを高速化。実務で広く採用。""")
)

cells.append(
    code(r"""# 擬似乱数 vs Sobol（単位正方形）: Sobol は隙間なく一様に埋める
pv.plotly_qmc_vs_pseudo().show()

print("価格誤差(|·−BSM|) at N=2^14:")
print(f"  プレーン MC = {abs(mca.plain_price(S0, K, r, sigma, T, 2**14, np.random.default_rng(0))[0] - bsm.call_price(S0, K, r, sigma, T)):.4f}")
print(f"  Sobol QMC   = {abs(mca.qmc_price(S0, K, r, sigma, T, 14, seed=0) - bsm.call_price(S0, K, r, sigma, T)):.4f}")""")
)

# 3. American & LSM
cells.append(
    md(r"""## 3. アメリカン型と Longstaff–Schwartz（LSM）

アメリカン・オプションは**最適停止問題** $V_0=\sup_\tau\mathbb E^Q[e^{-r\tau}h(S_\tau)]$。
各時点で「行使 $h(S_t)$ vs 継続価値 $\mathbb E^Q[\cdot\mid\mathcal F_t]$」を比較する。LSM(2001) は
継続価値を **ITM 経路上の最小二乗回帰**（多項式基底）で近似し、後ろ向きに行使判定する。
価格は二項木・有限差分とほぼ一致する。下図は有限差分から読む**早期行使境界** $S^*(\tau)$。""")
)
cells.append(
    md(r"""> **核心** — 回帰で継続価値を推定し、MC でアメリカン/バミューダを解く(LSM)。<br>
> **直感** — 後退帰納を最小二乗回帰で代替する。<br>
> **実務** — バミューダ・スワプション、CVA の wrong-way risk。MC でしか回らない規模の早期行使。""")
)

cells.append(
    code(r"""# アメリカンプット: LSM vs 二項木 vs 有限差分（一致）
S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.30, 1.0
lsm = mc.price_american_lsm(S0, K, r, sigma, T, kind="put", n_steps=50, n_paths=100_000, rng=np.random.default_rng(0))
tree = trees.crr_price(S0, K, r, sigma, T, 1000, kind="put", american=True)
fdp = fd.fd_vanilla(S0, K, r, sigma, T, kind="put", american=True, method="cn", n_s=400, n_t=400)
print(f"アメリカンプット: LSM={lsm:.4f}  二項木(1000)={tree:.4f}  有限差分(CN)={fdp:.4f}")

# 早期行使境界 S*(τ)（σ スライダー）
pv.plotly_american_boundary().show()""")
)

# 4. FD stability
cells.append(
    md(r"""## 4. 有限差分の安定性

$\theta$-スキーム: $\theta=0$ 陽（明示）、$\theta=1$ 陰（陰的）、$\theta=\tfrac12$ Crank–Nicolson。
**Lax の等価定理**: 整合性のあるスキームは「**安定 $\Leftrightarrow$ 収束**」。
陽スキームは **von Neumann 条件** $\frac{\sigma^2\,\Delta t}{(\Delta x)^2}\lesssim\frac12$ を満たすときのみ安定
——破ると振動が増幅して**発散**する。陰/CN は無条件安定で、CN は時間2次精度。""")
)
cells.append(
    md(r"""> **核心** — 陽解法は条件付き安定、陰解法/CN は無条件安定。<br>
> **直感** — 時間刻みと空間刻みの比が陽解法の安定性を決める(CFL)。<br>
> **実務** — PDE ソルバの設計判断。CN が精度・安定の実務的バランス。""")
)

cells.append(
    code(r"""# 陽スキーム: 安定なら BSM 一致、時間刻みが粗いと発散
true = bsm.call_price(100, 100, 0.05, 0.2, 1.0)
stable = fda.fd_explicit(100, 100, 0.05, 0.2, 1.0, n_s=100, n_t=4000)
unstable = fda.fd_explicit(100, 100, 0.05, 0.2, 1.0, n_s=200, n_t=100)
print(f"BSM = {true:.4f}")
print(f"陽(安定 factor={fda.stability_factor(0.2, 100, 4000):.3f}) = {stable:.4f}")
print(f"陽(不安定 factor={fda.stability_factor(0.2, 200, 100):.2f}) = {unstable:.3e}  ← 発散")
print(f"Crank-Nicolson(無条件安定) = {fd.fd_vanilla(100, 100, 0.05, 0.2, 1.0, method='cn'):.4f}")""")
)

# 5. Greeks AAD
cells.append(
    md(r"""## 5. グリークス：pathwise / LR / AAD

- **pathwise（経路微分）**: ペイオフを直接パラメータで微分。コールのデルタは
  $e^{-rT}\,\mathbb E[(S_T/S_0)\mathbf 1_{S_T>K}]$。連続なペイオフに有効、低分散。
- **尤度比（LR/score）**: 密度を微分。不連続ペイオフでも使えるが高分散。
- **AAD（随伴自動微分）**: pathwise を**逆方向**に伝播し、$P$ 個の感応度を **1 回の逆掃引**で
  $O(1)\times$ 価格コストで得る（Giles–Glasserman 2006「smoking adjoints」）。本巻の単一原資産では
  pathwise が随伴の結果そのもの。下のとおり pathwise・LR・bump・閉形式が一致する。""")
)
cells.append(
    md(r"""> **核心** — 感応度を差分でなく微分で——pathwise・尤度比・自動微分(AAD)。<br>
> **直感** — バンプ&リバルは遅く不安定。AAD は1パスで全 Greeks を出す。<br>
> **実務** — XVA の数千の感応度計算を実用化したブレークスルー。

> **実務での出番 — AAD がリスク計算を変えた**
>
> 大規模ポートフォリオのリスクは数千の感応度(各金利・各クレジット…)を要する。素朴な差分(バンプ&リバル)は感応度の数だけ再計算が要り、XVA では非現実的だった。随伴自動微分(AAD)は、1回のパスの計算コストとほぼ同じで全感応度を同時に出す。これにより XVA デスクのリアルタイム・リスクが可能になった——理論でなく計算技術が市場実務を変えた好例。""")
)

cells.append(
    code(r"""# デルタとベガを pathwise / LR / bump / 閉形式で比較（一致）
S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0
pd, pv_ = aad.pathwise_greeks(S0, K, r, sigma, T, rng=np.random.default_rng(2))
ld, lv = aad.likelihood_ratio_greeks(S0, K, r, sigma, T, rng=np.random.default_rng(2))
bd, bv = aad.bump_greeks(S0, K, r, sigma, T)
print(f"デルタ: pathwise={pd:.4f}  LR={ld:.4f}  bump={bd:.4f}  閉形式={bsm.call_delta(S0, K, r, sigma, T):.4f}")
print(f"ベガ : pathwise={pv_:.3f}  bump={bv:.3f}  閉形式={bsm.vega(S0, K, r, sigma, T):.3f}")""")
)

# validation
cells.append(
    code(r"""# === 検証: 本巻の主張を参照値に対して固定 ===
S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0
true = bsm.call_price(S0, K, r, sigma, T)
checks = []
# QMC は同じ N でプレーンより正確
qe = abs(mca.qmc_price(S0, K, r, sigma, T, 14, seed=0) - true)
pe = abs(mca.plain_price(S0, K, r, sigma, T, 2**14, np.random.default_rng(0))[0] - true)
checks.append(("QMC 誤差 < プレーン誤差", float(qe < pe), 1.0, 0.0))
# 制御変量は SE を削減
_, pse = mca.plain_price(S0, K, r, sigma, T, 2**14, np.random.default_rng(0))
_, cse = mca.control_variate_price(S0, K, r, sigma, T, 2**14, np.random.default_rng(0))
checks.append(("制御変量 SE < プレーン SE", float(cse < pse), 1.0, 0.0))
# LSM ≈ 有限差分（アメリカンプット）
lsm = mc.price_american_lsm(100, 100, 0.05, 0.3, 1.0, kind="put", n_steps=50, n_paths=100_000, rng=np.random.default_rng(0))
fdp = fd.fd_vanilla(100, 100, 0.05, 0.3, 1.0, kind="put", american=True, method="cn", n_s=400, n_t=400)
checks.append(("LSM ≈ 有限差分", lsm, fdp, 0.1))
# Crank-Nicolson == BSM
checks.append(("CN == BSM", fd.fd_vanilla(100, 100, 0.05, 0.2, 1.0, method="cn"), true, 0.02))
# pathwise delta == 閉形式
pd, _ = aad.pathwise_greeks(100, 100, 0.05, 0.2, 1.0, rng=np.random.default_rng(2))
checks.append(("pathwise δ == 閉形式", pd, bsm.call_delta(100, 100, 0.05, 0.2, 1.0), 5e-3))
for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.4f} want={want:.4f} (tol={tol:.3g})")
    assert ok, name
print("\n全チェック合格")""")
)

# exercises
cells.append(
    md(r"""## 練習問題

**Q1.** プレーン MC の誤差を 1/10 にするには $N$ を何倍にするか。QMC では？

<details><summary>解答</summary>

プレーン MC は $\mathrm{SE}\propto N^{-1/2}$ なので **100倍**。QMC は $\sim N^{-1}$ なので約 **10倍**で済む。
</details>

**Q2.** 配当のないアメリカン**コール**で LSM が早期行使を選ばないのはなぜか。

<details><summary>解答</summary>

配当が無ければ継続価値 > 本質的価値が常に成立（Ch.11）。回帰した継続価値が常に
行使価値を上回り、満期まで保有が最適と判定される。
</details>

**Q3.** 陽スキームで $\Delta x$ を半分にしたら、安定を保つには $\Delta t$ をどう変えるか。

<details><summary>解答</summary>

von Neumann 条件 $\sigma^2\Delta t/(\Delta x)^2\lesssim\tfrac12$ より、$\Delta x$ を半分にすると
$(\Delta x)^2$ は1/4。安定維持には $\Delta t$ も **1/4** に（時間ステップ4倍）。陰/CN なら不要。
</details>""")
)

# summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 | Hull 巻への接続 |
|---|---|---|
| 分散減少 | アンチセティック/制御変量/重点。同じ N で精度↑ | vol06（数値手法） |
| 準モンテカルロ | Sobol 低食い違い。$N^{-1}$ に近い収束 | vol06 |
| LSM | 継続価値を最小二乗回帰。木/FD と一致 | vol06・vol10 |
| FD 安定性 | von Neumann。陽は条件付き、陰/CN 無条件 | vol06 |
| pathwise/LR/AAD | 一致。AAD は全感応度を1逆掃引で | vol03（グリークス） |

**次巻**: A4 XVA と信用（エクスポージャ・CVA・コピュラ）。
**シリーズ**: `johnhull/ROADMAP.md`""")
)

# ===========================================================================
nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12.0"},
    },
    "cells": cells,
}

for idx, cell in enumerate(nb["cells"]):
    cell["id"] = f"cell-{idx:03d}"
    src = cell["source"]
    if isinstance(src, list) and len(src) > 1:
        for k in range(len(src) - 1):
            if not src[k].endswith("\n"):
                src[k] += "\n"
        if src[-1].endswith("\n"):
            src[-1] = src[-1].rstrip("\n")

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "advanced_numerics.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
