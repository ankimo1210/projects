"""
build_summary_notebook.py
================================
nbformat-dict pattern to generate qualitative_summary.ipynb (Hull 11e Ch.1, 8, 16, 35, 36, 37).

Usage:
    uv run python build_summary_notebook.py
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
    md(r"""# 総括編: 定性トピックとケーススタディ（Hull 11e Ch.1, 8, 16, 35, 36, 37）

`johnhull/volumes` シリーズ**最終巻**。残りの定性・事例章をまとめます：

- **Ch.1 イントロダクション** — デリバティブの全体像
- **Ch.8 証券化と金融危機** — ABS / CDO / 2007–08
- **Ch.16 従業員ストックオプション（ESO）** — ベスティング・希薄化・費用計上
- **Ch.35 エネルギー・コモディティ** — 平均回帰・利便利回り・天候デリバ
- **Ch.36 リアルオプション** — 経営の柔軟性をオプションとして評価
- **Ch.37 デリバティブの失敗事例** — ローグトレーダー・モデル/流動性リスク

> この巻の完成で **Hull 11e 全37章カバー達成**。共通関数は既存の `hullkit` を再利用""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import math

import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display

from hullkit import bsm, nbplot, trees

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.1 introduction
# ===========================================================================

# Cell 03: landscape md
cells.append(
    md(r"""## 1. デリバティブの全体像（Ch.1）

**デリバティブ** = 他の資産（原資産）の価格に価値が依存する金融商品。

| 軸 | 分類 |
|---|---|
| 市場 | 取引所（標準化・CCP）／ OTC（相対・柔軟） |
| 参加者 | ヘッジャー（リスク削減）／ 投機家（リスクテイク）／ 裁定者（無リスク利益） |
| 商品 | フォワード・先物 ／ オプション ／ スワップ |

本シリーズはこの全商品を一巡しました（フォワード/先物→第4冊、オプション→第2-3冊、
スワップ→第7冊、金利→第4・11冊、信用→第9冊、エキゾチック→第10冊）。""")
)

# Cell 04: forward payoff chart
cells.append(
    code(r"""# --- ロング/ショート・フォワードのペイオフ ---
K_f = 100.0
s_t = np.linspace(60.0, 140.0, 200)
fig1, ax1 = plt.subplots(figsize=(7.5, 4))
fig1.canvas.header_visible = False
ax1.plot(s_t, s_t - K_f, lw=2, label="ロング・フォワード（S_T − K）")
ax1.plot(s_t, K_f - s_t, lw=2, label="ショート・フォワード（K − S_T）")
ax1.axhline(0.0, color="black", lw=0.8)
ax1.axvline(K_f, color="0.7", ls=":", lw=1)
ax1.set_xlabel("満期原資産価格 $S_T$")
ax1.set_ylabel("ペイオフ")
ax1.set_title("フォワードの線形ペイオフ（オプションと違い両側に無限）")
ax1.legend()
display(fig1.canvas)""")
)

# ===========================================================================
# Section 2: Ch.8 securitization
# ===========================================================================

# Cell 05: securitization md
cells.append(
    md(r"""## 2. 証券化と金融危機（Ch.8）

- **ABS（資産担保証券）**: 住宅ローン等のプールを**トランシェ**（エクイティ→メザニン→シニア）に分割
- **ABS CDO**: ABS のメザニンを再度プールして再トランシェ化（リスクの「再パッケージ」）
- **オリジネート・トゥ・ディストリビュート**: 組成者が信用リスクを保持しない → 審査の甘さ（エージェンシー問題）
- 2007–08: 住宅価格下落 → サブプライム損失 → AAA とされた上位トランシェまで毀損 → 連鎖""")
)

# Cell 06: waterfall demo
cells.append(
    code(r"""# --- トランシェの損失ウォーターフォール（プール損失をエクイティから順に吸収） ---
tranches = [("エクイティ", 0.0, 0.05), ("メザニン", 0.05, 0.15), ("シニア", 0.15, 1.0)]


def allocate_loss(pool_loss, lo, hi):
    return min(max(pool_loss - lo, 0.0), hi - lo)


fig2, ax2 = plt.subplots(figsize=(8, 4))
fig2.canvas.header_visible = False
pool_losses = np.linspace(0.0, 0.30, 100)
for name, lo, hi in tranches:
    alloc = [allocate_loss(pl, lo, hi) / (hi - lo) for pl in pool_losses]
    ax2.plot(pool_losses * 100, np.array(alloc) * 100, lw=2, label=f"{name}（{lo:.0%}–{hi:.0%}）")
ax2.set_xlabel("プール全体の損失率 (%)")
ax2.set_ylabel("トランシェ毀損率 (%)")
ax2.set_title("損失はエクイティ→メザニン→シニアの順に吸収される")
ax2.legend()
display(fig2.canvas)

pl = 0.12
print(f"プール損失 {pl:.0%} のとき:")
for name, lo, hi in tranches:
    a = allocate_loss(pl, lo, hi)
    print(f"  {name}: 損失額 {a:.1%}（トランシェ毀損率 {a / (hi - lo):.0%}）")""")
)

# Cell 07: crisis lessons md
cells.append(
    md(r"""### 危機の教訓（Ch.8）

- **相関の過小評価**: トランシェ評価のコピュラ（第9冊）はテール相関を過小に見積もり、
  「分散したはずの」リスクが同時に顕在化した
- **格付けへの過信**: AAA = 安全ではない。モデルとデータの前提が崩れると上位も毀損
- **インセンティブの歪み**: 組成・販売・格付けの各段で短期利益が優先された""")
)

# Cell 08: securitization → ABS CDO md
cells.append(
    md(r"""### ABS CDO — リスクの再パッケージ

ABS のメザニン（BBB 相当）を集めて再びトランシェ化すると、
**ABS CDO の上位**が AAA を名乗る。だが原資産は同じサブプライムの相関リスクで、
住宅市場という単一ファクターに同時に晒されている。
「分散」は見かけだけで、システミックショックには無力だった（Ch.8 / 第9冊コピュラ参照）。""")
)

# ===========================================================================
# Section 3: Ch.16 employee stock options
# ===========================================================================

# Cell 09: ESO md
cells.append(
    md(r"""## 3. 従業員ストックオプション（ESO, Ch.16）

- 報酬として付与されるコール。**ベスティング期間**（権利確定まで行使不可）・
  **早期行使**（流動性・分散動機）・**没収**（離職）が特徴
- FAS123R 以降、**費用計上**が必須に。公正価値の見積りが論点
- 評価の実務: 満期そのものでなく**期待存続期間**を使った BSM が一般的
- 新株発行による**希薄化**を価値に織り込む（$N/(N+M)$ 調整）""")
)

# Cell 10: ESO valuation demo
cells.append(
    code(r"""# --- ESO 評価: 期待存続期間 + 希薄化調整 ---
S_E, K_E, R_E, SIG_E = 100.0, 100.0, 0.05, 0.30
T_contract, T_expected = 10.0, 6.0  # 契約満期 vs 期待存続期間
# 期待存続期間で BSM 評価（早期行使を反映した実務近似）
v_contract = bsm.call_price(S_E, K_E, R_E, SIG_E, T_contract)
v_expected = bsm.call_price(S_E, K_E, R_E, SIG_E, T_expected)
print(f"契約満期10年で評価   = {v_contract:.4f}")
print(f"期待存続6年で評価     = {v_expected:.4f}（早期行使を反映してこちらが実務的）")

# 希薄化: 既存株 N、新規発行 M（オプション）
N_shares, M_options = 10_000_000, 1_000_000
dilution = N_shares / (N_shares + M_options)
v_diluted = v_expected * dilution
print(f"\n希薄化係数 N/(N+M) = {dilution:.4f}")
print(f"希薄化後の1オプション価値 = {v_diluted:.4f}")""")
)

# Cell 11: ESO interactive
cells.append(
    code(r"""# --- 期待存続期間と ESO 価値（インタラクティブ） ---
fig3, ax3 = plt.subplots(figsize=(7.5, 4))
fig3.canvas.header_visible = False
life_sl = widgets.FloatSlider(value=6.0, min=1.0, max=10.0, step=0.5, description="期待存続(年)")
vol_sl = widgets.FloatSlider(value=0.30, min=0.15, max=0.60, step=0.05, description="σ")


def _upd_eso(change=None):
    ax3.clear()
    lives = np.linspace(1.0, 10.0, 50)
    vals = [bsm.call_price(S_E, K_E, R_E, vol_sl.value, t) for t in lives]
    ax3.plot(lives, vals, lw=2)
    v_now = bsm.call_price(S_E, K_E, R_E, vol_sl.value, life_sl.value)
    ax3.plot(life_sl.value, v_now, "o", ms=9, color="crimson")
    ax3.set_xlabel("期待存続期間（年）")
    ax3.set_ylabel("ESO 価値（希薄化前）")
    ax3.set_title(f"σ={vol_sl.value:.0%}: 存続{life_sl.value:.1f}年 → {v_now:.2f}")
    fig3.canvas.draw_idle()


life_sl.observe(_upd_eso, "value")
vol_sl.observe(_upd_eso, "value")
_upd_eso()
display(widgets.HBox([life_sl, vol_sl]), fig3.canvas)""")
)

# ===========================================================================
# Section 4: Ch.35 energy & commodity
# ===========================================================================

# Cell 12: commodity md
cells.append(
    md(r"""## 4. エネルギー・コモディティ・デリバティブ（Ch.35）

- コモディティ価格は**平均回帰**を示す（金利モデルの手法が応用できる）
- **利便利回り** $y$: 現物保有の暗黙の利益。$y > r+u$ なら**バックワーデーション**
  （先物 < スポット）。コスト・オブ・キャリー: $F_0 = S_0 e^{(r+u-y)T}$
- **電力は貯蔵不可** → 通常のキャリー議論が成立しない。価格ジャンプ・季節性が強い
- **天候デリバ**（HDD/CDD）・**CAT ボンド**: 系統的リスクがほぼゼロ →
  実世界確率で期待ペイオフを計算しリスクフリー割引（歴史シミュレーション）""")
)

# Cell 13: cost of carry backwardation
cells.append(
    code(r"""# --- 利便利回りとバックワーデーション ---
S0_c, r_c, u_c = 100.0, 0.05, 0.02
fig4, ax4 = plt.subplots(figsize=(7.5, 4))
fig4.canvas.header_visible = False
ts = np.linspace(0.0, 2.0, 50)
for y_c, label in [(0.0, "y=0（コンタンゴ）"), (0.07, "y=7%=r+u（フラット）"),
                   (0.10, "y=10%>r+u（バックワーデーション）")]:
    ax4.plot(ts, S0_c * np.exp((r_c + u_c - y_c) * ts), lw=2, label=label)
ax4.axhline(S0_c, color="0.6", ls=":", lw=1, label="スポット")
ax4.set_xlabel("満期 T（年）")
ax4.set_ylabel("先物価格 F0(T)")
ax4.set_title("利便利回り y が r+u を超えるとバックワーデーション")
ax4.legend(fontsize=8)
display(fig4.canvas)
f_back = S0_c * math.exp((r_c + u_c - 0.10) * 1.0)
print(f"y=10% の1年先物 = {f_back:.4f}（< スポット100 = バックワーデーション）")""")
)

# Cell 14: Schwartz mean reversion md
cells.append(
    md(r"""### Schwartz 一要因モデル（平均回帰）

対数スポット価格が長期均衡 $\theta$ に回帰する確率過程：

$$d\ln S = \kappa(\theta - \ln S)\,dt + \sigma\,dz$$

$\kappa$ が回帰速度。金利の Vasicek モデル（既存 `ir_models` ノートブック）と同型で、
コモディティの「価格は均衡へ引き戻される」性質を捉えます。""")
)

# Cell 15: Schwartz simulation
cells.append(
    code(r"""# --- Schwartz 一要因モデルのシミュレーション ---
kappa, theta_ln, sigma_s = 2.0, math.log(100.0), 0.30
T_s, n_steps, n_paths = 5.0, 500, 50
dt_s = T_s / n_steps
rng_s = np.random.default_rng(35)
ln_s = np.full((n_paths, n_steps + 1), math.log(60.0))  # 均衡より低い水準から開始
for i in range(n_steps):
    ln_s[:, i + 1] = (ln_s[:, i] + kappa * (theta_ln - ln_s[:, i]) * dt_s
                      + sigma_s * math.sqrt(dt_s) * rng_s.standard_normal(n_paths))
paths_s = np.exp(ln_s)
t_s = np.linspace(0.0, T_s, n_steps + 1)

fig5, ax5 = plt.subplots(figsize=(8, 4))
fig5.canvas.header_visible = False
ax5.plot(t_s, paths_s[:20].T, lw=0.6, alpha=0.5)
ax5.axhline(100.0, color="crimson", ls="--", lw=1.5, label="長期均衡 e^θ=100")
ax5.plot(t_s, np.exp(ln_s.mean(axis=0)), "k-", lw=2, label="平均パス")
ax5.set_xlabel("t（年）")
ax5.set_ylabel("スポット価格")
ax5.set_title("Schwartz 平均回帰: 60 から均衡 100 へ引き戻される")
ax5.legend()
display(fig5.canvas)
late_mean = ln_s[:, -100:].mean()
print(f"後半のln S 平均 = {late_mean:.4f} → 均衡 θ = {theta_ln:.4f}（回帰を確認）")""")
)

# ===========================================================================
# Section 5: Ch.36 real options
# ===========================================================================

# Cell 16: real options md
cells.append(
    md(r"""## 5. リアルオプション（Ch.36）

伝統的 NPV は**経営の柔軟性**（放棄・拡張・繰延）を無視し過小評価しがち。
各埋め込みオプションはリスク特性が本体と違い、適切な割引率が不明だからです。
解決策: **リスク中立評価を実物資産に拡張**（期待成長率を $\lambda s$ 下げ、リスクフリー割引）。

| 埋め込みオプション | 対応 |
|---|---|
| 放棄（abandon） | アメリカン・プット（ストライク=清算価値） |
| 拡張（expand） | アメリカン・コール（ストライク=追加投資） |
| 繰延（defer） | プロジェクト価値へのアメリカン・コール |
| 縮小（contract） | アメリカン・プット |""")
)

# Cell 17: abandonment option demo
cells.append(
    code(r"""# --- 放棄オプション = プロジェクト価値へのアメリカン・プット ---
V0_proj, salvage, r_ro, sig_ro, T_ro = 100.0, 90.0, 0.05, 0.30, 2.0
abandon_value = trees.crr_price(V0_proj, salvage, r_ro, sig_ro, T_ro, 500,
                                kind="put", american=True)
print(f"プロジェクト価値 V0 = {V0_proj}")
print(f"放棄オプション（清算価値 {salvage} で売る権利）= {abandon_value:.4f}")
print(f"柔軟性込みの価値 = {V0_proj + abandon_value:.4f} > 静的 NPV {V0_proj:.1f}")
print("→ 撤退の選択肢があるだけでプロジェクトの価値は上がる")

# 清算価値を動かすと放棄オプション価値が変わる
rows = []
for sv in (70.0, 80.0, 90.0, 100.0):
    av = trees.crr_price(V0_proj, sv, r_ro, sig_ro, T_ro, 500, kind="put", american=True)
    rows.append({"清算価値": sv, "放棄オプション価値": round(av, 4)})
display(pd.DataFrame(rows))""")
)

# Cell 18: real option lambda md
cells.append(
    md(r"""### リスク中立評価の実物への拡張（§36.1）

市場で取引されない実物資産でも、リスクの市場価格 $\lambda$ を CAPM 等で推定すれば
リスク中立評価が使えます：期待成長率を $m \to m - \lambda s$ に置き換え、
キャッシュフローをリスクフリーレートで割引く。
複数オプションが共存すると**相互作用**して非加法的になるため、
ツリーの各ノードで状態（拡張済み/放棄済み）を保持して評価します（第6冊 LSM も応用可）。""")
)

# ===========================================================================
# Section 6: Ch.37 mishaps
# ===========================================================================

# Cell 19: mishaps md
cells.append(
    md(r"""## 6. デリバティブの失敗事例（Ch.37）

| 事例 | 失敗の核 |
|---|---|
| Barings（Leeson）/ SocGen（Kerviel） | フロント/バックオフィス未分離（同一人物が執行と記録） |
| Kidder Peabody（Jett） | モデルのバグが架空利益を生成 |
| LTCM | 収束裁定＋高レバレッジ → 流動性ブラックホールで破綻 |
| Orange County / P&G | 非金融主体が投機的レバレッジを保有 |

**教訓**:
- リスク限度をボードで設定し個人まで分解、利益が出ていても違反は罰する
- フロント/ミドル/バックの分離は必須
- モデルリスク・流動性リスクを軽視しない（ストレステストで補完）
- ヘッジの目的はリスク削減であって収益向上ではない""")
)

# Cell 20: mishaps lessons md
cells.append(
    md(r"""### 流動性ブラックホールと収束裁定（Ch.37 / 第8・9冊）

LTCM は「理論上収束するはずの価格差」に高レバレッジで賭けたが、
**フライト・トゥ・クオリティ**で価格差はむしろ拡大。多くの参加者が同じ戦略を
取っていたため、売りが売りを呼ぶ**流動性ブラックホール**に陥った。
2007–08 危機（第8冊）の証券化商品の投げ売りも同じ構造です。
「市場を継続的に出し抜ける」という前提を置かないことが最大の教訓。""")
)

# ===========================================================================
# Section 7: verification / capstone
# ===========================================================================

# Cell 21: assertion cell
cells.append(
    code(r"""# --- 検証 ---
checks = []
checks.append(("コモディティ先物 97.0446（バックワーデーション）",
               100.0 * math.exp((0.05 + 0.02 - 0.10) * 1.0), 97.0446, 1e-3))
checks.append(("放棄オプション 8.3427",
               trees.crr_price(100.0, 90.0, 0.05, 0.30, 2.0, 500, kind="put", american=True),
               8.3427, 1e-3))
checks.append(("ウォーターフォール: プール12%でメザニン7%",
               min(max(0.12 - 0.05, 0.0), 0.15 - 0.05), 0.07, 1e-12))
checks.append(("ウォーターフォール: シニア無傷",
               min(max(0.12 - 0.15, 0.0), 1.0 - 0.15), 0.0, 1e-12))
checks.append(("ESO 希薄化係数 ∈ (0,1)",
               float(0.0 < 10_000_000 / 11_000_000 < 1.0), 1.0, 0.0))
# 放棄オプションは柔軟性を加える
checks.append(("放棄で価値増加",
               float(trees.crr_price(100.0, 90.0, 0.05, 0.30, 2.0, 500, kind="put",
                                     american=True) > 0.0), 1.0, 0.0))
# Schwartz 平均回帰（シード固定）
kp, th, sg = 2.0, math.log(100.0), 0.30
rng_v = np.random.default_rng(35)
ls = np.full((50, 501), math.log(60.0))
for i in range(500):
    ls[:, i + 1] = ls[:, i] + kp * (th - ls[:, i]) * 0.01 + sg * 0.1 * rng_v.standard_normal(50)
checks.append(("Schwartz 後半平均 ≈ θ", ls[:, -100:].mean(), th, 0.10))

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.6g} want={want:.6g}")
    assert ok, name
print("\n全チェック合格")""")
)

# Cell 22: series capstone md
cells.append(
    md(r"""## 7. シリーズ総括 — Hull 11e 全37章カバー達成

| # | Volume | 章 |
|---|--------|----|
| — | notebooks/bsm_chapter15 | 15 |
| — | interest_rate_models | 31, 32, 33 |
| 1 | 01_foundations | 13, 14 |
| 2 | 02_options_basics | 10, 11, 12, 17, 18 |
| 3 | 03_greeks | 19 |
| 4 | 04_futures_forwards_rates | 2, 3, 4, 5, 6 |
| 5 | 05_vol_smile_estimation | 20, 23 |
| 6 | 06_numerical_methods | 21, 27 |
| 7 | 07_swaps | 7, 34 |
| 8 | 08_risk_var | 22 |
| 9 | 09_credit_xva | 9, 24, 25 |
| 10 | 10_exotics_martingales | 26, 28 |
| 11 | 11_ir_derivatives_market | 29, 30 |
| 12 | 12_qualitative_summary | 1, 8, 16, 35, 36, 37 |

**全37章カバー完了。**""")
)

# Cell 23: hullkit inventory md
cells.append(
    md(r"""### hullkit モジュール一覧

| モジュール | 内容 | 主な巻 |
|---|---|---|
| `bsm` | BSM 価格・Greeks | 1, 2, 3 |
| `trees` | CRR 二項ツリー | 1, 6, 36 |
| `mc` | GBM MC・LSM | 1, 6 |
| `payoffs` | 戦略ペイオフ | 2 |
| `hedging` | デルタヘッジ・シミュ | 3 |
| `rates` | カーブ・債券・bootstrap | 4, 7, 11 |
| `volatility` | IV・EWMA・GARCH | 5 |
| `fd` | 有限差分 | 6 |
| `swaps` | IRS・通貨スワップ | 7, 11 |
| `risk` | VaR・ES | 8, 9 |
| `credit` | ハザード・Merton・コピュラ | 9 |
| `exotics` | エキゾチック閉形式 | 10 |
| `ir_options` | Black 金利モデル | 11 |
| `nbplot` | ノートブック描画ヘルパー | 全巻 |""")
)

# Cell 24: closing md
cells.append(
    md(r"""## おわりに

John Hull『Options, Futures, and Other Derivatives』(11e) の全37章を、
12巻の新規ノートブック＋既存2巻（BSM・金利モデル）でインタラクティブに一巡しました。

- 各巻は教科書の例題値に**ピン留めした検証セル**を持ち、ヘッドレス実行で再現性を担保
- 共通ロジックは `hullkit` パッケージに集約し、pytest で教科書値と突合
- 引用は repo の 11e Global Edition PDF と節・式・表番号まで突合済み

**次の発展**: 多ファクター HJM、SABR/Heston 較正、実市場データ接続、
LMM 完全実装などは各 PROGRESS.md の future ideas を参照。

**シリーズ全体図**: `johnhull/ROADMAP.md`""")
)

# Cell 25: final closing md
cells.append(
    md(r"""---
*johnhull volumes シリーズ完結。Hull 11e 全37章カバー達成（2026-06-08）。*""")
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
for cell in nb["cells"]:
    src = cell["source"]
    if isinstance(src, list) and len(src) > 1:
        for i in range(len(src) - 1):
            if not src[i].endswith("\n"):
                src[i] += "\n"
        if src[-1].endswith("\n"):
            src[-1] = src[-1].rstrip("\n")

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qualitative_summary.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
