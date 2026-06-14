"""
build_xva_credit_notebook.py
============================
nbformat-dict pattern to generate xva_credit.ipynb
(A4 deep-dive — counterparty credit exposure, XVA, default correlation & copulas).

Plotly figures (``fig.show()``) render in the static Jupyter Book HTML.
Numerical-verification cells assert against hand computations / closed forms.
References: Gregory, *The xVA Challenge*; Li (2000); Vasicek (2002); Hull Ch.24-25.

Usage:
    uv run python build_xva_credit_notebook.py
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
    md(r"""# XVA と信用 — エクスポージャ・CVA・コピュラ（A4 深掘り）

`johnhull` 深掘りシリーズ第4巻。Hull のハザード率・CDS の先、危機後の標準である
**カウンターパーティ信用**を扱う：将来エクスポージャ（EE/PFE）、**評価調整 XVA**
（CVA/DVA/FVA）、そして**デフォルト相関**を表すガウシアン・コピュラ
（CDO の価格モデルであり、2008年の教訓そのもの）。

| 節 | 内容 | 主参照 |
|---|---|---|
| 1 | エクスポージャ（EE / PFE） | Gregory Ch.7 |
| 2 | CVA / DVA / FVA | Gregory; Hull Ch.24 |
| 3 | デフォルト相関と1ファクター・コピュラ | Li (2000); Vasicek (2002) |
| 4 | テール依存とコピュラの限界 | — |
| 5 | Vasicek 大規模プールと信用 VaR | Hull eq.24.10; Basel ASRF |

> Hull 該当章: Ch.24–25（信用リスク・信用デリバティブ）。本巻はその先の中立 DD・XVA。""")
)

cells.append(
    code(r"""# --- imports ---
import numpy as np
import plotly.graph_objects as go

from hullkit import credit, xva, copula
from hullkit import plotly_viz as pv

np.set_printoptions(precision=4, suppress=True)""")
)

# 1. exposure
cells.append(
    md(r"""## 1. カウンターパーティ・エクスポージャ

デリバティブの相手方が破綻すると、こちらに有利な含み益（正の時価）が回収不能リスクに晒される。
時刻 $t$ のエクスポージャは $E_t=\max(V_t,0)$。リスク中立シミュレーションから：
- **期待エクスポージャ** $\mathrm{EE}(t)=\mathbb E[\max(V_t,0)]$ — CVA を駆動。
- **将来エクスポージャ** $\mathrm{PFE}_\alpha(t)$ — $\max(V_t,0)$ の高分位（信用限度枠の設定に使う）。

下図はアット・ザ・マネーのフォワードの EE/PFE。満期に向けて拡散で広がる。""")
)

cells.append(
    code(r"""# フォワードのエクスポージャ EE/PFE（σ スライダー）
pv.plotly_exposure_profile().show()

S0, r, sigma, T = 100.0, 0.05, 0.20, 1.0
K = S0 * np.exp(r * T)  # ATM forward
t, mtm = xva.forward_exposure(S0, r, sigma, K, T, n_steps=50, n_paths=60_000, rng=np.random.default_rng(0))
ee = xva.expected_exposure(mtm)
pf = xva.pfe(mtm, 0.975)
print(f"EE(0)={ee[0]:.3f}（ATM なので 0）  EE(中間)={ee[25]:.3f}  PFE97.5%(中間)={pf[25]:.3f}")""")
)

# 2. CVA
cells.append(
    md(r"""## 2. CVA / DVA / FVA

**CVA**（信用評価調整）は相手方デフォルトの期待損失の現在価値：
$$\mathrm{CVA}=(1-R)\int_0^T \mathrm{DF}(t)\,\mathrm{EE}(t)\,d\mathrm{PD}(t)
\approx (1-R)\sum_i \mathrm{DF}(t_i)\,\mathrm{EE}(t_i)\,\big[\mathrm{PD}(t_i)-\mathrm{PD}(t_{i-1})\big].$$
- **DVA**（債務評価調整）は自分のデフォルトに対する鏡像（負のエクスポージャ ENE と自社ハザード）。
- **FVA**（資金調達評価調整）は無担保エクスポージャの資金調達コスト $\approx s_f\sum \mathrm{DF}\,\mathrm{EE}\,\Delta t$。

価格は「リスクフリー価格 − CVA + DVA − FVA …」と調整される。""")
)

cells.append(
    code(r"""# CVA / DVA / FVA を計算（ハザード・回収率・資金スプレッドから）
ene = xva.expected_negative_exposure(mtm)
cva = xva.cva(t, ee, hazard=0.02, recovery=0.4, r=r)
dva = xva.dva(t, ene, own_hazard=0.015, own_recovery=0.4, r=r)
fva = xva.fva(t, ee, funding_spread=0.01, r=r)
print(f"CVA = {cva:.4f}   DVA = {dva:.4f}   FVA = {fva:.4f}")

# 手計算チェック: EE 一定=5, r=0 → CVA=(1-R)·EE·(1-e^{-λT})
ee_c = np.full(51, 5.0); t_c = np.linspace(0, 1, 51)
print(f"手計算チェック CVA = {xva.cva(t_c, ee_c, 0.02, 0.4, 0.0):.5f}  (= 0.6·5·(1-e^-0.02) = {0.6 * 5 * (1 - np.exp(-0.02)):.5f})")""")
)

# 3. default correlation & copula
cells.append(
    md(r"""## 3. デフォルト相関と1ファクター・ガウシアン・コピュラ

ポートフォリオ信用では、各社の**限界**デフォルト確率 $p$ よりも**相関**が損失分布を支配する。
1ファクター・ガウシアン・コピュラ（Li 2000）は各社の潜在資産を
$$A_i=\sqrt{\rho}\,M+\sqrt{1-\rho}\,\varepsilon_i,\qquad \text{デフォルト} \iff A_i<\Phi^{-1}(p)$$
と置く（$M$ は共通因子）。$\rho$ を変えても限界 $p$ は不変だが、**損失分布のテールが激変**する。
危機前に「安全」とされたシニア・トランシェが、相関の過小評価で焦げついた。""")
)

cells.append(
    code(r"""# ポートフォリオ損失分布 — 相関 ρ（平均=pd 不変、ρ↑ でテール肥大）
pv.plotly_portfolio_loss_correlation().show()

pd_ = 0.05
for rho in (0.0, 0.2, 0.5):
    L = copula.portfolio_loss_samples(pd_, rho, n_names=100, n_sims=50_000, rng=np.random.default_rng(1))
    print(f"ρ={rho}: 平均損失={L.mean():.4f}(pd={pd_})  std={L.std():.4f}  P(損失>15%)={np.mean(L > 0.15):.4f}")""")
)

# 4. tail dependence
cells.append(
    md(r"""## 4. テール依存とコピュラの限界

コピュラは「周辺分布」と「依存構造」を分離する（Sklar の定理）。ガウシアン・コピュラは
**テール依存がゼロ**：極端事象が同時に起きる確率を構造的に過小評価する。$\rho$ を上げると
散布図の点が対角に寄り、共通因子 $M$ が悪いときに**まとめてデフォルト**する様子が見える。
実務では $t$-コピュラ（テール依存あり）やベース相関などで補正する。""")
)

cells.append(
    code(r"""# ガウシアンコピュラ標本（ρ スライダー）: ρ↑ で同時デフォルトが集まる
pv.plotly_copula_scatter().show()

# 共通因子が悪い(M=-2)と全社の条件付きデフォルト確率が跳ね上がる
print(f"条件付きデフォルト P(default|M): M=-2 → {copula.conditional_default_prob(0.05, 0.3, -2.0):.4f}, "
      f"M=0 → {copula.conditional_default_prob(0.05, 0.3, 0.0):.4f}, M=+2 → {copula.conditional_default_prob(0.05, 0.3, 2.0):.4f}")""")
)

# 5. Vasicek & credit VaR
cells.append(
    md(r"""## 5. Vasicek 大規模プールと信用 VaR

名柄数 $\to\infty$ の均質プールでは損失が共通因子だけに依存し、**Vasicek の閉形式**になる：
$$P(L\le x)=\Phi\!\Big(\frac{\sqrt{1-\rho}\,\Phi^{-1}(x)-\Phi^{-1}(p)}{\sqrt{\rho}}\Big).$$
信用 VaR（信頼水準 $c$）は最悪の共通因子に対応する損失率
$$\mathrm{VaR}_c=\Phi\!\Big(\frac{\Phi^{-1}(p)+\sqrt{\rho}\,\Phi^{-1}(c)}{\sqrt{1-\rho}}\Big),$$
これが **Basel の ASRF（資産相関 $\rho$ の単一ファクター）**資本賦課の骨格。""")
)

cells.append(
    code(r"""# Vasicek 損失 CDF と信用 VaR
pd_, rho = 0.05, 0.2
print("Vasicek 損失 CDF:", {x: round(float(copula.vasicek_loss_cdf(x, pd_, rho)), 3) for x in (0.05, 0.10, 0.20)})
for c in (0.99, 0.999):
    print(f"信用 VaR({c:.1%}) = {credit.vasicek_credit_var(pd_, rho, c):.4f}  (損失率)")""")
)

# validation
cells.append(
    code(r"""# === 検証: 本巻の主張を参照値に対して固定 ===
checks = []
# CVA 手計算一致
ee_c = np.full(51, 5.0); t_c = np.linspace(0, 1, 51)
checks.append(("CVA 手計算一致", xva.cva(t_c, ee_c, 0.02, 0.4, 0.0), 0.6 * 5 * (1 - np.exp(-0.02)), 1e-9))
# 相関は限界デフォルトを変えない
L0 = copula.portfolio_loss_samples(0.05, 0.0, 100, 50_000, np.random.default_rng(1))
L5 = copula.portfolio_loss_samples(0.05, 0.5, 100, 50_000, np.random.default_rng(1))
checks.append(("平均損失 = pd (ρ=0.5)", float(L5.mean()), 0.05, 5e-3))
checks.append(("相関でテール肥大 (var↑)", float(L5.var() > 3 * L0.var()), 1.0, 0.0))
# 独立プール分散 = pd(1-pd)/n
checks.append(("独立プール var = pd(1-pd)/n", float(L0.var()), 0.05 * 0.95 / 100, 1e-4))
# Vasicek CVaR > 期待損失 pd
checks.append(("信用VaR(99.9%) > pd", float(credit.vasicek_credit_var(0.05, 0.2, 0.999) > 0.05), 1.0, 0.0))
for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.4f} want={want:.4f} (tol={tol:.3g})")
    assert ok, name
print("\n全チェック合格")""")
)

# exercises
cells.append(
    md(r"""## 練習問題

**Q1.** CVA が大きくなるのは EE が大きいときか、相手方の信用が悪いときか。

<details><summary>解答</summary>

両方。$\mathrm{CVA}=(1-R)\int \mathrm{DF}\,\mathrm{EE}\,d\mathrm{PD}$ は EE（エクスポージャ）と
$d\mathrm{PD}$（ハザード）の積。さらに両者が正相関だと**ワンウェイ（wrong-way）リスク**で一段と増える。
</details>

**Q2.** ガウシアン・コピュラで $\rho$ を上げると、シニア・トランシェの価値はどう動くか。

<details><summary>解答</summary>

シニア（高損失側）の被弾確率が上がるため価値は**下がる**（スプレッド拡大）。
逆にエクイティ（最初の損失）は相関上昇で守られ得る。相関がトランシェ間で価値を移す。
</details>

**Q3.** なぜガウシアン・コピュラは危機で過小評価を招いたか。

<details><summary>解答</summary>

テール依存がゼロで、**同時極端デフォルト**を構造的に低く見る。加えて相関 $\rho$ を
過去データから低めに推定したため、シニア・トランシェのテールリスクを取り逃がした。
</details>""")
)

# summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 | Hull 巻への接続 |
|---|---|---|
| エクスポージャ | EE が CVA を、PFE が限度枠を駆動 | vol09（信用・XVA） |
| CVA/DVA/FVA | リスクフリー価格からの評価調整 | vol09 |
| 1ファクター・コピュラ | 限界 pd 不変・相関 ρ が損失テールを支配 | vol09 |
| テール依存 | ガウシアンは 0 → 同時極端を過小評価 | — |
| Vasicek / 信用VaR | 大規模プール閉形式、Basel ASRF の骨格 | vol08（リスクVaR）・vol09 |

**次巻**: capstone（Heston×Fourier で価格 → MC で Greeks → その CVA、を一気通貫）。
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xva_credit.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
