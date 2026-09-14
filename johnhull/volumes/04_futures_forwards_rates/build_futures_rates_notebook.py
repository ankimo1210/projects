"""
build_futures_rates_notebook.py
================================
nbformat-dict pattern to generate futures_rates.ipynb (Hull 11e Ch.2-6).

Usage:
    uv run python build_futures_rates_notebook.py
"""

import json
import os

# ---------------------------------------------------------------------------
# Cell helpers (same pattern as build_foundations_notebook.py)
# ---------------------------------------------------------------------------


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

# ===========================================================================
# Cell 00: title / intro
# ===========================================================================
cells.append(
    md(r"""# 先物・フォワード・金利編（Hull 11e Ch.2–6）

`johnhull/volumes` シリーズ第4冊。デリバティブの土台となる現物・先物・金利を扱います：

- **Ch.2 先物市場の仕組み** — 日次値洗い・証拠金・CCP
- **Ch.3 先物によるヘッジ** — ベーシスリスク、最小分散ヘッジ比率、ベータヘッジ
- **Ch.4 金利**（中核）— 複利変換、ゼロカーブ bootstrap、FRA、デュレーション（`hullkit.rates` を実装）
- **Ch.5 フォワード・先物価格の決定** — コストオブキャリー
- **Ch.6 金利先物** — デイカウント、CTD、デュレーションヘッジ

> 共通関数は `hullkit`（rates / nbplot）から import""")
)
cells.append(
    md(r"""> **核心** — フォワード/先物価格は『今買って持ち越す費用』（コストオブキャリー）で決まる。金利は割引の言語。<br>
> **直感** — 将来受け渡す資産は、今借りて買って保管すれば再現できる。その費用が裁定価格。<br>
> **実務** — ヘッジ（商社・運用）、カーブ構築、債券リスク管理の土台。すべての割引はここから。""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display

from hullkit import nbplot, rates

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.2 futures markets
# ===========================================================================

# Cell 03: mechanics digest
cells.append(
    md(r"""## 1. 先物市場の仕組み（Ch.2 ダイジェスト）

- 取引所で標準化（原資産・サイズ・受渡月）。ほとんどは受渡し前に**反対売買で決済**
- **日次値洗い（marking to market）**: 毎日清算価格で損益を証拠金口座に反映。
  残高が**維持証拠金**を下回ると**マージンコール**（当初証拠金水準まで補充）
- クリアリングハウス/CCP が全取引の相手方となり信用リスクを吸収
- 満期接近で先物価格はスポットに収束（乖離は裁定で消える）

| | フォワード | 先物 |
|---|---|---|
| 取引 | OTC・相対 | 取引所・標準化 |
| 決済 | 満期一括 | 日次値洗い |
| 信用リスク | 相手方 | CCP が吸収 |""")
)
cells.append(
    md(r"""> **核心** — 先物は取引所・日次値洗い・CCP 清算。フォワードは相対(OTC)。<br>
> **直感** — 日次決済で信用リスクを CCP が吸収。フォワードは相手方リスクが残る。<br>
> **実務** — 清算集中・証拠金規制(EMIR/Dodd-Frank)の背景。先物とフォワードの微小な価格差(金利相関)もここから。""")
)

# Cell 04: margin account simulation
cells.append(
    code(r"""# --- 証拠金口座の台帳（Hull GE Table 2.1 を再現、§2.4 p.52） ---
# 金先物 2枚 × 100オンスのロング、Day 1 に $1,750 で約定し Day 16 に $1,726.90 で反対売買
# 当初証拠金 $6,000/枚（計 $12,000）、維持証拠金 $4,500/枚（計 $9,000）
# マージンコールは当日の残高で判定し、翌日の取引終了までに入金される（p.53）。超過分は引き出さない
N_OZ = 200
F0_M, INIT_M, MAINT_M = 1750.00, 12_000.0, 9_000.0
futures_path = np.array([1741.00, 1738.30, 1744.60, 1741.30, 1740.10, 1736.20, 1729.90, 1730.80,
                         1725.40, 1728.10, 1711.00, 1711.00, 1714.30, 1716.10, 1723.00,
                         1726.90])  # Day 1–15 は決済価格、Day 16 は反対売買の約定価格

rows = [{"日": 1, "価格": F0_M, "日次損益": np.nan, "累積損益": np.nan,
         "証拠金残高": INIT_M, "マージンコール": np.nan}]
daily_gains, balances, margin_calls = [], [], {}
balance, pending_call, prev = INIT_M, 0.0, F0_M
for day, f in enumerate(futures_path, start=1):
    gain = (f - prev) * N_OZ
    balance += gain + pending_call  # 前日のコールは当日中に入金済み
    pending_call = 0.0
    if balance < MAINT_M:
        pending_call = INIT_M - balance  # 当初証拠金の水準まで戻す額
        margin_calls[day] = pending_call
    daily_gains.append(gain)
    balances.append(balance)
    rows.append({"日": day, "価格": f, "日次損益": round(gain, 2),
                 "累積損益": round(sum(daily_gains), 2), "証拠金残高": round(balance, 2),
                 "マージンコール": round(margin_calls[day], 2) if day in margin_calls else np.nan})
    prev = f
df_margin = pd.DataFrame(rows)
display(df_margin.apply(lambda col: col if col.name == "日"
                        else col.map(lambda v: "" if pd.isna(v) else f"{v:,.2f}")))
cum_gain = sum(daily_gains)
total_calls = sum(margin_calls.values())
print("マージンコール: " +"、".join(f"Day {d} に ${c:,.0f}" for d, c in margin_calls.items())
      + "（Hull: Day 7 に $4,020、Day 11 に $3,780）")
print(f"累積損益 = (1,726.90 − 1,750) × {N_OZ} = {(futures_path[-1] - F0_M) * N_OZ:,.2f}"
      f" ／ 日次損益の合計 = {cum_gain:,.2f}（Hull: −$4,620。一致が値洗いの本質）")
print(f"最終残高 = 当初 {INIT_M:,.0f} + 累積損益 {cum_gain:,.0f} + 入金 {total_calls:,.0f}"
      f" = {balances[-1]:,.2f}（Hull: $15,180）")""")
)

# ===========================================================================
# Section 2: Ch.3 hedging with futures
# ===========================================================================

# Cell 05: hedge basics
cells.append(
    md(r"""## 2. 先物によるヘッジとベーシスリスク（§3.1–3.3）

- **ショートヘッジ**: 将来売る資産を持つ側（実現価格 $= F_1 + b_2$）
- **ロングヘッジ**: 将来買う予定の側
- **ベーシス** $b = S - F$。満期前決済やクロスヘッジ（対象資産 ≠ 先物原資産）では
  $b_2$ が不確実 — これが**ベーシスリスク**""")
)
cells.append(
    md(r"""> **核心** — ヘッジしても残るのが『ベーシス＝現物−先物』の変動リスク。<br>
> **直感** — 満期・銘柄・受渡地が完全一致しないと現物と先物がズレる。最適ヘッジ比率で最小化する。<br>
> **実務** — 商社・航空・エネルギーの実需ヘッジで必ず出る。完全ヘッジは幻想——残差をどう管理するか。""")
)

# Cell 06: optimal hedge ratio
cells.append(
    code(r"""# --- 最小分散ヘッジ比率（ジェット燃料を灯油先物でクロスヘッジ、Hull §3.4） ---
RHO_H, SIG_S, SIG_F = 0.928, 0.0263, 0.0313
h_star = RHO_H * SIG_S / SIG_F  # eq (3.1)

rng_h = np.random.default_rng(31)
zf = rng_h.standard_normal(5000)
zs = rng_h.standard_normal(5000)
d_f = SIG_F * zf
d_s = SIG_S * (RHO_H * zf + np.sqrt(1.0 - RHO_H**2) * zs)
h_grid = np.linspace(0.0, 1.6, 81)
var_h = [float(np.var(d_s - h * d_f)) for h in h_grid]
h_hat = float(np.polyfit(d_f, d_s, 1)[0])  # ΔS を ΔF に回帰 → 傾き ≈ h*

fig1, ax1 = plt.subplots(figsize=(7.5, 4))
fig1.canvas.header_visible = False
ax1.plot(h_grid, var_h, lw=2)
ax1.axvline(h_star, color="crimson", ls="--", lw=1.5, label=f"h* = ρσ_S/σ_F = {h_star:.3f}")
ax1.set_xlabel("ヘッジ比率 h")
ax1.set_ylabel("ヘッジ後ポジションの分散")
ax1.set_title("分散は h = h* で最小（ヘッジ効果 = ρ² = "
              f"{RHO_H**2:.3f}）")
ax1.legend()
display(fig1.canvas)
print(f"回帰推定 ĥ = {h_hat:.4f}（理論値 {h_star:.4f}）")
n_star = h_star * 2_000_000 / 42_000
print(f"ジェット燃料200万ガロンを 42,000ガロン/枚 の灯油先物で → N* = {n_star:.2f} ≈ {round(n_star)} 枚")""")
)

# Cell 06b: daily settlement / tailing the hedge md
cells.append(
    md(r"""### 日次決済の影響とテイリング（§3.4 “Impact of Daily Settlement”, p.83）

上の $h^*$ は満期一括決済（フォワード）を前提にしています。先物は日次決済なので、実際は
**1日ごとのヘッジの連続**です。日次の変化率で回帰した $\hat h = \hat\rho\,\hat\sigma_S/\hat\sigma_F$ を使うと

$$N^* = \frac{\hat h\,V_A}{V_F} \quad \text{(3.3)}, \qquad V_A = S\,Q_A,\; V_F = F\,Q_F$$

Hull の例: $V_A = 2{,}000{,}000 \times 1.10$、$V_F = 42{,}000 \times 1.30 = 54{,}600$。
Hull は $\hat\rho = 0.8$ をそのまま $\hat h$ に用いて（$\hat\sigma_S = \hat\sigma_F$ に相当）
$N^* = 0.8 \times 2{,}200{,}000 / 54{,}600 = 32.23 \approx 32$ 枚。

さらに、ヘッジの残存期間に生じる証拠金の運用・調達金利を考えると、枚数を割り引くのが適切です。
金利 5%・残存 1 年なら $N^*$ を $1.05$ で割る（$32.23/1.05 = 30.70$）。これを
**テイリング（tailing the hedge）**と呼びます。""")
)

# Cell 07: beta hedging md
cells.append(
    md(r"""### 株価指数先物によるベータヘッジ（§3.5）

$$N^* = \beta\,\frac{V_A}{V_F} \quad \text{(eq 3.5)}, \qquad
\beta \to \beta^*: \; (\beta - \beta^*)\frac{V_A}{V_F}\ \text{枚ショート}$$

ヘッジで消えるのは**システマティックリスク**のみ。β を 0 にすればリスクフリー相当、
β を任意の目標値に調整することもできます。""")
)

# Cell 08: beta hedge demo
cells.append(
    code(r"""V_A, F_IDX, MULT, BETA = 5_050_000.0, 1_010.0, 250.0, 1.5
V_F = F_IDX * MULT
n_beta = BETA * V_A / V_F
print(f"ポートフォリオ ${V_A:,.0f}（β={BETA}）、先物1枚 = {F_IDX:.0f}×{MULT:.0f} = ${V_F:,.0f}")
print(f"完全ヘッジ: N* = β·V_A/V_F = {n_beta:.1f} 枚ショート\n")
rows = []
for b_target in (0.0, 0.75, 1.5, 2.0):
    k = (BETA - b_target) * V_A / V_F
    rows.append({"目標β*": b_target, "取引枚数": round(abs(k), 1),
                 "方向": "ショート" if k > 0 else ("ロング" if k < 0 else "—")})
display(pd.DataFrame(rows))""")
)

# ===========================================================================
# Section 3: Ch.4 interest rates (centerpiece)
# ===========================================================================

# Cell 09: compounding
cells.append(
    md(r"""## 3. 複利の単位（§4.4）

金利は複利頻度が決まって初めて意味を持ちます。本書（とこのシリーズ）の標準は**連続複利**：

$$R_c = m \ln\!\left(1 + \frac{R_m}{m}\right), \qquad R_m = m\left(e^{R_c/m} - 1\right) \quad \text{(4.3), (4.4)}$$""")
)
cells.append(
    md(r"""> **核心** — 同じ金利でも複利頻度で数値が変わる。連続複利 R_c が理論の標準。<br>
> **直感** — R_c=m·ln(1+R_m/m)。割引と微分が e で綺麗になるので理論は連続複利を使う。<br>
> **実務** — クオート(半年複利等)と理論(連続)の換算ミスは評価のズレに直結。単位を揃えるのが第一歩。""")
)

# Cell 10: conversion table
cells.append(
    code(r"""# 年率10%を各複利頻度から連続複利へ（hullkit.rates）
rows = []
for m, label in [(1, "年1回"), (2, "半年"), (4, "四半期"), (12, "月次"), (365, "日次")]:
    rc = rates.to_continuous(0.10, m)
    rows.append({"複利頻度": label, "m": m, "連続複利換算": f"{rc:.5%}",
                 "逆変換チェック": f"{rates.from_continuous(rc, m):.5%}"})
display(pd.DataFrame(rows))
print(f"半年複利10% → 連続複利 {rates.to_continuous(0.10, 2):.4%}（Hull: 9.758%）")""")
)

# Cell 11: bonds md
cells.append(
    md(r"""## 4. ゼロレート・債券価格・YTM・パーイールド（§4.5–4.6）

- **ゼロレート** $R(t)$: 満期 $t$ の一括払い投資に適用される金利
- **債券価格**: 各キャッシュフローを対応するゼロレートで個別に割引いた合計
- **YTM**: 全キャッシュフローを単一レート $y$ で割引いて価格に一致させる解
- **パーイールド**: 価格が額面に等しくなるクーポンレート""")
)
cells.append(
    md(r"""> **核心** — ゼロレートが割引の素。YTM・パーイールドはその要約に過ぎない。<br>
> **直感** — 債券価格＝各 CF をゼロレートで割引いた和。YTM は単一利回りに潰した近似。<br>
> **実務** — 相対価値(リッチ/チープ)判定はゼロカーブが基準。YTM の単純比較だと誤る。""")
)

# Cell 12: Table 4.2 bond
cells.append(
    code(r"""# Hull Table 4.2: ゼロレート 5.0/5.8/6.4/6.8%（連続複利）、2年 6% 半年払い債
times_b = [0.5, 1.0, 1.5, 2.0]
cfs_b = [3.0, 3.0, 3.0, 103.0]
zeros_b = [0.050, 0.058, 0.064, 0.068]
price_b = rates.bond_price(times_b, cfs_b, zeros_b)
ytm_b = rates.bond_yield(times_b, cfs_b, price_b)
print(f"債券価格 = {price_b:.3f}（Hull: 98.39）")
print(f"YTM（連続複利）= {ytm_b:.4%}（Hull: 6.76%）")

# パーイールド: c·A/m + 100·d = 100 を解く（m=2）
d_factor = np.exp(-zeros_b[-1] * times_b[-1])
a_factor = sum(np.exp(-z * t) for z, t in zip(zeros_b, times_b))
par_c = (100.0 - 100.0 * d_factor) * 2.0 / a_factor
print(f"パーイールド = {par_c:.3f}%（年率、半年複利）")""")
)

# Cell 13: bootstrap md
cells.append(
    md(r"""## 5. ブートストラップ法によるゼロカーブ構築（§4.7）

市場で観測できるのは債券**価格**。短期のゼロクーポン債から順に、
クーポン債の既知キャッシュフローを既決ゼロレートで割引き、
残った最終キャッシュフローから未知のゼロレートを逐次的に解きます（Table 4.3）。""")
)
cells.append(
    md(r"""> **核心** — 市場価格から、短い満期 → 長い満期へ順にゼロレートを解いていく。<br>
> **直感** — 既知の短期ゼロで割引いた残りを最終 CF に当て、未知のゼロを1つずつ確定する。<br>
> **実務** — あらゆる金利デリバティブ評価の出発点。カーブが間違えば全評価が狂う。""")
)

# Cell 14: bootstrap demo
cells.append(
    code(r"""# Hull Table 4.3 の5銘柄から bootstrap（hullkit.rates.bootstrap_zero_curve）
instruments = [
    (0.25, 0.0, 99.6),
    (0.50, 0.0, 99.0),
    (1.00, 0.0, 97.8),
    (1.50, 4.0, 102.5),
    (2.00, 5.0, 105.0),
]
bt_times, bt_zeros = rates.bootstrap_zero_curve(instruments)
df_bt = pd.DataFrame({"満期": bt_times, "ゼロレート": [f"{z:.4%}" for z in bt_zeros]})
display(df_bt)
print("Hull: 1.603% / 2.010% / 2.225% / 2.284% / 2.416%")

fig2, ax2 = plt.subplots(figsize=(7.5, 4))
fig2.canvas.header_visible = False
t_fine = np.linspace(0.25, 2.0, 200)
ax2.plot(t_fine, [rates.zero_interp(t, bt_times, bt_zeros) * 100 for t in t_fine],
         lw=1.5, label="線形補間")
ax2.plot(bt_times, np.array(bt_zeros) * 100, "o", ms=7, label="bootstrap 点")
ax2.set_xlabel("満期（年）")
ax2.set_ylabel("ゼロレート（%）")
ax2.set_title("Table 4.3 から構築したゼロカーブ")
ax2.legend()
display(fig2.canvas)""")
)

# Cell 15: forward/FRA md
cells.append(
    md(r"""## 6. フォワードレートと FRA（§4.8–4.9）

$$R_F = \frac{R_2 T_2 - R_1 T_1}{T_2 - T_1} \quad \text{(4.5)}$$

**FRA** は将来期間 $[T_1, T_2]$ の金利を固定する OTC 契約。固定受取側の価値：

$$V_{\text{FRA}} = L\,(R_K - R_F)\,(T_2 - T_1)\,e^{-R_2 T_2}$$

$R_K, R_F$ は期間 $T_2 - T_1$ の複利頻度で表示した金利（Example 4.3 では半年複利）、$R_2$ は連続複利のゼロレート。

順イールドではフォワードレートはゼロレートの上に位置します。""")
)
cells.append(
    md(r"""> **核心** — フォワードレート＝カーブに織り込まれた将来の金利。<br>
> **直感** — 順イールドではフォワードはゼロレートの上。連続する2つのゼロから一意に出る。<br>
> **実務** — FRA・金利先物の値付け、将来金利の市場予想の読み取りに使う。""")
)

# Cell 16: forward/FRA demo
cells.append(
    code(r"""# bootstrap カーブからフォワードレートを計算
rows = []
for (t1, z1), (t2, z2) in zip(list(zip(bt_times, bt_zeros))[:-1],
                              list(zip(bt_times, bt_zeros))[1:]):
    rows.append({"期間": f"{t1}→{t2}年", "フォワードレート": f"{rates.forward_rate(z1, t1, z2, t2):.4%}"})
display(pd.DataFrame(rows))

rf_simple = rates.forward_rate(0.03, 1.0, 0.04, 2.0)
print(f"例: 1年3% / 2年4% → 1→2年フォワード = {rf_simple:.2%}（eq 4.5）")
fra = rates.fra_value(100e6, 0.058, 0.050, 1.5, 2.0, 0.040)
print(f"FRA（Ex 4.3: 元本1億、固定5.8%受取、フォワード5.0%、1.5→2.0年、R2=4%）= {fra:,.0f}（Hull: 369,200）")
print("※ fra_value の R_K と R_F は期間 t2−t1 の単利（その期間の複利頻度、ここでは半年複利）で、"
      "Ex 4.3 の 5.8%/5.0% をそのまま渡す。連続複利なのは割引の R2=4% だけ。"
      "連続複利のフォワードを使うなら rates.from_continuous(r, m=2) で半年複利に直してから渡す")""")
)

# Cell 17: duration md
cells.append(
    md(r"""## 7. デュレーションとコンベクシティ（§4.10–4.11）

$$D = \frac{\sum_i t_i c_i e^{-y t_i}}{B}, \qquad \frac{\Delta B}{B} \approx -D\,\Delta y \quad \text{(4.8), (4.12)}$$

$$\frac{\Delta B}{B} \approx -D\,\Delta y + \tfrac{1}{2} C (\Delta y)^2 \quad \text{(4.14 のテイラー展開より)}$$

線形近似は**平行シフト・小変化**が前提。大きな変化はコンベクシティで2次補正します
（プレーン債券は $C>0$ → 「小さく損・大きく得」のバイアス）。""")
)
cells.append(
    md(r"""> **核心** — デュレーション＝金利感応度(1次)、コンベクシティ＝その曲がり(2次)。<br>
> **直感** — 価格-利回り曲線は凸。デュレーション(接線)が捉え損なう曲率がコンベクシティ。<br>
> **実務** — 債券ポートフォリオの金利リスク管理・ヘッジ枚数計算の基本量。""")
)

# Cell 18: duration demo + chart
cells.append(
    code(r"""# Hull Table 4.6: 3年・10%クーポン（半年5）・y=12%連続複利
times_d = np.arange(0.5, 3.01, 0.5)
cfs_d = [5.0] * 5 + [105.0]
y_d = 0.12
b_d = rates.bond_price(times_d, cfs_d, y_d)
dur_d = rates.macaulay_duration(times_d, cfs_d, y_d)
conv_d = rates.convexity(times_d, cfs_d, y_d)
print(f"B = {b_d:.3f}（Hull: 94.213） D = {dur_d:.3f}（Hull: 2.653） C = {conv_d:.3f}")
print(f"Δy=+10bp: 実際 {rates.bond_price(times_d, cfs_d, y_d + 0.001) - b_d:+.3f}"
      f" ／ −BDΔy = {-b_d * dur_d * 0.001:+.3f}")

dy_grid = np.linspace(-0.03, 0.03, 121)
actual = np.array([rates.bond_price(times_d, cfs_d, y_d + dy) - b_d for dy in dy_grid])
lin = -b_d * dur_d * dy_grid
quad = lin + 0.5 * conv_d * b_d * dy_grid**2

fig3, ax3 = plt.subplots(figsize=(8, 4.5))
fig3.canvas.header_visible = False
ax3.plot(dy_grid * 100, actual, lw=2, label="実際の価格変化")
ax3.plot(dy_grid * 100, lin, ls="--", lw=1.5, label="−BDΔy（線形）")
ax3.plot(dy_grid * 100, quad, ls=":", lw=2, label="＋½CB(Δy)²（2次）")
ax3.set_xlabel("Δy（%）")
ax3.set_ylabel("ΔB")
ax3.set_title("デュレーション近似とコンベクシティ補正")
ax3.legend()
display(fig3.canvas)""")
)

# ===========================================================================
# Section 4: Ch.5 forward and futures prices
# ===========================================================================

# Cell 19: cost of carry md
cells.append(
    md(r"""## 8. フォワード価格＝コストオブキャリー（§5.4–5.7, §5.11–5.12）

| 資産 | フォワード価格 | キャリー c |
|---|---|---|
| 無収入 | $F_0 = S_0 e^{rT}$ (5.1) | $r$ |
| 既知収入 $I$（PV） | $F_0 = (S_0 - I)e^{rT}$ (5.2) | — |
| 連続利回り $q$ | $F_0 = S_0 e^{(r-q)T}$ (5.3) | $r-q$ |
| 外貨（金利平価） | $F_0 = S_0 e^{(r-r_f)T}$ (5.9) | $r-r_f$ |
| 保管コスト $u$ | $F_0 = S_0 e^{(r+u)T}$ (5.12) | $r+u$ |

裁定論法: $F_0$ が高すぎれば「借りて買って先渡し売り」、低すぎれば逆。""")
)
cells.append(
    md(r"""> **核心** — F_0=S_0 e^{(r−q)T}。持ち越し費用＝金利−保有利回り。<br>
> **直感** — 高すぎれば『借りて買って先で売る』、低すぎれば逆——裁定が価格を縛る。<br>
> **実務** — 商品・株・FX の先物の理論価格。配当・保管費・コンビニエンスイールドで一般化する。

> **実務での出番 — キャッシュ・アンド・キャリー裁定**
>
> 理論フォワードからの乖離は、現物を借入で買って先物を売る(逆も)ことで無リスク利益になる。だから市場は F_0≈コストオブキャリーに張り付く。乖離が出るのは取引コスト・調達制約・配当/保管費の不確実性があるとき——その残差こそアービトラージ・デスクの収益源。""")
)

# Cell 20: forward price examples
cells.append(
    code(r"""print(f"無収入株: S=40, r=5%, T=3ヶ月 → F = 40e^(0.05×0.25) = "
      f"{40.0 * np.exp(0.05 * 0.25):.4f}（Hull: 40.50）")
# Hull §5.5（p.130–131）: 4ヶ月後のクーポン $40 を 4ヶ月金利 3% で割り引いて I = 39.60
s_i, r_5, t_5 = 900.0, 0.04, 0.75
pv_i = 40.0 * np.exp(-0.03 * 4.0 / 12.0)
f_income = (s_i - pv_i) * np.exp(r_5 * t_5)
print(f"既知収入（クーポン債）: S={s_i:.0f}, I = 40e^(−0.03×4/12) = {pv_i:.2f}, r=4%, T=9ヶ月 → "
      f"F = (900−{pv_i:.2f})e^(0.04×0.75) = {f_income:.2f}（Hull: 886.60）")
print(f"株価指数: S=1300, q=1%, r=5%, T=0.25 → F = {1300.0 * np.exp((0.05 - 0.01) * 0.25):.2f}")
print(f"外貨: S=0.80, r=6%, r_f=2%, T=2 → F = {0.80 * np.exp((0.06 - 0.02) * 2.0):.4f}（金利平価）")""")
)

# Cell 21: forward value md
cells.append(
    md(r"""### フォワード契約の価値（§5.7）

締結時のデリバリー価格 $K = F_0$ で価値ゼロ。その後 $F_0$ が動くと：

$$f = (F_0 - K)e^{-rT} \quad \text{(5.4)}$$

無収入資産なら展開形 $f = S_0 - Ke^{-rT}$ (5.5) と恒等的に一致します。""")
)

# Cell 22: forward valuation demo
cells.append(
    code(r"""# 締結: S=25, r=10%, 6ヶ月 → K = F0
s_v, r_v = 25.0, 0.10
k_v = s_v * np.exp(r_v * 0.5)
print(f"締結時: K = F0 = {k_v:.4f}, f = 0")

# 3ヶ月後: S=24, 残存 0.25年
s_now, tau_v = 24.0, 0.25
f_now = s_now * np.exp(r_v * tau_v)
val_general = (f_now - k_v) * np.exp(-r_v * tau_v)  # eq (5.4)
val_direct = s_now - k_v * np.exp(-r_v * tau_v)     # eq (5.5)
print(f"3ヶ月後: F = {f_now:.4f}, f(5.4式) = {val_general:+.4f}, "
      f"f(5.5式) = {val_direct:+.4f}, 差 = {abs(val_general - val_direct):.2e}（恒等）")""")
)

# Cell 23: consumption assets md
cells.append(
    md(r"""### 消費資産・コンビニエンスイールド・先物と期待スポット（§5.11, §5.14）

- 消費資産は売り裁定が効かず $F_0 \le (S_0+U)e^{rT}$ — 等号回復のための
  **コンビニエンスイールド** $y$: $F_0 = S_0 e^{(r+u-y)T}$
- $y > r+u$ なら先物カーブは右下がり（**バックワーデーション**）、逆なら**コンタンゴ**
- 期待将来スポットとの関係: $F_0 = E(S_T)e^{(r-k)T}$ (5.20) —
  正の系統的リスク（$k>r$）なら $F_0 < E(S_T)$（normal backwardation）""")
)

# Cell 24: interactive carry curve
cells.append(
    code(r"""# --- 先物タームストラクチャー F0(T) = S e^{(r+u−q−y)T}（インタラクティブ） ---
fig4, ax4 = plt.subplots(figsize=(8, 4.5))
fig4.canvas.header_visible = False
S_TS = 100.0
T_TS = np.linspace(0.0, 2.0, 100)
r_ts_sl = widgets.FloatSlider(value=0.05, min=0.0, max=0.10, step=0.005, description="r")
u_ts_sl = widgets.FloatSlider(value=0.00, min=0.0, max=0.05, step=0.005, description="u 保管")
qy_ts_sl = widgets.FloatSlider(value=0.00, min=0.0, max=0.15, step=0.005, description="q+y 利回り")


def _upd_carry(change=None):
    ax4.clear()
    c_net = r_ts_sl.value + u_ts_sl.value - qy_ts_sl.value
    f_curve = S_TS * np.exp(c_net * T_TS)
    ax4.plot(T_TS, f_curve, lw=2)
    ax4.axhline(S_TS, color="0.7", ls=":", lw=1, label="スポット S")
    state = "コンタンゴ（右上がり）" if c_net > 0 else ("バックワーデーション（右下がり）" if c_net < 0 else "フラット")
    ax4.set_title(f"純キャリー c−y = {c_net:+.3f} → {state}")
    ax4.set_xlabel("満期 T（年）")
    ax4.set_ylabel("先物価格 F0(T)")
    ax4.legend()
    fig4.canvas.draw_idle()


for w in (r_ts_sl, u_ts_sl, qy_ts_sl):
    w.observe(_upd_carry, "value")
_upd_carry()
display(widgets.HBox([r_ts_sl, u_ts_sl, qy_ts_sl]), fig4.canvas)""")
)

# ===========================================================================
# Section 5: Ch.6 interest rate futures
# ===========================================================================

# Cell 25: day count md
cells.append(
    md(r"""## 9. デイカウントとクリーン/ダーティ価格（§6.1）

$$\text{現金価格（ダーティ）} = \text{クォート価格（クリーン）} + \text{経過利息}$$

| 慣行 | 用途 |
|---|---|
| actual/actual | 米国債 |
| 30/360 | 米国社債・地方債 |
| actual/360 | マネーマーケット |

同じ債券・同じ日付でも、慣行によって経過利息が変わります。""")
)
cells.append(
    md(r"""> **核心** — 経過利息の数え方(デイカウント)で価格表示が変わる。<br>
> **直感** — ダーティ＝実支払額、クリーン＝経過利息を除いた表示。慣行で分子分母が変わる。<br>
> **実務** — 債券決済・損益計算で必須。慣行違い(ACT/360 vs 30/360 等)の取り違えは現金差を生む。""")
)

# Cell 26: accrued interest demo
cells.append(
    code(r"""# Hull §6.1 の例: 年8%クーポン（半年4.0）、期間 3/1→9/1、受渡日 7/3
coupon_semi = 4.0
# actual/actual（米国債方式）: 実日数 124/184
ai_actual = 124.0 / 184.0 * coupon_semi
# 30/360（社債方式）: 30日月×4 + 2日 = 122日 / 180日
ai_30_360 = 122.0 / 180.0 * coupon_semi
print(f"actual/actual: 124/184 × {coupon_semi} = {ai_actual:.4f}（Hull: 2.6957）")
print(f"30/360       : 122/180 × {coupon_semi} = {ai_30_360:.4f}（Hull: 2.7111）")
print(f"差 = {abs(ai_actual - ai_30_360):.4f} — 慣行の取り違えはそのまま価格誤差になる")""")
)

# Cell 27: T-bond futures md
cells.append(
    md(r"""## 10. T-bond 先物: コンバージョンファクターと CTD（§6.2）

ショート側は複数の**デリバラブル銘柄**から選んで受け渡せます：

$$\text{受取額} = \text{決済価格} \times \text{CF} + \text{経過利息}$$

CF は「6%利回りで評価した額面あたり価格」。ショートは

$$\text{クォート価格} - \text{決済価格} \times \text{CF}$$

を最小にする**最安受渡銘柄（CTD）**を選びます。""")
)
cells.append(
    md(r"""> **核心** — 受渡可能な複数銘柄のうち、最も安く渡せる銘柄(CTD)が先物価格を決める。<br>
> **直感** — CF で標準化しても完全中立にならず、売り手が最安受渡銘柄を選ぶオプションを持つ。<br>
> **実務** — 国債先物のヘッジ・裁定で CTD の特定は必須。CTD 切替リスクも管理対象。""")
)

# Cell 28: CTD selection
cells.append(
    code(r"""# CTD 選択（決済価格 93.25、3銘柄の例）
df_ctd = pd.DataFrame({
    "債券": ["A", "B", "C"],
    "クォート価格": [99.50, 143.50, 119.75],
    "CF": [1.0382, 1.5188, 1.2615],
})
settle_px = 93.25
df_ctd["受渡しコスト"] = (df_ctd["クォート価格"] - settle_px * df_ctd["CF"]).round(3)
display(df_ctd)
ctd = df_ctd.loc[df_ctd["受渡しコスト"].idxmin(), "債券"]
print(f"CTD = 債券{ctd}（コスト最小）。利回り>6% では低クーポン・長期債が CTD になりやすい")""")
)

# Cell 29: eurodollar + duration hedge md
cells.append(
    md(r"""## 11. 金利先物によるデュレーションヘッジ（§6.3–6.4）

- **ユーロドル/SOFR 先物**: クォート 0.01 変化 = 1枚 $25。先物レート→フォワードレートには
  **コンベクシティ調整** $\text{forward} = \text{futures} - \tfrac{1}{2}\sigma^2 t_1 t_2$ が必要（Hull Technical Note 1；11e 本文は調整の存在のみ記載）
- **デュレーションベースのヘッジ枚数**:

$$N^* = \frac{P\,D_P}{V_F\,D_F}$$

イールドカーブの**平行シフト**を仮定した近似です。""")
)
cells.append(
    md(r"""> **核心** — 必要先物枚数＝ポートフォリオの金額デュレーション ÷ 先物の金額デュレーション。<br>
> **直感** — 平行シフトを仮定し、ポートとヘッジの金利感応度を一致させる。<br>
> **実務** — 債券運用・ALM の金利リスク中立化の定番。カーブの非平行変化が残差リスク。""")
)

# Cell 30: convexity adj chart + duration hedge
cells.append(
    code(r"""fig5, ax5 = plt.subplots(figsize=(7.5, 4))
fig5.canvas.header_visible = False
sig_r = 0.012
t1_grid = np.arange(1.0, 10.01, 0.5)
adj_bp = 0.5 * sig_r**2 * t1_grid * (t1_grid + 0.25) * 1e4
ax5.plot(t1_grid, adj_bp, lw=2)
ax5.set_xlabel("先物満期 t1（年）")
ax5.set_ylabel("コンベクシティ調整（bp）")
ax5.set_title(f"σ={sig_r:.1%}: 調整は満期の2乗オーダーで拡大（先物レート > フォワードレート）")
display(fig5.canvas)

p_dur, d_p, v_fut, d_fut = 10_000_000.0, 6.8, 93_062.50, 9.2
n_dur = p_dur * d_p / (v_fut * d_fut)
print(f"ポートフォリオ $10M（D_P=6.8年）を T-bond 先物（V_F=$93,062.50, D_F=9.2年）でヘッジ:")
print(f"N* = P·D_P/(V_F·D_F) = {n_dur:.2f} ≈ {round(n_dur)} 枚ショート")""")
)

# Cell 30b: ED / SOFR futures zero-curve bootstrap md
cells.append(
    md(r"""### 先物からゼロカーブを延ばす（§6.3 “Calculating Zero Curves”, eq 6.2）

先物レートにコンベクシティ調整を施すとフォワードレート $R_F$ が得られ、式 (4.5) を $R_2$ について解くと
短いゼロレートから順に長い満期へ延ばせます（すべて連続複利）：

$$R_2 = \frac{R_F\,(T_2 - T_1) + R_1 T_1}{T_2} \quad \text{(6.2)}$$

**Example 6.4（ユーロドル先物, p.164–165）**: 300 日ゼロ 2.80%、300 日から 90 日間のフォワード 3.30%、
391 日から 3.50% とすると

$$R_{391} = \frac{0.033 \times 91 + 0.028 \times 300}{391} = 2.916\%, \qquad
R_{489} = \frac{0.035 \times 98 + 0.02916 \times 391}{489} = 3.033\%$$

原資産は 90 日金利だが、限月間の 91 日・98 日に適用したものとみなして繋ぐ。

**Example 6.5（3ヶ月 SOFR 先物, p.165）**: 3ヶ月 SOFR 先物は期間の**終わり**に決済され、
期間の一部の翌日物がすでに観測済みのことがある。観測済み 1ヶ月の複利が 2%、先物が示す 3ヶ月全体が 2.5% なら、
残り 2ヶ月のゼロレート $R$ は $0.02 \times 1/12 + R \times 2/12 = 0.025 \times 3/12$ から $R = 2.75\%$。
以降は次の限月のフォワードと式 (6.2) で 5ヶ月、8ヶ月…と延ばす。""")
)

# ===========================================================================
# Section 6: verification / exercises / summary
# ===========================================================================

# Cell 31: assertion cell
cells.append(
    code(r"""# --- 教科書例題との突合せ（hullkit/tests/test_rates.py にも同等の検証あり） ---
checks = []
checks.append(("半年複利10%→連続 9.758%", rates.to_continuous(0.10, 2), 0.097580, 1e-5))
checks.append(("Table 4.2 価格 98.39", rates.bond_price(times_b, cfs_b, zeros_b), 98.385, 5e-3))
checks.append(("Table 4.2 YTM 6.76%", rates.bond_yield(times_b, cfs_b, price_b), 0.0676, 2e-4))
for (t_chk, z_chk), want in zip(zip(bt_times, bt_zeros),
                                [0.016032, 0.020101, 0.022245, 0.022845, 0.024162]):
    checks.append((f"bootstrap {t_chk}年", z_chk, want, 5e-5))
checks.append(("フォワード 5%", rates.forward_rate(0.03, 1.0, 0.04, 2.0), 0.05, 1e-12))
checks.append(("FRA 369,247", rates.fra_value(100e6, 0.058, 0.050, 1.5, 2.0, 0.040), 369_246.5, 1.0))
checks.append(("Table 4.6 B=94.213", b_d, 94.213, 5e-3))
checks.append(("Table 4.6 D=2.653", dur_d, 2.653, 2e-3))
checks.append(("F=40.50（S=40, 3ヶ月）", 40.0 * np.exp(0.05 * 0.25), 40.5031, 1e-3))
checks.append(("§5.5 既知収入 I=39.60", pv_i, 39.60, 5e-3))
checks.append(("§5.5 既知収入 F=886.60", f_income, 886.60, 5e-3))
checks.append(("フォワード価値の恒等 (5.4)≡(5.5)", val_general, val_direct, 1e-12))
checks.append(("h* = 0.7798", h_star, 0.77976, 1e-4))
checks.append(("ベータヘッジ N*=30", n_beta, 30.0, 1e-9))
checks.append(("デュレーションヘッジ 79.42", n_dur, 79.42, 0.01))
checks.append(("Table 2.1 マージンコール Day 7 = 4,020", margin_calls.get(7, 0.0), 4_020.0, 1e-6))
checks.append(("Table 2.1 マージンコール Day 11 = 3,780", margin_calls.get(11, 0.0), 3_780.0, 1e-6))
checks.append(("Table 2.1 コールは2回だけ", float(len(margin_calls)), 2.0, 0.0))
checks.append(("Table 2.1 累積損益 −4,620", cum_gain, -4_620.0, 1e-6))
checks.append(("Table 2.1 最終残高 15,180", balances[-1], 15_180.0, 1e-6))
checks.append(("値洗い不変量（日次損益の合計 = (F_T − F_0)×200）", cum_gain,
               float((futures_path[-1] - F0_M) * N_OZ), 1e-6))
checks.append(("残高 = 当初 + 累積損益 + 入金", balances[-1], INIT_M + cum_gain + total_calls, 1e-6))

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.6g} want={want:.6g}")
    assert ok, name
print("\n全チェック合格")""")
)

# Cell 32: exercises
cells.append(
    md(r"""## 12. 練習問題

**Q1.** 年2回複利で8%の金利。連続複利では？　月次複利では？

<details><summary>解答</summary>

連続: 2ln(1.04) = 7.844%。月次: 12(e^{0.07844/12}−1) = 7.870%。
</details>

**Q2.** ゼロレートが全満期 6%（連続）のとき、2年後に1.5年債を受け渡すフォワード価格はどう求める？

<details><summary>解答</summary>

債券のスポット価格を計算し、受渡しまでのクーポン PV を引いて $F_0=(S_0−I)e^{rT}$（eq 5.2）。
</details>

**Q3.** D=5.2年・$20M のポートフォリオを D_F=8.0年・1枚 $95,000 の先物でヘッジするには？

<details><summary>解答</summary>

N* = 20,000,000×5.2/(95,000×8.0) = 136.8 ≈ 137枚ショート。
</details>""")
)

# Cell 33: summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 |
|---|---|
| 値洗い | 日次損益の合計 = (F_T−F_0)×数量。マージンコールで信用リスクを抑える |
| ヘッジ比率 | h* = ρσ_S/σ_F（回帰の傾き）。効果は ρ²。指数先物は β·V_A/V_F |
| 複利変換 | 連続複利が解析の標準。R_c = m·ln(1+R_m/m) |
| bootstrap | 短期から逐次、既知 CF を割引いて残りを解く |
| デュレーション | ΔB ≈ −BDΔy（平行シフト前提）。大変化はコンベクシティ補正 |
| キャリー | F_0 = S e^{(r+u−q−y)T}。符号がコンタンゴ/バックワーデーションを決める |
| CTD | ショートはクォート − 決済×CF を最小化する銘柄を選ぶ |

**次へ**: `volumes/05_vol_smile_estimation`（Ch.20, 23）または `volumes/07_swaps`（Ch.7, 34 — `rates.py` を活用）
**シリーズ**: `johnhull/ROADMAP.md` 参照""")
)

# ===========================================================================
# Notebook assembly
# ===========================================================================

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.12.0"},
    },
    "cells": cells,
}

# Normalize cell sources: all lines except the last should end with \n
for i, cell in enumerate(nb["cells"]):
    cell["id"] = f"cell-{i:03d}"
    src = cell["source"]
    if isinstance(src, list) and len(src) > 1:
        for i in range(len(src) - 1):
            if not src[i].endswith("\n"):
                src[i] += "\n"
        if src[-1].endswith("\n"):
            src[-1] = src[-1].rstrip("\n")

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "futures_rates.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
