"""
build_capstone_notebook.py
==========================
nbformat-dict pattern to generate capstone.ipynb — one position, every tool.

Prices a call under Heston via Fourier (A2), checks it against the risk-neutral
expectation (A1) and Monte-Carlo / QMC (A3), computes its delta (A3), measures the
counterparty CVA of the hedge (A4), and shows the whole stack collapses to the
Hull-level BSM result in the zero-vol-of-vol limit.

Usage:
    uv run python build_capstone_notebook.py
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
    md(r"""# Capstone — 1つのポジション、すべての道具

`johnhull` 深掘りシリーズ総まとめ。**確率ボラの株に対する 1 年コール**という単一ポジションを、
A1–A4 の道具で一気通貫に扱う：

1. **価格** — Heston × Fourier(COS)（A2）。
2. **正当化** — 価格 = リスク中立割引期待値（A1: Girsanov/Feynman-Kac）を MC で確認。
3. **数値効率** — COS は少数項、MC は多数パス、QMC で加速（A3）。
4. **感応度** — デルタ（A3: bump/AAD）。確率ボラなのでベガ・リスクが残る。
5. **信用** — ヘッジのフォワードのカウンターパーティ CVA（A4）。
6. **健全性** — vol-of-vol→0 で全部 Hull レベルの BSM に collapse。

> 各ステップが既存の `hullkit` 関数（`heston/fourier/mc_advanced/aad/xva`）の実呼び出しで、
> 図・テスト・本文が同じ数式を共有する。""")
)

cells.append(
    code(r"""# --- imports ---
import numpy as np

from hullkit import aad, bsm, fourier, heston, mc, xva
from hullkit import mc_advanced as mca

# Heston パラメータ（株式の典型: 下方スキュー）
S0, K, r, T = 100.0, 100.0, 0.05, 1.0  # S0,K=価格, r=年率5%(連続複利), T=1年
v0, kappa, theta, xi, rho = 0.04, 1.5, 0.04, 0.6, -0.7  # 初期分散/平均回帰(/年)/長期分散/vol-of-vol/相関
def cf(u):
    return heston.heston_cf(u, r, T, v0, kappa, theta, xi, rho)
print(f"ポジション: 1年 ATM コール, S0={S0}, K={K}, r={r:.0%}")
print(f"Heston: v0={v0}, κ={kappa}, θ={theta}, ξ={xi}, ρ={rho}")""")
)

cells.append(
    md(r"""### 記号と単位

- $S,K$=価格、$r$=無リスク金利(連続複利・年率)、$T$=満期(年)、$y=\ln(S_T/S_0)$=対数収益率。
- Heston: $v_0$=初期分散・$\kappa$=平均回帰速度(/年)・$\theta$=長期分散・$\xi$=vol-of-vol・$\rho$=相関(分散は年率)。
- $\lambda$=ハザード率(/年)、$R$=回収率、EE=期待エクスポージャ。価格・CVA は想定元本と同じ通貨単位。""")
)

# 1. price (A2) + 2. risk-neutral check (A1) + 3. numerics (A3)
cells.append(
    md(r"""## 1–3. 価格・リスク中立性・数値効率（A2 → A1 → A3）

確率ボラ下では閉形式が無いので **Fourier(COS)** で価格を得る。これは
$e^{-rT}\mathbb E^Q[(S_T-K)^+]$ — **A1 の Feynman-Kac/Girsanov** が保証する割引期待値 — に等しく、
独立な **Monte-Carlo（A3）** とも一致する。COS は項数で**指数収束**、MC は $1/\sqrt N$、QMC で加速。""")
)

cells.append(
    code(r"""# 価格を3通りで: Fourier(COS) == 割引期待値(MC) == QMC
price_cos = fourier.cos_price(cf, S0, K, r, T)
price_mc, se = heston.heston_mc_price(S0, K, r, T, v0, kappa, theta, xi, rho,
                                      n_steps=200, n_paths=300_000, rng=np.random.default_rng(0))
print(f"Heston コール価格:")
print(f"  Fourier (COS)        = {price_cos:.4f}")
print(f"  リスク中立 MC E^Q[·]  = {price_mc:.4f} ± {se:.4f}  ({abs(price_cos - price_mc) / se:.1f} SE)")
# 数値効率: COS は N=160 項で収束済み、MC は同じ精度に約 (誤差比)^2 倍のパスが要る
for n_terms in (16, 40, 160):
    print(f"  COS(N={n_terms:3d}) = {fourier.cos_price(cf, S0, K, r, T, N=n_terms):.4f}")""")
)

# 4. greeks (A3)
cells.append(
    md(r"""## 4. デルタと残るリスク（A3）

デルタは COS 価格を $S_0$ で**中心差分**して得る（単一原資産なので AAD/pathwise と同値）。
BSM の閉形式デルタ（ATM 含意ボラ使用）と近いが、**確率ボラの下ではベガ・相関リスクが残り**、
デルタ・ヘッジだけでは消えない（だから vol-of-vol・スキューを別途ヘッジする）。""")
)

cells.append(
    code(r"""# Heston デルタ = COS 価格の中心差分
h = 0.5
delta_heston = (fourier.cos_price(cf, S0 + h, K, r, T) - fourier.cos_price(cf, S0 - h, K, r, T)) / (2 * h)
# 参考: BSM デルタ（ATM 含意ボラ ≈ √v0）
from hullkit import volatility
iv_atm = volatility.implied_vol(price_cos, S0, K, r, T)
delta_bsm = bsm.call_delta(S0, K, r, iv_atm, T)
# 単一原資産 GBM での pathwise デルタ（AAD と同値）も同水準
pd_, _ = aad.pathwise_greeks(S0, K, r, iv_atm, T, rng=np.random.default_rng(1))
print(f"Heston デルタ(COS 差分) = {delta_heston:.4f}")
print(f"BSM デルタ(含意ボラ {iv_atm:.3f}) = {delta_bsm:.4f}   pathwise(同ボラ) = {pd_:.4f}")
print("→ デルタは近いが、Heston ではベガ/スキュー・リスクが残る（デルタヘッジのみでは不十分）")""")
)

# 5. CVA (A4)
cells.append(
    md(r"""## 5. ヘッジのカウンターパーティ CVA（A4）

このコールをヘッジするためにフォワードを建てると、相手方への**与信エクスポージャ**が生じる。
将来エクスポージャ EE から **CVA**（相手方デフォルトの期待損失現価）を計算する。
価格は「リスクフリー価格 − CVA」と調整される——危機後の中立 DD の基本。""")
)

cells.append(
    code(r"""# ヘッジ・フォワードのエクスポージャと CVA
fwd_k = S0 * np.exp(r * T)
t, mtm = xva.forward_exposure(S0, r, np.sqrt(v0), fwd_k, T, n_steps=50, n_paths=60_000, rng=np.random.default_rng(2))
ee = xva.expected_exposure(mtm)
cva = xva.cva(t, ee, hazard=0.02, recovery=0.4, r=r)
print(f"ヘッジ・フォワード: EE(中間)={ee[25]:.3f}  PFE97.5%(中間)={xva.pfe(mtm, 0.975)[25]:.3f}")
print(f"CVA(λ=2%, R=40%) = {cva:.4f}")
print(f"信用調整後の実効コスト ≈ リスクフリー価格 {price_cos:.4f} に対し CVA {cva:.4f} を上乗せ")""")
)

# 6. BSM limit (sanity)
cells.append(
    md(r"""## 6. 健全性: vol-of-vol → 0 で Hull レベルへ collapse

$\xi\to0$ かつ $v_0=\theta=\sigma^2$ にすると分散は一定 $\sigma^2$ になり、Heston は GBM、
COS 価格は **BSM 閉形式** に一致する。深掘りの全機構が、退化極限で Hull の基礎に戻ることを確認。""")
)

cells.append(
    code(r"""# vol-of-vol → 0: Heston(COS) == BSM
sigma = 0.20
def cf_bsm_limit(u):
    return heston.heston_cf(u, r, T, sigma**2, kappa, sigma**2, 1e-3, rho)
cos_limit = fourier.cos_price(cf_bsm_limit, S0, K, r, T)
print(f"Heston(ξ→0) COS = {cos_limit:.4f}   BSM 閉形式 = {bsm.call_price(S0, K, r, sigma, T):.4f}")""")
)

# validation
cells.append(
    code(r"""# === 検証: capstone の主張を固定 ===
checks = []
checks.append(("Fourier == リスク中立 MC", price_cos, price_mc, 4 * se + 0.03))
checks.append(("Heston(ξ→0) == BSM", cos_limit, bsm.call_price(S0, K, r, 0.20, T), 2e-3))
checks.append(("デルタが [0,1]", float(0.0 < delta_heston < 1.0), 1.0, 0.0))
checks.append(("CVA > 0", float(cva > 0.0), 1.0, 0.0))
# QMC は同じ N でプレーンより正確（A3 を ATM コールで再掲）
qe = abs(mca.qmc_price(S0, K, r, 0.20, T, 14, seed=0) - bsm.call_price(S0, K, r, 0.20, T))
pe = abs(mca.plain_price(S0, K, r, 0.20, T, 2**14, np.random.default_rng(0))[0] - bsm.call_price(S0, K, r, 0.20, T))
checks.append(("QMC 誤差 < プレーン誤差", float(qe < pe), 1.0, 0.0))
for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.4f} want={want:.4f} (tol={tol:.3g})")
    assert ok, name
print("\n全チェック合格 — 価格・Greeks・CVA・極限が整合")""")
)

# summary
cells.append(
    md(r"""## まとめ — どの道具がどこで効いたか

| ステップ | 使った深掘り | 既存 Hull 巻 |
|---|---|---|
| 価格 = 割引期待値 | A1 Girsanov/Feynman-Kac | vol01・bsm |
| Fourier(COS) 価格 | A2 Heston/特性関数/COS | vol05 |
| MC/QMC/収束 | A3 分散減少・QMC | vol06 |
| デルタ(AAD/bump) | A3 pathwise/AAD | vol03 |
| エクスポージャ・CVA | A4 XVA/コピュラ | vol09 |
| 退化極限 = BSM | 全 A + 基礎 | bsm・vol01 |

**1 本のリスク中立評価の背骨**に、確率解析（A1）・確率ボラと Fourier（A2）・高度な数値（A3）・
信用と XVA（A4）が枝として接続する——これが johnhull 深掘りの全体像。

**シリーズ索引**: `johnhull/ROADMAP.md`／**可視化ポータル**: `make hull-report`。""")
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capstone.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
