"""
build_exotics_notebook.py
================================
nbformat-dict pattern to generate exotics.ipynb (Hull 11e Ch.26, 28).

Usage:
    uv run python build_exotics_notebook.py
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
    md(r"""# エキゾチック・オプションと測度（Hull 11e Ch.26, 28）

`johnhull/volumes` シリーズ第10冊。複雑なペイオフと、その背後の数学：

- **エキゾチック（Ch.26）** — バイナリ、バリア、ルックバック、アジアン、交換（Margrabe）、バリアンス・スワップ
- **マルチンゲールと測度（Ch.28）** — ニュメレール、市場リスクの価格 λ、フォワード測度

> 共通関数は `hullkit`（exotics / bsm / mc / nbplot）から import。
> 第6冊（数値解法）・第5冊（スマイル）の道具がここで効きます""")
)
cells.append(
    md(r"""> **核心** — エキゾチックは標準部品の組み合わせ＋経路依存。測度変換が値付けの万能道具。<br>
> **直感** — 適切なニュメレールを選ぶと、複雑な期待値が単純な形に化ける。<br>
> **実務** — 仕組債・為替・金利の仕立て商品の値付け。測度選択が計算を決める。""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import math

import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
from scipy.stats import norm

from hullkit import bsm, exotics, mc, nbplot
from hullkit._binary_lesson import _figures

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.26 exotics
# ===========================================================================

# Cell 03: taxonomy md
cells.append(
    md(r"""## 1. エキゾチックの分類（Ch.26）

OTC で取引される非標準ペイオフ。GE 版 Ch.26 の商品節（§26.1–26.16）を並べると次のとおり。
多くは GBM 仮定下で**解析解**を持ち、ないものはツリーか MC で評価します（「Hull の評価法」は本文の記述）：

| § | 型 | 特徴 | Hull の評価法 |
|---|---|---|---|
| 26.1 | パッケージ | バニラ・フォワード・現金・原資産の組み合わせ（レンジ・フォワード、支払繰延べ型） | 構成要素の和 |
| 26.2 | 永久アメリカン | 満期なしのアメリカン・コール／プット | 閉形式（最適行使境界 $H_1, H_2$） |
| 26.3 | 非標準アメリカン | 行使日を限定（バミューダン）、ロックアウト期間、行使価格の変化 | 二項ツリーで行使判定を変える |
| 26.4 | ギャップ | $S_T > K_2$ のとき $S_T - K_1$ を支払う | BSM の修正（閉形式） |
| 26.5 | フォワード・スタート | $T_1$ に ATM で始まるオプション | $c\,e^{-qT_1}$ |
| 26.6 | クリケ（ラチェット） | 行使価格をリセットするオプションの列 | 通常オプション＋フォワード・スタートの和、複雑なら MC |
| 26.7 | コンパウンド | オプションのオプション（4 種） | 2 変量正規分布 $M$ による閉形式（Geske） |
| 26.8 | チューザー | $T_1$ にコールかプットを選ぶ | 同一 $K, T_2$ ならコール＋プットのパッケージ |
| 26.9 | バリア | 到達で発生（in）／消滅（out） | 閉形式（in＋out＝バニラ）、離散観測は BGK 補正、パリジャンはツリー／MC |
| 26.10 | バイナリ | 不連続ペイオフ（cash／asset-or-nothing） | 閉形式 |
| 26.11 | ルックバック | 経路の最大／最小（フローティング・フィックスト） | 閉形式 |
| 26.12 | シャウト | 一度だけ「叫んだ」時点の本源的価値を下限として確保 | 二項／三項ツリー |
| 26.13 | アジアン | 平均価格でペイオフ | 算術平均を対数正規で近似しモーメント整合＋Black（26.3/26.4）（幾何平均は厳密に対数正規） |
| 26.14 | 交換 | 資産 $U$ を資産 $V$ と交換 | Margrabe（26.5、r 非依存） |
| 26.15 | 複数資産（レインボー） | 2 資産以上に依存（バスケットなど） | バスケットはモーメント整合＋Black か相関 GBM の MC |
| 26.16 | ボラティリティ／バリアンス・スワップ | 実現ボラ・実現分散を固定値と交換 | バリアンスはプット・コールのストリップで複製（26.6–26.8）、ボラ・スワップはより難しい |

§26.17 の**静的オプション複製**は商品ではなく、上の商品をバニラの組み合わせでヘッジする技法です。""")
)
cells.append(
    md(r"""> **核心** — 経路依存・多資産・条件付きなど、バニラを超える構造の分類。<br>
> **直感** — 多くは既知の部品(バニラ・バイナリ)に分解できる。<br>
> **実務** — 商品設計とリスク分解の地図。分解して値付け・ヘッジする。""")
)

# Section 2: §26.10 binary options
cells.append(
    md(r"""## 2. バイナリ・オプション（§26.10）

### 2.1 4つの満期給付と決済規約

現金額 $Q$ と満期原資産価格 $S_T$ に対して、4契約の給付は

$$
\begin{aligned}
X_{\mathrm{cash\ call}}&=Q\,1_{\{S_T\ge K\}}, &
X_{\mathrm{cash\ put}}&=Q\,1_{\{S_T<K\}},\\
X_{\mathrm{asset\ call}}&=S_T\,1_{\{S_T\ge K\}}, &
X_{\mathrm{asset\ put}}&=S_T\,1_{\{S_T<K\}}.
\end{aligned}
$$

ここでは **call は $S_T\ge K$、put は $S_T<K$** を採用します。これは契約上の決済規約です。
正の $T,\sigma$ を持つ連続分布モデルでは $P(S_T=K)=0$ なので、等号の割当ては時点0価格を変えません。
図の塗りつぶし点が実際の決済、白抜き点が反対側の片側極限です。""")
)

cells.append(
    code(r"""S_BIN, K_BIN = 100.0, 100.0
R_BIN, QDIV_BIN, SIG_BIN, T_BIN = 0.05, 0.02, 0.20, 1.0
PAYOUT_BIN = 100.0

binary_figures = _figures(
    S0=S_BIN,
    K=K_BIN,
    r=R_BIN,
    q=QDIV_BIN,
    sigma=SIG_BIN,
    T=T_BIN,
    payout=PAYOUT_BIN,
)

# §3以降の既存セルが使う q=0・unit-cash の互換変数。
S_B, K_B, R_B, SIG_B, T_B = 100.0, 100.0, 0.05, 0.20, 1.0
aon = exotics.asset_or_nothing(S_B, K_B, R_B, SIG_B, T_B, kind="call")
con = exotics.cash_or_nothing(S_B, K_B, R_B, SIG_B, T_B, kind="call", payout=1.0)
van = bsm.call_price(S_B, K_B, R_B, SIG_B, T_B)""")
)

cells.append(code(r"""binary_figures["binary_payoffs"].show()"""))

cells.append(
    md(r"""### 2.2 GBM仮定と4つの時点0価格

欧州型で満期だけを観測し、リスク中立下の GBM

$$dS_t=(r-q)S_t\,dt+\sigma S_t\,dW_t$$

と定数 $r,q,\sigma$ を仮定します。$S_0,K,Q$ は通貨、$T$ は年、$r,q$ は連続複利の年率、
$\sigma$ は年率ボラティリティです。閉形式の価格領域は $S_0,K,T,\sigma>0$ です。

$$
d_1=\frac{\log(S_0/K)+(r-q+\sigma^2/2)T}{\sigma\sqrt T},\qquad
d_2=d_1-\sigma\sqrt T.
$$

ここで $N$ は標準正規分布の累積分布関数です。

$$
\begin{aligned}
V_{\mathrm{cash\ call}}&=Qe^{-rT}N(d_2), &
V_{\mathrm{cash\ put}}&=Qe^{-rT}N(-d_2),\\
V_{\mathrm{asset\ call}}&=S_0e^{-qT}N(d_1), &
V_{\mathrm{asset\ put}}&=S_0e^{-qT}N(-d_1).
\end{aligned}
$$

$N(d_2)$ と $N(-d_2)$ はリスク中立測度での call/put 発生確率です。一方、

$$
N(d_1)=\frac{E^{\mathbb Q}[S_T1_{\{S_T\ge K\}}]}{E^{\mathbb Q}[S_T]},\qquad
N(-d_1)=\frac{E^{\mathbb Q}[S_T1_{\{S_T<K\}}]}{E^{\mathbb Q}[S_T]}
$$

はそれぞれの事象を満期資産で重み付けした確率、すなわち配当再投資後の total-return stock を
ニュメレールとする測度での確率に対応し、同じリスク中立事象確率ではありません。
この違いが現金給付の $e^{-rT}$ と資産給付の $e^{-qT}$ に現れます。""")
)

cells.append(
    code(r"""binary_prices = {
    "cash call": exotics.cash_or_nothing(
        S_BIN, K_BIN, R_BIN, SIG_BIN, T_BIN, q=QDIV_BIN, kind="call", payout=PAYOUT_BIN
    ),
    "cash put": exotics.cash_or_nothing(
        S_BIN, K_BIN, R_BIN, SIG_BIN, T_BIN, q=QDIV_BIN, kind="put", payout=PAYOUT_BIN
    ),
    "asset call": exotics.asset_or_nothing(
        S_BIN, K_BIN, R_BIN, SIG_BIN, T_BIN, q=QDIV_BIN, kind="call"
    ),
    "asset put": exotics.asset_or_nothing(
        S_BIN, K_BIN, R_BIN, SIG_BIN, T_BIN, q=QDIV_BIN, kind="put"
    ),
}
binary_price_table = pd.DataFrame(
    {"price（通貨）": [f"{binary_prices[label]:.6f}" for label in binary_prices]},
    index=pd.Index(binary_prices, name="contract"),
)
display(binary_price_table)""")
)

cells.append(
    md(r"""### 2.3 call/putの給付分解と現在価値

複製では任意の $Q$ を持つ価格表と区別し、cash binary の支払額を **$Q=K$** にします。

$$
\begin{aligned}
(S_T-K)^+&=S_T1_{\{S_T\ge K\}}-K1_{\{S_T\ge K\}},\\
(K-S_T)^+&=K1_{\{S_T<K\}}-S_T1_{\{S_T<K\}}.
\end{aligned}
$$

したがって現在価値でも

$$c=V_{\mathrm{asset\ call}}-V_{\mathrm{cash\ call}}(Q=K),\qquad
p=V_{\mathrm{cash\ put}}(Q=K)-V_{\mathrm{asset\ put}}$$

です。call の $S_T=K$ では2脚が相殺し、put では2脚とも0なので、選択した等号規約でも分解が成立します。""")
)

cells.append(
    code(r"""PAYOUT_REPLICATION_BIN = K_BIN
cash_call_repl = exotics.cash_or_nothing(
    S_BIN, K_BIN, R_BIN, SIG_BIN, T_BIN,
    q=QDIV_BIN, kind="call", payout=PAYOUT_REPLICATION_BIN,
)
cash_put_repl = exotics.cash_or_nothing(
    S_BIN, K_BIN, R_BIN, SIG_BIN, T_BIN,
    q=QDIV_BIN, kind="put", payout=PAYOUT_REPLICATION_BIN,
)
asset_call_repl = exotics.asset_or_nothing(
    S_BIN, K_BIN, R_BIN, SIG_BIN, T_BIN, q=QDIV_BIN, kind="call"
)
asset_put_repl = exotics.asset_or_nothing(
    S_BIN, K_BIN, R_BIN, SIG_BIN, T_BIN, q=QDIV_BIN, kind="put"
)
call_replication = asset_call_repl - cash_call_repl
put_replication = cash_put_repl - asset_put_repl
call_vanilla_bin = bsm.call_price(S_BIN, K_BIN, R_BIN, SIG_BIN, T_BIN, q=QDIV_BIN)
put_vanilla_bin = bsm.put_price(S_BIN, K_BIN, R_BIN, SIG_BIN, T_BIN, q=QDIV_BIN)

display(pd.DataFrame(
    {
        "binary replication": [f"{call_replication:.6f}", f"{put_replication:.6f}"],
        "vanilla price": [f"{call_vanilla_bin:.6f}", f"{put_vanilla_bin:.6f}"],
        "difference": [
            f"{call_replication - call_vanilla_bin:.6e}",
            f"{put_replication - put_vanilla_bin:.6e}",
        ],
    },
    index=pd.Index(["call", "put"], name="kind"),
))""")
)

cells.append(code(r"""binary_figures["binary_replication"].show()"""))

cells.append(
    md(r"""### 2.4 不連続給付と決済リスク

現金給付のバイナリーは $K$ のごく近くで小さな参照価格差が $Q$ の給付差になり、
資産給付のバイナリーでもジャンプ幅は $K$ になります。とくに取引の薄い市場では、
満期判定の価格が一時的な需給の影響を受けやすく、モデル価格だけでは決済リスクを解消できません。
契約時に参照市場・価格ソース・判定時刻・丸め・障害時の代替手順・紛争処理を合意し、
図の片側極限と実際の等号決済を区別することが重要です。""")
)

cells.append(
    md(r"""### 2.5 call spread、butterfly、行使価格微分

幅 $h$ の centered call spread の満期給付

$$\frac{(S_T-(K-h/2))^+-(S_T-(K+h/2))^+}{h}$$

は $S_T\ne K$ で unit cash call の給付へ収束します。ただし $S_T=K$ ではすべての $h>0$ で $1/2$ であり、
採用した等号決済値1とは一致しません。価格について

$$-\frac{\partial C}{\partial K}=e^{-rT}N(d_2)$$

は unit cash digital（$Q=1$）の現在価値です。$C(K)$ を、$S_0,r,q,\sigma,T$ を固定した同一満期の
欧州 call 価格（行使価格 $K$ の関数）とします。正規化した centered butterfly 価格には

$$
\frac{C(K-h)-2C(K)+C(K+h)}{h^2}
\longrightarrow \frac{\partial^2 C}{\partial K^2}
=e^{-rT}f_{S_T}^{\mathbb Q}(K)
$$

という極限があり、$f_{S_T}^{\mathbb Q}$ はリスク中立測度での満期価格密度です。この極限は
割引された満期密度で、デジタル給付そのものではありません。下図は価格密度ではなく、
$[(S_T-(K-h))^+-2(S_T-K)^++(S_T-(K+h))^+]/h^2$ で正規化した満期給付を描き、
幅 $h=1,5,15$ の局所化を比べます。""")
)

cells.append(code(r"""binary_figures["binary_spreads"].show()"""))

cells.append(
    md(r"""### 2.6 有限残存期間のcash-callデルタ

$T>0$ の cash-or-nothing call のデルタは

$$
\Delta_{\mathrm{cash\ call}}
=\frac{Qe^{-rT}\phi(d_2)}{S_0\sigma\sqrt T}
$$

$\phi$ は標準正規密度です。このデルタは正の $S_0,K,T,\sigma$ の各点では有限です。満期へ近づくと $K$ 近傍へ鋭く集中し、
$S_0\ne K$ では0へ向かいます。有限時間のデルタを「発散」と呼ばず、不連続な満期給付へ近づく極限と
区別します。図は $T=1$ 年、30日、1日の同じ合成市場を比較します。""")
)

cells.append(code(r"""binary_figures["binary_delta"].show()"""))

# §26.9 acceptance pilot: definitions, branches, monitoring, risk and Parisian.
cells.append(
    md(r"""## 3. バリア・オプション（§26.9、GE pp.620–622）

**到達目標**：8種類の契約を payoff から区別し、価格式の分岐、観測頻度、負のベガ、
Parisian の滞在条件を説明できること。この節の数値はすべて**教材用の合成例**です。

### 3.1 終値だけでは決まらない

$S_0$ は現在価格、$K$ は行使価格、$H$ はバリア（すべて同じ通貨単位）。
$T$ は残存年数、$r,q$ は年率の連続複利金利・配当利回り、$\sigma$ は年率ボラティリティ。
まずリスク中立下で $dS_t=(r-q)S_tdt+\sigma S_tdW_t$、定数パラメータ、欧州型、
**リベート（到達時などの払戻し）0、期間 $[0,T]$ の連続観測**を仮定します。

下方は $\tau_d=\inf\{t\ge0:S_t\le H\}$、上方は $\tau_u=\inf\{t\ge0:S_t\ge H\}$。
等号も到達に含めます。新規の未到達契約は down なら $H<S_0$、up なら $H>S_0$。
実装は時点0も観測し、すでに到達していれば in はバニラ、out は0を返します。
過去の到達履歴は入力しないため、評価開始前の状態は契約側で管理します。

$G_c=(S_T-K)^+$、$G_p=(K-S_T)^+$ とすると、8種類は次の4組です。

| 方向・権利 | in の満期 payoff | out の満期 payoff |
|---|---|---|
| down call | $G_c1_{\{\tau_d\le T\}}$ | $G_c1_{\{\tau_d>T\}}$ |
| up call | $G_c1_{\{\tau_u\le T\}}$ | $G_c1_{\{\tau_u>T\}}$ |
| down put | $G_p1_{\{\tau_d\le T\}}$ | $G_p1_{\{\tau_d>T\}}$ |
| up put | $G_p1_{\{\tau_u\le T\}}$ | $G_p1_{\{\tau_u>T\}}$ |

各経路で $G1_{\{\tau\le T\}}+G1_{\{\tau>T\}}=G$。割引期待値を取れば
$V_{\rm in}+V_{\rm out}=V_{\rm vanilla}$、かつ $0\le V_{\rm in},V_{\rm out}\le V_{\rm vanilla}$。
同じ $H,K,T$ と観測規則の組で成り立ちます。両方の payoff が0の経路もあります。
消滅・未発生の可能性により価格が抑えられますが、リベートを付けた契約にはこの分解をそのまま使えません。""")
)

cells.append(
    code(r"""# 同じ始値100・終値110でも、H=90への途中の到達が契約を分ける。
path_t = np.array([0, .2, .4, .6, .8, 1.0])
path_safe = np.array([100, 96, 94, 98, 104, 110])
path_hit = np.array([100, 95, 88, 97, 103, 110])
fig_path, axes_path = plt.subplots(1, 2, figsize=(11, 3.8), constrained_layout=True)
fig_path.canvas.header_visible = False
payoff_rows = []
for label, prices in (("未到達", path_safe), ("途中で到達", path_hit)):
    hit = prices.min() <= 90
    payoff = max(prices[-1] - 100, 0)
    payoff_rows.append((label, payoff * hit, payoff * (not hit)))
    axes_path[0].plot(path_t, prices, marker="o", label=label)
axes_path[0].axhline(90, color="crimson", ls="--", label="H=90")
axes_path[0].set(xlabel="時刻（年）", ylabel="原資産価格", title="同じ終値、異なる到達履歴")
axes_path[0].legend()
x_path = np.arange(2)
axes_path[1].bar(x_path - .17, [row[1] for row in payoff_rows], width=.34, label="down-and-in")
axes_path[1].bar(x_path + .17, [row[2] for row in payoff_rows], width=.34, label="down-and-out")
axes_path[1].set(xticks=x_path, xticklabels=[row[0] for row in payoff_rows],
                 ylabel="満期 payoff", title="K=100：合計はどちらも10")
axes_path[1].legend()
assert all(row[1] + row[2] == 10 for row in payoff_rows)
display(fig_path.canvas)
print("図の経路は点間を直線で結んだ合成例。満期 payoff と時点0の価格を区別する。")""")
)

cells.append(
    md(r"""### 3.2 閉形式の全分岐を読む

$\Phi$ を標準正規 CDF、$c,p$ を同じ条件の BSM バニラ価格として、記号をまとめます。

$$s=\sigma\sqrt T,\quad \lambda=\frac{r-q+\sigma^2/2}{\sigma^2},\quad
x=\frac{\ln(S_0/H)}s+\lambda s,\quad
y_1=\frac{\ln(H/S_0)}s+\lambda s,\quad
y=\frac{\ln(H^2/(S_0K))}s+\lambda s.$$

$$A=S_0e^{-qT},\quad B=Ke^{-rT},\quad
U=A(H/S_0)^{2\lambda},\quad W=B(H/S_0)^{2\lambda-2}.$$

以下は到達前の連続観測の式です。まず表の側を求め、対応する in/out はバニラから差し引きます。
$H=K$ では隣り合う式の値が一致します。

| 組 | 条件 | 直接求める価格 | もう一方 |
|---|---|---|---|
| down call | $H\le K$ | $c_{di}=U\Phi(y)-W\Phi(y-s)$ | $c_{do}=c-c_{di}$ |
| down call | $H>K$ | 下の $C_d$ | $c_{di}=c-C_d$ |
| up call | $H\le K$ | $c_{uo}=0$ | $c_{ui}=c$ |
| up call | $H>K$ | 下の $C_u$ | $c_{uo}=c-C_u$ |
| up put | $H\ge K$ | $p_{ui}=-U\Phi(-y)+W\Phi(-y+s)$ | $p_{uo}=p-p_{ui}$ |
| up put | $H<K$ | 下の $P_u$ | $p_{ui}=p-P_u$ |
| down put | $H\ge K$ | $p_{do}=0$ | $p_{di}=p$ |
| down put | $H<K$ | 下の $P_d$ | $p_{do}=p-P_d$ |

$$\begin{aligned}
C_d=c_{do}&=A\Phi(x)-B\Phi(x-s)-U\Phi(y_1)+W\Phi(y_1-s),\\
C_u=c_{ui}&=A\Phi(x)-B\Phi(x-s)
-U[\Phi(-y)-\Phi(-y_1)]+W[\Phi(-y+s)-\Phi(-y_1+s)],\\
P_u=p_{uo}&=-A\Phi(-x)+B\Phi(-x+s)+U\Phi(-y_1)-W\Phi(-y_1+s),\\
P_d=p_{di}&=-A\Phi(-x)+B\Phi(-x+s)
+U[\Phi(y)-\Phi(y_1)]-W[\Phi(y-s)-\Phi(y_1-s)].
\end{aligned}$$

**縮退の理由**：up call で $H\le K$ なら、正の payoff を得る経路は $S_T>K\ge H$ へ進むため
必ず到達します。到達確率そのものが1という意味ではありません。
down put の $H\ge K$ も同様です。
下の表では $K=80,100,120$ を変えて両側の分岐を含めます。

**別の計算法で検証**：$X=\ln(S_T/S_0)$ は平均 $(r-q-\sigma^2/2)T$、分散 $v=\sigma^2T$ の正規分布です。
$h=\ln(H/S_0)$ とし、始点・終点がバリアの安全側にある場合、
条件付き Brownian bridge の生存確率は
$w_{\rm out}(X)=1-\exp[-2h(h-X)/v]$。終点が到達側なら0です。
したがって $e^{-rT}\int G(S_0e^x)w_{\rm out}(x)f_X(x)\,dx$ を数値積分しても out の価格を求められます。
in は積分内の重みを $1-w_{\rm out}$ に変更します。
この方法は上の CDF 価格式や価格の差引きを参照しません。
独立テストは8種類・$H\lessgtr K$・$H=K$・配当・負の金利を含む48ケースを照合します。""")
)

cells.append(
    code(r"""# 8種類 × 3ストライク。価格式の分岐を通り、同じ条件の in/out を比較する。
barrier_rows = []
for kind, pricer, vanilla_fn in (("call", exotics.barrier_call, bsm.call_price),
                                ("put", exotics.barrier_put, bsm.put_price)):
    for direction, barrier_h in (("down", 90.0), ("up", 110.0)):
        for knock in ("in", "out"):
            row = {"契約": f"{direction}-and-{knock} {kind}", "H": barrier_h}
            for strike in (80.0, 100.0, 120.0):
                value = pricer(100, strike, barrier_h, .05, .2, 1, barrier=f"{direction}-and-{knock}")
                row[f"K={strike:g}"] = value
                assert -1e-10 <= value <= vanilla_fn(100, strike, .05, .2, 1) + 1e-10
            barrier_rows.append(row)
display(pd.DataFrame(barrier_rows).round(4))
cdi = exotics.barrier_call(S_B, K_B, 90, R_B, SIG_B, T_B, barrier="down-and-in")
cdo = exotics.barrier_call(S_B, K_B, 90, R_B, SIG_B, T_B, barrier="down-and-out")
fig2, axes2 = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
fig2.canvas.header_visible = False
for ax, (kind, direction) in zip(axes2.flat, [("call", "down"), ("call", "up"),
                                             ("put", "down"), ("put", "up")]):
    pricer = exotics.barrier_call if kind == "call" else exotics.barrier_put
    vanilla_fn = bsm.call_price if kind == "call" else bsm.put_price
    hs = np.linspace(60, 100, 65) if direction == "down" else np.linspace(100, 160, 65)
    values = {}
    for knock in ("in", "out"):
        values[knock] = np.array([pricer(100, 100, h, .05, .2, 1, barrier=f"{direction}-and-{knock}")
                                  for h in hs])
        ax.plot(hs, values[knock], label=f"{direction}-and-{knock}")
    van_barrier = vanilla_fn(100, 100, .05, .2, 1)
    assert np.allclose(values["in"] + values["out"], van_barrier, atol=1e-10)
    ax.axhline(van_barrier, color=".5", ls=":", label=f"vanilla {kind}")
    ax.axvline(100, color=".7", ls=":")
    ax.set(xlabel="バリア H", ylabel="時点0の価格", title=f"{direction} {kind}（S0=K=100）")
    ax.legend(fontsize=9)
display(fig2.canvas)
print("r=5%, q=0, σ=20%, T=1年。Hが現在価格S0へ近づくほど out↓・in↑。")""")
)

cells.append(
    md(r"""### 3.3 観測頻度と BGK 近似

連続観測と、決まった時刻だけ観測する契約では到達イベントが異なります。
時点0に加え $jT/m$（$j=1,\ldots,m$）を観測すると、観測間の一時的な到達を見逃します。
同じ契約バリアなら、離散観測の out は連続観測以上、in は連続観測以下の価格になります。

Hull p.622 の Broadie–Glasserman–Kou 補正は、連続式のバリアを

$$H_{\rm BGK}=H\exp(\pm0.5826\,\sigma\sqrt{T/m})$$

へ移す**近似**です。up は $+$、down は $-$ で、現在価格から遠ざけます。
$m\to\infty$ で補正は消えます。実装の n_observations に $m$ を渡すとこの補正が有効です。
$T$ は年、$m$ は期間全体の観測回数で、日次なら1年の例では252です。

下の週次 up-and-in put は、観測日時の GBM を直接生成した MC と BGK を比較します。
誤差棒は MC の $\pm3$ 標準誤差であり、BGK の誤差保証ではありません。
少数観測、$S_0$ が $H$ に近い契約、不等間隔の監視は、この1例から精度を判断できません。
実際の観測日程を用いる MC 等で別途確認します。

**近似でも維持する厳密条件**：満期 $T$ が観測日なので、up-and-out call の $H\le K$ と
down-and-out put の $H\ge K$ は離散観測でも価格0です。正の満期 payoff を得る価格に到達すると、
その満期観測で必ず消滅するためです。対応する in はバニラ価格になります。
この条件は補正後のバリアでなく、元の契約バリアで判定します。

""")
)

cells.append(
    code(r"""# 週次監視の独立 MC。連続式をシミュレーションの payoff 判定には使用しない。
obs_m, obs_n, obs_sigma = 52, 200_000, .30
obs_rng = np.random.default_rng(2026)
obs_log = np.zeros(obs_n)
obs_hit = np.zeros(obs_n, dtype=bool)
for _ in range(obs_m):
    obs_log += (.05 - .5 * obs_sigma**2) / obs_m + obs_sigma / math.sqrt(obs_m) * obs_rng.standard_normal(obs_n)
    obs_hit |= obs_log >= math.log(1.2)
obs_payoff = math.exp(-.05) * np.maximum(100 - 100 * np.exp(obs_log), 0) * obs_hit
obs_mc = obs_payoff.mean()
obs_se = obs_payoff.std(ddof=1) / math.sqrt(obs_n)
obs_grid = np.array([4, 12, 52, 252, 1000, 10000])
obs_prices = [exotics.barrier_put(100, 100, 120, .05, .3, 1,
              barrier="up-and-in", n_observations=int(m)) for m in obs_grid]
obs_cont = exotics.barrier_put(100, 100, 120, .05, .3, 1, barrier="up-and-in")
fig_obs, ax_obs = plt.subplots(figsize=(8, 3.7), constrained_layout=True)
fig_obs.canvas.header_visible = False
ax_obs.semilogx(obs_grid, obs_prices, marker="o", label="BGK 近似：up-and-in put")
ax_obs.axhline(obs_cont, color=".5", ls="--", label="連続観測")
ax_obs.errorbar([52], [obs_mc], yerr=[3 * obs_se], fmt="s", capsize=6, label="週次 MC ±3 SE")
ax_obs.set(xlabel="期間1年の観測回数 m（対数軸）", ylabel="価格",
           title="S0=K=100, H=120, r=5%, q=0, σ=30%")
ax_obs.legend()
display(fig_obs.canvas)
print(f"週次 MC={obs_mc:.5f}, SE={obs_se:.5f}; BGK={obs_prices[2]:.5f}; 連続={obs_cont:.5f}")
assert abs(obs_prices[2] - obs_mc) < 3 * obs_se

# 満期観測からの厳密条件は、BGKがHをKの向こう側へ動かしても維持する。
for fixing_count in (4, 52):
    zero_call = exotics.barrier_call(100, 110, 110, .05, .3, 1,
                                    barrier="up-and-out", n_observations=fixing_count)
    zero_put = exotics.barrier_put(100, 90, 90, .05, .3, 1,
                                  barrier="down-and-out", n_observations=fixing_count)
    assert zero_call == zero_put == 0.0
    print(f"満期を含む年{fixing_count}回観測：H=K の up-out call / down-out put = {zero_call:g} / {zero_put:g}")


""")
)
cells.append(
    md(r"""### 3.4 ボラティリティが上がると安くなることもある

up-and-out call では、ボラ増加によるバニラ価値の増加と、消滅確率の増加が競合します。
$S_0=99,H=100,K=90$ の例では後者が勝ち、$\partial V/\partial\sigma<0$。
負のベガはすべてのバリア・全パラメータで成り立つ法則ではありません。
隣のバニラの正のベガと比較してください。""")
)
cells.append(
    code(r"""vega_sigmas = np.linspace(.10, .50, 65)
vega_out = [exotics.barrier_call(99, 90, 100, .05, s, 1, barrier="up-and-out") for s in vega_sigmas]
vega_van = [bsm.call_price(99, 90, .05, s, 1) for s in vega_sigmas]
fig_vega, axes_vega = plt.subplots(1, 2, figsize=(10, 3.6), constrained_layout=True)
fig_vega.canvas.header_visible = False
for ax, prices, title in zip(axes_vega, [vega_out, vega_van],
                            ["up-and-out call：この範囲で負のベガ", "同条件の vanilla call：正のベガ"]):
    ax.plot(100 * vega_sigmas, prices, lw=2)
    ax.set(xlabel="年率ボラティリティ σ（%）", ylabel="価格", title=title)
assert np.all(np.diff(vega_out) < 0) and np.all(np.diff(vega_van) > 0)
display(fig_vega.canvas)
vega_difference = (exotics.barrier_call(99, 90, 100, .05, .21, 1, barrier="up-and-out")
                   - exotics.barrier_call(99, 90, 100, .05, .20, 1, barrier="up-and-out"))
print(f"S0=99, K=90, H=100, T=1年, r=5%, q=0。σを20%→21%にすると out の価格変化={vega_difference:.6f}。")""")
)

cells.append(
    md(r"""### 3.5 Parisian：一瞬の到達と滞在時間を分ける

通常のバリアでは短いスパイクでも到達が成立します。Parisian はバリアの外側に
一定期間滞在することを条件にします。契約で「連続50日」か「累積50日」かを確認する必要があります。

Hull p.622 の契約例は、down-and-out put、$K=0.9S_0$、$H=0.75S_0$、閾値50日。
下図はこれに合わせた**合成の経路**です。原資産価格は各1日区間で一定とし、滞在時間を正確に数えます。
経路Aは30日と20日に分かれ、経路Bは50日続けてバリアを下回ります。
どちらも満期 $S_T=80$、バニラ put payoff は10です。

| 契約 | 経路A：30日+20日 | 経路B：連続50日 |
|---|---|---|
| 通常 down-and-out put | 最初の到達で消滅 | 最初の到達で消滅 |
| Parisian・連続50日 | 生存、payoff 10 | 消滅、payoff 0 |
| Parisian・累積50日 | 消滅、payoff 0 | 消滅、payoff 0 |

リベート0とし、滞在時間が閾値に達した時点で消滅する規約です。
通常の barrier_call / barrier_put はこの滞在履歴を持たず、Parisian の価格には使えません。
ここでは契約の違いと payoff 判定までを扱います。価格を求める MC・二項木と必要な工夫は
§27.5–27.6 の学習へ接続します。""")
)

cells.append(
    code(r"""# 各区間 [day, day+1) は1日。最後の時点の価格は滞在日数に加えない。
par_days = np.arange(101)
par_a = np.where(((par_days >= 10) & (par_days < 40)) |
                 ((par_days >= 60) & (par_days < 80)), 70.0, 100.0)
par_b = np.where((par_days >= 10) & (par_days < 60), 70.0, 100.0)
par_a[-1] = par_b[-1] = 80.0

def _longest_stay(mask):
    longest = current = 0
    for below in mask:
        current = current + 1 if below else 0
        longest = max(longest, current)
    return longest

fig_par, axes_par = plt.subplots(1, 2, figsize=(11, 3.7), constrained_layout=True)
fig_par.canvas.header_visible = False
for ax, label, prices in zip(axes_par, ["A：30日 + 20日", "B：連続50日"], [par_a, par_b]):
    below = prices[:-1] < 75
    consecutive, total = _longest_stay(below), int(below.sum())
    ax.step(par_days, prices, where="post", label="原資産価格")
    ax.axhline(75, color="crimson", ls="--", label="H=75")
    ax.set(xlabel="日", ylabel="原資産価格",
           title=f"{label}（最大連続={consecutive}, 累積={total}日）")
    ax.legend(loc="lower right")
    payoff = max(90 - prices[-1], 0)
    print(f"{label}: 通常out={payoff * (not below.any()):g}, "
          f"連続50日out={payoff * (consecutive < 50):g}, 累積50日out={payoff * (total < 50):g}")
assert (_longest_stay(par_a[:-1] < 75), _longest_stay(par_b[:-1] < 75)) == (30, 50)
assert (par_a[:-1] < 75).sum() == (par_b[:-1] < 75).sum() == 50
display(fig_par.canvas)""")
)

cells.append(
    md(r"""### 3.6 8種類を操作して確認する

選択欄から call/put・up/down・in/out を切り替えます。選んだ契約を実線、
対応する契約を破線、バニラを点線で表示します。
縦点線 $H=S_0$ で、in はバニラへ、out は0へ接続することを確認してください。
静的な表示では上の4面図が8種類をカバーします。以下の操作図は Book と portal でも動作します。

**理解の確認**
1. $S_0=90,H=105,K=120$ の up-and-out call が0になる理由は？
2. 観測回数を減らすと、同じ $H$ の out が高くなる理由は？
3. ボラ増加で up-and-out call が安くなる経路上の理由は？
4. バリアの下に30日、その後20日滞在した場合、連続50日と累積50日で何が変わる？

**解答の要点**：1. 正の call payoff には $H$ を通過する必要がある。
2. 観測間の到達が消滅条件に数えられず、生存経路が増える。
3. 消滅する経路の増加がバニラ価値の増加を上回る場合がある。
4. 連続条件は未成立、累積条件は成立する。""")
)

cells.append(
    code(r"""from hullkit import plotly_viz

fig_barrier_explorer = plotly_viz.plotly_barrier_knockout()
fig_barrier_explorer.show()""")
)

# Cell 08: lookback md + demo
cells.append(
    md(r"""## 4. ルックバックとアジアン

### 4.1 ルックバック・オプション（§26.11）

#### 4.1.1 契約と過去の極値

Hull GE pp.623–625。以下はすべて合成例です。$S_0,K,m_0,M_0$ と給付・価格の単位は通貨、
$T$ は年、$r,q$ は連続複利の年率、$\sigma$ は年率ボラティリティです。
過去の最小値 $m_0$ と最大値 $M_0$ は今日を含み、$0<m_0\le S_0\le M_0$。
新規契約では $m_0=M_0=S_0$ です。満期までの観測も今日と満期を含めます。

$$m_T=\min\{m_0,\inf_{0\le t\le T}S_t\},\qquad
M_T=\max\{M_0,\sup_{0\le t\le T}S_t\}.$$

|契約|満期給付（通貨）|意味|
|---|---|---|
|floating call|$S_T-m_T$|最安値で買う|
|floating put|$M_T-S_T$|最高値で売る|
|fixed call|$(M_T-K)^+$|最高値と固定行使価格を比較|
|fixed put|$(K-m_T)^+$|最安値と固定行使価格を比較|

下図は9節点を直線補間した決定論的経路です。棒はこの経路の**満期給付**であり現在価格ではありません。
過去の極値を $(100,100)$ から $(80,130)$ に変え、将来経路が同じでも給付が変わることを確認します。""")
)
cells.append(
    code(r"""from hullkit._lookback_lesson import _figures as lookback_lesson_figures

lookback_figures = lookback_lesson_figures()
lb = exotics.lookback_floating_call(S_B, S_B, R_B, SIG_B, T_B)
lookback_figures["lookback_payoffs"].show()""")
)
cells.append(
    md(r"""#### 4.1.2 フローティング価格式と Example 26.2

連続観測、一定係数のリスク中立 GBM $dS_t=(r-q)S_tdt+\sigma S_tdW_t$ を仮定します。
$S_0,T,\sigma>0$、有効な過去の極値、$r\ne q$ の場合の式です。
$N$ は標準正規分布関数、$d=r-q$、$A=\sigma^2/(2d)$ とおきます。
式を短く分けて示すと、

$$c_{\rm fl}=S_0e^{-qT}\{N(a_1)-A N(-a_1)\}
-m_0e^{-rT}\{N(a_2)-A e^{Y_1}N(-a_3)\},$$

$$a_1=\frac{\ln(S_0/m_0)+(d+\sigma^2/2)T}{\sigma\sqrt T},
\qquad a_2=a_1-\sigma\sqrt T,$$

$$a_3=\frac{\ln(S_0/m_0)+(-d+\sigma^2/2)T}{\sigma\sqrt T},
\qquad Y_1=-\frac{2(d-\sigma^2/2)\ln(S_0/m_0)}{\sigma^2}.$$

同じ記法で put は

$$p_{\rm fl}=M_0e^{-rT}\{N(b_1)-A e^{Y_2}N(-b_3)\}
+S_0e^{-qT}\{A N(-b_2)-N(b_2)\},$$

$$b_1=\frac{\ln(M_0/S_0)+(-d+\sigma^2/2)T}{\sigma\sqrt T},
\qquad b_2=b_1-\sigma\sqrt T,$$

$$b_3=\frac{\ln(M_0/S_0)+(d-\sigma^2/2)T}{\sigma\sqrt T},
\qquad Y_2=\frac{2(d-\sigma^2/2)\ln(M_0/S_0)}{\sigma^2}.$$

$a_i,b_i,Y_i,A$ は無次元です。$e^{-rT}$ は現金の割引、$S_0e^{-qT}$ は配当を考慮した
満期の株式受渡しの現在価値。極値に依存する項が経路依存性を取り込みます。
価格は $e^{-rT}\mathbb E^Q[\text{満期給付}]$ であり、一つの標本経路の給付とは異なります。

**Example 26.2**：$S_0=m_0=M_0=50,r=0.10,q=0,\sigma=0.40,T=0.25$。
put の係数は $b_1=-0.025,b_2=-0.225,b_3=0.025,Y_2=0$。
原著の丸め値は call 8.04、put 7.79 です。""")
)
cells.append(
    code(r"""lookback_example = {
    "floating call": exotics.lookback_floating_call(50., 50., .10, .40, .25, q=0.),
    "floating put": exotics.lookback_floating_put(50., 50., .10, .40, .25, q=0.),
}
display(pd.DataFrame({
    "price（通貨）": [f"{v:.6f}" for v in lookback_example.values()],
    "原著の丸め": ["8.04", "7.79"],
}, index=pd.Index(lookback_example, name="contract")))""")
)
cells.append(
    md(r"""#### 4.1.3 過去の極値が現在価格に与える影響

$S_0=100,r=5\%,q=2\%,\sigma=20\%,T=1$ を固定します。
横軸は現在株価ではなく過去の最小値 $m_0$／最大値 $M_0$ です。
$m_0$ が低いほど floating call と fixed put は高く、$M_0$ が高いほど floating put と
fixed call は高くなります（弱い単調性）。floating の価格は $K$ に依存しません。
fixed put は $m_0\ge K$、fixed call は $M_0\le K$ の範囲で過去の極値を変えても価格が一定です。
この平坦部分は次の starred history から説明できます。""")
)
cells.append(code(r"""lookback_figures["lookback_history"].show()"""))
cells.append(
    md(r"""#### 4.1.4 固定行使価格の複製

$M_0^*=\max(M_0,K)$、$m_0^*=\min(m_0,K)$ を定義します。
星付き floating はこの修正した過去の極値と同じ満期を使う契約です。
満期には $M_T^*=\max(M_T,K)$、$m_T^*=\min(m_T,K)$ なので、経路ごとに

$$(M_T-K)^+=(M_T^*-S_T)+S_T-K,$$
$$(K-m_T)^+=(S_T-m_T^*)+K-S_T.$$

これは満期給付の恒等式です。各脚を現在価値にすると Hull の価格関係になります。

$$c_{\rm fix}=p_{\rm fl}^*+S_0e^{-qT}-Ke^{-rT},$$
$$p_{\rm fix}=c_{\rm fl}^*+Ke^{-rT}-S_0e^{-qT}.$$

下図は $m_0=85,M_0=120$、他の市場条件は前図と同じです。
各脚と合計はすべて**現在価格（通貨）**。合計だけでなく floating・株式・現金の各脚の
符号と値を確認します。$K$ が過去の極値を跨ぐと星付き履歴が切り替わります。
同一の原資産・満期・行使価格・観測規則なら、fixed call/put はそれぞれバニラ以上です。
floating call は $K\ge m_0$ のバニラ call 以上、floating put は $K\le M_0$ の
バニラ put 以上（いずれも今日・満期を観測）です。任意の $K$ への無条件な比較ではありません。""")
)
cells.append(code(r"""lookback_figures["lookback_replication"].show()"""))
cells.append(
    md(r"""#### 4.1.5 観測頻度と連続観測

解析式は連続観測です。離散 fixing では見逃した高値・安値によって給付が変わります。
今日と満期を含む入れ子の観測集合を増やすと、最小値は下がり最大値は上がるため、4給付は減りません。
ただし実際の契約では fixing 時刻、参照価格、休日、欠測処理も確定する必要があります。

図の1・2・4・8区間は同じ9節点の直線補間経路を観測します。8区間ならこの**人工的な折れ線**の
極値を完全に捉えます。これは連続 GBM の極値を有限格子で捕捉した証拠でも、価格精度・収束の検証でもありません。
離散観測の価格には専用モデルまたは補正の検証が必要です。""")
)
cells.append(code(r"""lookback_figures["lookback_monitoring"].show()"""))
cells.append(
    md(r"""#### 4.1.6 適用範囲と確認問題

**未対応境界：`abs(r-q)<1e-8` は既存 API が例外を返します。**
$r=q$ で式に現れる分母の特異性は除去可能であり、経済的価値が発散する意味ではありません。
原著は Problem 26.23 にこの場合を委ねています。本教材では極限エンジンを実装していません。
適用条件は $S_0,T,\sigma>0$、$0<m_0\le S_0\le M_0$、固定型では $K>0$、
連続観測の一定係数 GBM とします。満期ゼロ・ゼロボラ・離散契約への外挿は扱いません。

1. 同じ終値でも過去の極値を変えると、どの4給付がどれだけ変わるか。
2. $K=125,M_0=120$ の fixed call が、履歴をそのまま使った floating put では複製できない理由は何か。
3. fixing を増やすと給付はどう変わるか。それだけで解析価格の精度を主張できるか。
4. $r=q$ の除去可能特異点と、現在の API の未対応境界を区別して説明できるか。

数値は独立な極値分布の積分参照と照合し、共有図は Book とポータルの双方で操作・各脚・表示を検査します。""")
)

# Cell 08b: shout lesson
cells.append(
    md(r"""### 4.2 シャウト・オプション（§26.12）

#### 4.2.1 契約と50/60の例

満期までに一度だけシャウトでき、シャウトしない選択も残ります。早期に現金を受け取るアメリカン行使とは違い、給付は満期です。原著の主題は call です。
Hull の文字通りの読み方では、時刻 $\tau$ に原資産 $S_\tau$ でシャウトした給付は

$$H_T=\max(S_T-K,S_\tau-K)=(S_\tau-K)+(S_T-S_\tau)^+.$$

内在価値を床にする読み方は $\max((S_T-K)^+,(S_\tau-K)^+)$ です。
両者は $S_\tau\ge K$ で一致しますが、$S_\tau<K$ の文字通りの式には負の給付もあり得ます。
下の最適化は文字通りのシャウトを選ぶか、権利を残すかを比較し、満期には通常の非負給付を使います。
$S_\tau<K$ では文字通りの給付は欧州 call 以下、内在価値の床なら欧州 call と同じです。シャウトしない選択があるので、この領域の読み方の違いは最適価格を変えません。

原著の例は **K=50、シャウト時60**。満期給付は $\max(S_T-50,10)$ です。

|満期価格 $S_T$|40|60|75|
|---|---|---|---|
|通常 call の給付|0|10|25|
|シャウト後の給付|10|10|25|

これは原著の給付例であって、価格の引用ではありません。以下の市場価格と二項木は合成例です。""")
)

cells.append(
    code(r"""from hullkit._shout_lesson import _figures as shout_lesson_figures

shout_figures = shout_lesson_figures()
shout_figures["shout_payoff"].show()""")
)

cells.append(
    md(r"""#### 4.2.2 給付分解からシャウト価値へ

一定係数のリスク中立 GBM、連続配当利回り $q$ を仮定します。残存期間 $u=T-\tau$ とし、シャウト時の $S$ は観測済みです。

$$J(S,u)=(S-K)e^{-ru}+c_{\rm BS}(S,S,r,q,\sigma,u).$$

第1脚は満期の確定額 $S-K$ の現在価値、第2脚は行使価格を $S$ にリセットした欧州 ATM call です。
$S<K$ では現金脚は負です。符号を消すと別契約になります。両脚の和だけでなく個別の値を確認します。
満期給付の分解をそのまま現在価格と呼ばず、確定額を割り引き、残る call を評価してください。""")
)

cells.append(
    md(r"""#### 4.2.3 CRR後退計算と N=3 節点

$\Delta t=T/N$、$a=e^{\sigma\sqrt{\Delta t}}$、$b=1/a$ とおきます。

$$p=\frac{e^{(r-q)\Delta t}-b}{a-b},\qquad 0<p<1.$$

満期は $V_N(S)=(S-K)^+$。未シャウトの各節点では

$$C_i(S)=e^{-r\Delta t}\{pV_{i+1}(Sa)+(1-p)V_{i+1}(Sb)\},$$
$$V_i(S)=\max\{J(S,T-i\Delta t),C_i(S)\}.$$

アメリカン・オプションと同じ後退 max の手順ですが、障害値は即時行使価値でなく $J$ です。
権利を使えば残りは欧州 call のため、未使用権利の値だけを後退計算できます。同値なら宣言を選びます（価格は同じです）。
下図は $S_0=K=100,r=5\%,q=2\%,\sigma=20\%,T=1$、N=3 の10節点。
根の値は **11.681238968672309**。各非終端節点には符号付き現金脚、ATM脚、即時シャウト、継続、選択値を表示します。
終端では分解を計算せず通常の内在価値のみを示します。N=3 は手順の説明で、細格子の価格精度ではありません。""")
)

cells.append(
    code(r"""shout_figures["shout_decision"].show()""")
)

cells.append(
    md(r"""#### 4.2.4 境界と収束を読む

原著の連続時間の判断を、有限の CRR 判断日で近似します。有限木は連続時間問題の厳密解ではありません。
N=128/256/512/1024 の価格差は振動し得るため、単調収束を仮定しません。保存済み N=1024 の42価格行では
独立参照に対する最大絶対残差は約0.003793で、採用許容差0.005以内です。
これは検査範囲での経験的残差であって、全領域の証明された誤差上界ではありません。

左図の上下点は **同じ実際の CRR 層** にある継続／シャウト節点の区間です。層を補間していません。
独立 B 境界曲線が必ず区間内に入る保証はなく、positive-carry の残存0.5年では B は上端より約0.12618高いです。
long-high-vol の幅は約13.8〜40.4と粗く、59の疎な層だけを表示します。根や区間を作れない層は除外します。
右図は左と同一市場の ATM call の価格残差です。境界幅と価格残差は異なる量です。""")
)

cells.append(
    code(r"""shout_figures["shout_boundary"].show()""")
)

cells.append(
    md(r"""#### 4.2.5 欧州・ルックバックとの比較条件

同じ GBM、市場係数、満期、行使価格、非負の call 給付を比較します。シャウトしない選択が欧州 call を保証し、
新規極値 $M_0=S_0$ を含む連続観測の fixed-strike lookback は、任意の一度のシャウト時と満期の価格を含みます。
したがって連続時間の契約では

$$C_{\rm European}\le C_{\rm Shout}\le C_{\rm fixed\ lookback}.$$

有限木と解析式の異なる近似を混ぜる場合には残差を含めて検査します。履歴付き極値、異なる観測日、異なる市場条件を混ぜた一般的なプレミアム主張ではありません。
下図は7市場の call、$K=100,S_0=80,100,125$。価格42行は call/put 各21行です。
lookback 上下比較の実測範囲は **36行・6市場**。$r=q$ の shout は対応していますが、既存 lookback API は未対応なので
その棒は **欠測であり0ではありません**。独立二方式の価格比較は ATM の14行のみです。
put の21価格は原典外の拡張として独立に価格付けした検査です。欧州の $S/K$・$r/q$ 交換対称性は流用せず、原著の call 教材の範囲には数えません。
lookback は事後の全期間最高値を選べますが、shout は将来最高値を知らず一回決めるため安くなります。
比較可能な ATM 6市場での上乗せ比 $(C_{\rm Shout}-C_{\rm European})/(C_{\rm lookback}-C_{\rm European})$ は約20〜31%という実測値で、普遍則ではありません。""")
)

cells.append(
    code(r"""shout_figures["shout_comparison"].show()""")
)

cells.append(
    md(r"""#### 4.2.6 適用域・限界と理解の確認

$S,K,T,\sigma>0$、有限の一定係数 $r,q$、有効な CRR 確率が前提です。
価格・給付・現金脚の単位は通貨、$T,u$ は年、$r,q$ は連続複利年率、$\sigma$ は年率ボラティリティです。不正な入力は明示的に拒否します。
現金配当、時変ボラティリティ、契約固有の離散判断カレンダー、$T=0$、$\sigma=0$、全パラメータ領域の安定性は今回の受入対象外です。
図は保存済み JSON を読み、教材生成時に高価な価格探索は実行しません。

1. K=50、60でシャウト後、満期40と75で受け取る額は？
2. $S<K$ で現金脚の符号を正に直してよいですか？
3. シャウトの価値を即時行使価値 $S-K$ と比較するだけで十分ですか？
4. CRR 上下節点の区間内に独立境界がないとき、連続境界の誤りと断定できますか？
5. $r=q$ の図に lookback 棒がないのは価格が0だからですか？

**解答の要点**：1. 10と25。2. いいえ、契約を変えます。3. いいえ、割引現金と ATM call の和を継続価値と比較します。
4. いいえ、離散判断と疎な格子の区間は連続境界の保証ではありません。5. いいえ、既存 API 未対応による欠測です。""")
)

# Cell 09: asian lesson
cells.append(
    md(r"""### 4.3 アジアン・オプション（§26.13）

#### 4.3.1 三つの契約と観測の規約

平均価格型は満期スポットではなく**経路平均** $A$ で決済します。call の給付は $\max(A-K,0)$、
put は $\max(K-A,0)$。**平均行使型**は逆に、満期値を平均と比べて $\max(S_T-A,0)$、$\max(A-S_T,0)$ を払います。

平均をどう取るかは契約条項です。本書では観測日を $t_i=iT/m$ とし、**今日は観測日に入れず、満期は入れます**。
この規約でのみ原著の 12/52/250 観測の印刷値が再現します。連続平均は $m\to\infty$ の理想化です。""")
)

cells.append(
    code(r"""from hullkit._asian_lesson import _figures as asian_lesson_figures

asian_figures = asian_lesson_figures()
asian_figures["asian_payoff"].show()""")
)

cells.append(
    md(r"""#### 4.3.2 モーメント整合と Example 26.3

算術平均の分布に閉形式はありませんが、**モーメントは厳密に書けます**。$F_u=S_0e^{(r-q)u}$ として

$$M_1=\frac1m\sum_i F_{t_i},\qquad M_2=\frac1{m^2}\sum_i\sum_j F_{t_i}F_{t_j}e^{\sigma^2\min(t_i,t_j)}.$$

Turnbull-Wakeman は「平均は対数正規」と仮定し、この2つを合わせて Black モデル（式18.7・18.8）に入れます。
フォワードは $F_0=M_1$、ボラティリティは $\sigma_A^2=\ln(M_2/M_1^2)/T$ です（式26.3・26.4）。

原著 Example 26.3 は $S_0=K=50$、$r=10\%$、$q=0$、$\sigma=40\%$、$T=1$ 年。
連続平均で $M_1=52.59$、$M_2=2{,}922.76$、$\sigma_A=23.54\%$、価格 **5.62** です。

連続平均の印刷式は $r-q$ で割る形をしていますが、これは**可除特異点**です。
$r=q$ で価格が消えるわけではなく、印刷式にそのまま代入できないだけで、極限は有限です。
`asian_moments` は連続平均でもこの極限を計算するので、$r=q$ でも値を返します
（$S=100$、$r=q=3\%$、$\sigma=30\%$、$T=2$ で $M_1=100$、$M_2=10{,}628.00$、ATM call は $9.2488$）。
離散版はそもそも割り算を含まないので、観測日を渡せば同じ式がそのまま使えます。""")
)

cells.append(
    code(r"""EX = dict(S=50.0, K=50.0, r=0.10, q=0.0, sigma=0.40, T=1.0)
m1, m2 = exotics.asian_moments(EX["S"], EX["r"], EX["sigma"], EX["T"], q=EX["q"])
sigma_a = math.sqrt(math.log(m2 / m1**2) / EX["T"])
price = exotics.asian_average_price(EX["S"], EX["K"], EX["r"], EX["sigma"], EX["T"], q=EX["q"])
print(f"M1 = {m1:.2f}（原著 52.59）  M2 = {m2:.2f}（原著 2,922.76）")
print(f"整合ボラ = {sigma_a * 100:.2f}%（原著 23.54%）  価格 = {price:.4f}（原著 5.62）")

put = exotics.asian_average_price(EX["S"], EX["K"], EX["r"], EX["sigma"], EX["T"],
                                  q=EX["q"], kind="put")
parity = math.exp(-EX["r"] * EX["T"]) * (m1 - EX["K"])
print(f"put = {put:.4f}、パリティ残差 C-P-e^(-rT)(M1-K) = {price - put - parity:.2e}"
      "（近似の良し悪しによらず厳密に0）")""")
)

cells.append(
    md(r"""#### 4.3.3 平均は対数正規ではない

モーメント整合は分布を2次までしか合わせません。平均と分散は一致しますが、**形は一致しません**。
下図は算術平均の実測分布に、当てはめた対数正規を重ねたものです。
実測の歪度は当てはめた対数正規より**大きく**、右裾が厚いままです。このズレが価格の誤差になります。""")
)

cells.append(
    code(r"""asian_figures["asian_distribution"].show()""")
)

cells.append(
    md(r"""#### 4.3.4 観測数と価格

観測を増やすと平均のばらつきが減ります。Example 26.3 のような ATM コールでは価格が下がり、
原著は 12/52/250 観測で **6.00 / 5.70 / 5.63** を示します。
下のコードは同じ規約で同じ数字を出し、図は独立参照価格（制御変量モンテカルロ）と並べます。

ただし**これは一般則ではありません**。平均の期待値 $M_1$ も観測規約とキャリーで動くので、
負金利・$S/K=1.25$ のコールでは 12→250 観測で参照価格が 23.7263→23.8378 と上がります。
厳密な**幾何平均**の価格は、幾何平均 $\le$ 算術平均から**コールでは下界**になります。
プットでは不等号が逆向きで上界です（正キャリー・52観測・ATM プットで 3.9204 対 3.7884）。""")
)

cells.append(
    code(r"""for m in (12, 52, 250):
    times = [(i + 1) * EX["T"] / m for i in range(m)]
    value = exotics.asian_average_price(EX["S"], EX["K"], EX["r"], EX["sigma"], EX["T"],
                                        q=EX["q"], times=times)
    print(f"観測 {m:3d} 回: {value:.4f}")
print(f"連続平均      : {price:.4f}")

asian_figures["asian_observations"].show()""")
)

cells.append(
    md(r"""#### 4.3.5 既発契約：$K^*$ への読み替え

平均期間の一部がすでに過ぎた契約も同じ道具で扱えます。観測済み期間を $t_1$、その平均を $\bar S$、
残りを $t_2$ とすると、給付は

$$\max\!\left(\frac{t_1\bar S+t_2 A}{t_1+t_2}-K,\;0\right)=\frac{t_2}{t_1+t_2}\max(A-K^*,0),
\qquad K^*=\frac{t_1+t_2}{t_2}K-\frac{t_1}{t_2}\bar S$$

となり、**新規発行の契約を $K^*$ で評価して $t_2/(t_1+t_2)$ 倍する**だけです。これは近似ではなく給付の恒等式です。
$K^*<0$ なら call は必ず行使されるので、オプションではなくフォワードとして評価します（put は無価値）。

下の表は **Example 26.3 の既発版**です：$S_0=K=50$、$r=10\%$、$q=0$、$\sigma=40\%$ のまま、
平均期間 1 年のうち $t_1=0.6$ 年が終わり $t_2=0.4$ 年が残っている状況とします。
観測済み平均 $\bar S$ を 40／50／60／90 と変えると $K^*=125-1.5\bar S$ なので、$\bar S=90$ で $K^*=-10<0$、
つまり確実に行使される側へ移ります。同じ条件の数値を独立参照にも保存し、実画面で突き合わせています。""")
)

cells.append(
    code(r"""rows_seasoned = []
for observed in (40.0, 50.0, 60.0, 90.0):   # 独立参照と同じ条件（Example 26.3 の既発版）
    elapsed, remaining = 0.6, 0.4
    weight = remaining / (elapsed + remaining)
    shifted = EX["K"] / weight - observed * elapsed / remaining
    value = exotics.asian_seasoned_average_price(EX["S"], EX["K"], EX["r"], EX["sigma"],
                                                 elapsed, remaining, observed, q=EX["q"])
    rows_seasoned.append({"観測済み平均 S̄": observed, "K*": round(shifted, 3),
                          "確実に行使": shifted <= 0.0, "call 価格": round(value, 4)})
display(pd.DataFrame(rows_seasoned))""")
)

cells.append(
    md(r"""#### 4.3.6 平均行使型・適用域・理解の確認

平均行使型は「平均を渡して満期値を受け取る」交換オプションとして評価できます（Margrabe、式26.5）。
ただし平均を対数正規とみなす近似に加え、**対数の共分散をどう置くか**という選択が入ります。
ここでは幾何平均に対しては厳密な $\mathrm{Cov}(\ln A,\ln S_T)=\sigma^2\overline{t}$ を使っています。

**適用域**：モーメント整合は $\sigma\sqrt T$ が小さいほど正確です。下図のとおり、
低ボラ・短期では誤差 0.1% 未満ですが、$\sigma=70\%$・5年では **+10% を超えます**。
誤差は片側ではありません。実測は 144 行（観測 2/12/52/250、$S/K=0.8/1.0/1.25$）で、
相対誤差を意味のある形で書けるのは参照価格が 0.5 を超える **119 行**です。

| 実測 | 条件 | 相対誤差 |
|---|---|---:|
| 119行の最大の高値 | 高ボラ・長期（σ=70%, T=5年）、put、$S/K=1.25$、観測250 | **+23.35%** |
| 119行の最大の安値 | 配当>金利（σ=25%, T=1.5年）、call、$S/K=0.80$、観測12 | **−6.85%** |
| 原著 Example 26.3（連続平均） | σ=40%, T=1年、ATM call | +0.99%（5.6168 対 5.5618） |
| 参照価格 0.5 以下の17行 | 負金利（σ=18%, T=0.75年）、観測250 | **+20.44%**（put, $S/K$=1.25）／**−18.29%**（call, $S/K$=0.8） |

安い行を落とすと誤差は小さく見えます。上の 119 行の範囲を「全行の範囲」と読み替えないでください
（残り 17 行は相対誤差がむしろ大きく、8 行は参照価格が 0 で比が定義できません）。

**符号はマネーネスの一般則になりません。** 同じ $S/K$ でも市場と契約で向きが変わります
（例：ゼロキャリー・observations 52・call・$S/K=0.8$ で −2.89%、
高ボラ長期・同じ $S/K$ の call では +12.31%）。図の×印は、差が標準誤差の4倍未満で
符号を確定できない点です。実務で使うなら、この表の範囲を条件として添えてください。

**理解の確認**

1. 同じ $K$ のバニラと平均価格型はどちらが高いか。その理由を平均の分散で説明できるか。
2. 観測日を「今日を含む」に変えると $M_1$ と価格はどう動くか。原著の印刷値は再現するか。
3. $K^*<0$ の契約をオプションとして評価すると何がまずいか。
4. 誤差が +10% になる市場で、この近似を使ってよいと言えるか。何を添えれば言えるか。""")
)

cells.append(
    code(r"""asian_figures["asian_error"].show()

# 後段のチェックで使う連続平均コール（原著の主題）
a_tw = exotics.asian_call_turnbull_wakeman(S_B, K_B, R_B, SIG_B, T_B)
print(f"合成市場の Turnbull-Wakeman アジアン = {a_tw:.4f}（バニラ ATM コール {van:.4f} より安い）")""")
)

# Cell 11: exchange options (section 26.14)
cells.append(
    md(r"""### 4.4 交換オプション（§26.14、GE pp.627–628）

#### 4.4.1 行使価格が資産である契約

満期 $T$ に価値 $U_T$ の資産を渡して価値 $V_T$ の資産を受け取る権利の給付は

$$\max(V_T - U_T,\ 0).$$

普通のオプションとの違いは**行使価格が固定額でなく、満期に確定する別の資産の価値**である点です。
通貨の交換（円建て資産とドル建て資産）、株式を対価とする公開買付、
最良の投資先を選べる契約などがこの形になります。

$U,V$ はともに相関 $\rho$ の幾何ブラウン運動とし、ボラティリティを $\sigma_U,\sigma_V$、
連続配当利回りを $q_U,q_V$ とします。単位は価格が通貨、$T$ が年、利回りとボラは年率連続です。""")
)

cells.append(
    code(r"""from hullkit._exchange_lesson import _figures as exchange_lesson_figures

exchange_figures = exchange_lesson_figures()
exchange_figures["exchange_payoff"].show()""")
)

cells.append(
    md(r"""#### 4.4.2 Margrabe の式と $\hat\sigma$

価格は式 26.5 で与えられます。

$$
V_0e^{-q_VT}N(d_1)-U_0e^{-q_UT}N(d_2),\qquad
d_1=\frac{\ln(V_0/U_0)+(q_U-q_V+\hat\sigma^2/2)T}{\hat\sigma\sqrt T},\qquad
d_2=d_1-\hat\sigma\sqrt T,
$$

$$
\hat\sigma=\sqrt{\sigma_U^2+\sigma_V^2-2\rho\sigma_U\sigma_V}.
$$

$\hat\sigma$ は**比 $V/U$ のボラティリティ**です。2つのボラと相関は、この1つの量を通じてしか価格に入りません。
$\rho$ が高いほど2資産が同じ方向に動き、比のばらつきが減って交換の価値は下がります。
$\rho\to1$ かつ $\sigma_U=\sigma_V$ では $\hat\sigma\to0$ となり、価格は
$\max(V_0e^{-q_VT}-U_0e^{-q_UT},0)$ すなわち**割引フォワードの差**に収束します。

$q_U,q_V$ は $d_1$ では差 $q_U-q_V$ としてのみ効き、係数では各資産の割引に効きます。

交差項 $-2\rho\sigma_U\sigma_V$ を落とす誤りは、相関のある行では必ず検出されます
（独立参照との比較で、$\rho\neq0$ の 21 行すべてが拒否されました）。""")
)

cells.append(
    code(r"""exchange_figures["exchange_correlation"].show()""")
)

cells.append(
    md(r"""#### 4.4.3 なぜ $r$ に依存しないのか

式 26.5 にリスクフリー金利 $r$ は現れません。理由は、$r$ が上がると
リスク中立測度での**2資産の期待成長率も、満期給付の割引率も同じだけ上がり、打ち消し合う**ためです。
形式的には $U$ をニュメレールに取ると $r$ が消えます。

これは「$r$ を入れ忘れている」のではなく、契約の性質です。
下図では、式 26.5 を一切使わない求積による独立参照価格を $r\in[-5\%, 12\%]$ で計算しています
（24 行 × 3 レートの測定で最大差は 1.8×10⁻¹⁴、つまり浮動小数の丸めだけです）。

比較のため、同じ $\hat\sigma$ を使いながら**行使価格を今日の $U_0$ に固定した普通のコール**として
読んだ場合も重ねています。こちらは $r$ とともに動きます。差を生むのは
「行使価格が満期に確定する資産の価値である」という一点です。""")
)

cells.append(
    code(r"""exchange_figures["exchange_rate"].show()

# 独立参照（求積）と式26.5、そして V/U への読み替えを同じ条件で並べる
rows_exchange = []
for rho in (-0.5, 0.0, 0.5, 0.9):
    sigma_hat = exotics.exchange_spread_volatility(0.2, 0.2, rho)
    price = exotics.exchange_option(100.0, 100.0, 0.2, 0.2, rho, 1.0)
    restated = 100.0 * bsm.call_price(1.0, 1.0, 0.0, sigma_hat, 1.0, q=0.0)
    rows_exchange.append({"相関ρ": rho, "σ̂": round(sigma_hat, 4),
                          "交換オプション（26.5）": round(price, 4),
                          "V/U への読み替え": round(restated, 4),
                          "差": f"{restated - price:.2e}"})
display(pd.DataFrame(rows_exchange))""")
)

cells.append(
    md(r"""#### 4.4.4 $V/U$ への読み替え

原典は同じ価格を別の言葉で書き直します。この契約は

> **$V/U$ を原資産、行使価格 1.0、リスクフリー金利 $q_U$、配当利回り $q_V$ とするコール $U_0$ 個**

と等価です（式 17.4 と比べてください）。上の表の最終列がこの読み替えで、
式 26.5 と $10^{-14}$ の桁で一致します。

この読み替えには2つの使い道があります。第一に、$\hat\sigma$ が比のボラだという意味が見えます。
第二に、**米国型の評価経路がそのまま出てきます**。""")
)

cells.append(
    md(r"""#### 4.4.5 better-of／worse-of と米国型

$\max$ と $\min$ は恒等式で交換オプションに分解できます。

$$\max(U_T, V_T) = U_T + \max(V_T - U_T, 0), \qquad \min(U_T, V_T) = V_T - \max(V_T - U_T, 0)$$

したがって価値は「片方の資産を配当利回りぶん割引した値 $\pm$ 交換オプション」です。
足すと $\max+\min=U+V$ になるので、2つの値が同時にずれることはありません
（独立に価格付けした参照との残差は $8.5\times10^{-14}$）。

**米国型**（Rubinstein）は上の読み替えから、$V/U$ 上の米国型コール $U_0$ 個として二項木で評価できます。
配当のない資産に対するコールは早期行使されないので、**$q_V=0$ なら米国型は欧州型に一致します**。
受け取る資産に配当（あるいは利回り）があるときにだけ早期行使に価値が出ます。

木は有限格子なので、欧州型の閉形式との差には早期行使と離散化が混ざります。
下図は**同じ格子で行使判定だけを外した価格**と比べることで両者を分離しています。
$q_V=0$ の市場では早期行使ぶんが $1.2\times10^{-13}$、残るのは格子の $2.7\times10^{-3}$ だけです。""")
)

cells.append(
    code(r"""exchange_figures["exchange_american"].show()

rows_american = []
for name, q_v in (("配当なし q_V=0", 0.0), ("受取側に配当 q_V=6%", 0.06)):
    for ratio in (1.0, 1.25):
        kwargs = dict(U0=100.0, V0=100.0 * ratio, sigma_u=0.25, sigma_v=0.25,
                      rho=0.5, T=1.5, q_u=0.0, q_v=q_v)
        european = exotics.exchange_option(**kwargs)
        american = exotics.exchange_option_american(**kwargs)
        rows_american.append({"市場": name, "V₀/U₀": ratio,
                              "欧州型": round(european, 4), "米国型（木）": round(american, 4),
                              "早期行使の上乗せ": f"{american - european:+.4f}"})
display(pd.DataFrame(rows_american))

# better-of / worse-of は分解の恒等式そのもの
bw = dict(U0=100.0, V0=110.0, sigma_u=0.25, sigma_v=0.25, rho=0.5, T=1.5, q_u=0.0, q_v=0.06)
better, worse = exotics.better_of_two_assets(**bw), exotics.worse_of_two_assets(**bw)
forwards = 100.0 * math.exp(-0.0 * 1.5) + 110.0 * math.exp(-0.06 * 1.5)
print(f"better-of {better:.4f} + worse-of {worse:.4f} = {better + worse:.4f}")
print(f"割引フォワードの和                     = {forwards:.4f}"
      f"（差 {better + worse - forwards:.2e}）")""")
)

cells.append(
    md(r"""#### 4.4.6 適用域・限界と理解の確認

この節の実装と数値は、**定数の $\sigma_U,\sigma_V,\rho,q_U,q_V$ をもつ2本の相関 GBM**という仮定の上にあります。
確率的ボラティリティ、ジャンプ、時間変動する相関、現金配当は対象外です。
米国型は有限の CRR 木で、残差は格子効果であって誤差上界ではありません。
$T=0$、$\hat\sigma=0$ ちょうど、$\rho=\pm1$ ちょうどは端点として扱い、$\hat\sigma\le0$ では
割引フォワードの差を返します（木は立てられないので拒否します）。

**§26.14 には例題がなく、印刷された数値もありません。** 本冊の 7.965567 は原典の値ではなく、
本リポジトリが独立参照（求積2経路とモンテカルロ）で確かめた自前の固定値です。

**理解の確認**

1. $\sigma_U=\sigma_V=30\%$、$\rho=1$ のとき価格はいくらか。式を使わずに答えられるか。
2. $r$ を 2% から 10% に上げると交換オプションの価格はどう動くか。理由を1文で。
3. worse-of を「$V$ を買って交換オプションを売る」と読むと、売った側のリスクは何か。
4. 受け取る資産が配当利回り 6% の株価指数のとき、米国型と欧州型のどちらを買うべきか。""")
)

# Cell 11b: basket / rainbow lesson (section 26.15)
cells.append(
    md(r"""### 4.5 レインボーとバスケット（§26.15、GE pp.628–629）

2つ以上のリスク資産に依存する契約をレインボー・オプションと呼びます。交換、better-of、
worse-of もその仲間です。CBOT の T-bond 先物でショート側が受渡銘柄を選ぶ権利は、
**レインボーの文脈を示す例**です。印刷されたバスケット価格例ではありません。
§26.15 にはバスケットの数値例題がなく、以下は本リポジトリの合成市場です。

#### 4.5.1 保有量を先に足し、最後に行使する

満期のポートフォリオ価値と欧州型給付は

$$B_T=\sum_i w_iS_i(T),\qquad
C_T=(B_T-K)^+,\quad P_T=(K-B_T)^+.$$

$w_i$ は非負・単位なしの保有量で、少なくとも1つを正とします。合計1の比率である必要はありません。
資産価格・$K$・$B_T$・給付は同じ通貨単位、$T$ は年、$r,q_i$ は連続複利年率、
$\sigma_i$ は年率ボラティリティです。$w=(0.6,0.5)$、満期価格 $(90,60)$ なら
$B_T=84$、コールは0、プットは16。第2資産の寄与30は正なので、**ゼロ給付とゼロ保有量は別**です。
図は満期給付であって現在価値ではありません。""")
)
cells.append(
    code(r"""from hullkit._basket_lesson import _figures as basket_lesson_figures

basket_figures = basket_lesson_figures()
basket_figures["basket_payoff"].show()""")
)
cells.append(
    md(r"""#### 4.5.2 厳密な2モーメントと近似 Black 価格

定数パラメータの相関付きリスク中立 GBM を仮定します。

$$\frac{dS_i}{S_i}=(r-q_i)dt+\sigma_i dW_i,\qquad
dW_i\,dW_j=\rho_{ij}dt.$$

保有量を含めたフォワード寄与を $F_i=w_iS_i(0)e^{(r-q_i)T}$ とすれば、次の期待値は**厳密**です。
$M_2$ の単位は通貨の二乗です。

$$M_1=E[B_T]=\sum_iF_i,$$
$$M_2=E[B_T^2]=\sum_i\sum_jF_iF_j e^{\rho_{ij}\sigma_i\sigma_jT}.$$

一方、和 $B_T$ は一般に対数正規ではありません。最初の2モーメントだけを一致させた
対数正規代理分布に Black の式を適用する価格は**近似**です（Hull 式26.3・26.4の考え方）。

$$v=\log(M_2/M_1^2),\quad\hat\sigma=\sqrt{v/T},$$
$$d_1=\frac{\log(M_1/K)}{\sqrt v}+\frac{\sqrt v}{2},\quad d_2=d_1-\sqrt v.$$
$$C_{\rm MM}=e^{-rT}[M_1N(d_1)-KN(d_2)],$$
$$P_{\rm MM}=e^{-rT}[KN(-d_2)-M_1N(-d_1)].$$

$v=0$ なら割引した確定給付を返します。1つの非ゼロ保有資産、または完全相関・同じボラの
比例資産ではバスケット自身が対数正規になり、厳密な BSM アンカーに帰着します。
一般の場合でも put-call parity は $C-P=e^{-rT}(M_1-K)$ を満たします。

**自前の計算例。** $S=(100,80)$、$w=(0.6,0.5)$、$\sigma=(0.2,0.3)$、
$q=(0.01,0.025)$、$\rho=0.35$、$r=0.03$、$T=1$、$K=100$。
以下は高速なモーメント計算と近似価格だけを実行します。""")
)
cells.append(
    code(r"""basket_inputs = dict(
    spots=[100.0, 80.0], weights=[0.6, 0.5], rate=0.03,
    dividends=[0.01, 0.025], volatilities=[0.2, 0.3],
    correlations=[[1.0, 0.35], [0.35, 1.0]], expiry=1.0,
)
basket_m1, basket_m2 = exotics.basket_moments(**basket_inputs)
basket_sigma = math.sqrt(math.log(basket_m2 / basket_m1**2))
basket_call = exotics.basket_option_price(**basket_inputs, strike=100.0)
basket_put = exotics.basket_option_price(**basket_inputs, strike=100.0, kind="put")
print(f"M1 = {basket_m1:.6f}; M2 = {basket_m2:.6f};")
print(f"matched sigma = {basket_sigma:.6f}")
print(f"approx call = {basket_call:.6f}; approx put = {basket_put:.6f}")
print(f"call - put = {basket_call - basket_put:.6f};")
basket_parity = math.exp(-0.03) * (basket_m1 - 100)
print(f"discounted forward spread = {basket_parity:.6f}")""")
)
cells.append(
    md(r"""#### 4.5.3 相関は平均を動かさず交差項を動かす

同じ $S,w,r,q,\sigma,T$ を固定すると、$M_1$ は $\rho$ に依存しません。2資産の
$M_2$ に入る交差項は $2F_1F_2e^{\rho\sigma_1\sigma_2T}$ で、交差**共分散**の寄与は

$$2\operatorname{Cov}(w_1S_1(T),w_2S_2(T))
=2F_1F_2\left(e^{\rho\sigma_1\sigma_2T}-1\right).$$

図の3市場は $\rho=-0.65,0.35,0.90$ だけを変更しています。非負保有量なので相関が上がると
交差寄与、バスケット分散、マッチした $\hat\sigma$ が上がります。左軸は通貨の二乗、
右軸は年率ボラ（%）です。交換オプションでは価格を決めるのが**比**のばらつきでしたが、
ここでは**和**のばらつきを測る点に注意してください。""")
)
cells.append(code(r"""basket_figures["basket_correlation"].show()"""))
cells.append(
    md(r"""#### 4.5.4 独立参照で近似を測る

2資産は第1資産の正規因子で条件付け、第2資産の対数正規給付を解析的に平均し、
残る1次元の積分を数値求積した価格を参照します。$\rho=\pm1$ の特異点では
非退化の条件式を使わず、厳密なアンカーまたは正半定値行列を扱える MC を使います。

別経路として、相関 GBM の満期値を独立乱数で100万本生成しました。別の2万本の
pilot で第1モーメント制御変量の係数を推定し、本標本の調整済み給付から標準誤差 SE を求めます。
図の誤差棒は **MC 推定値 ±4SE** で、モデル誤差の上限ではありません。
3資産には MC 参照を使います。乱数 seed・本数・求積設定は保存記録に固定されています。

条件付き積分の有限区間に対する QUADPACK 推定誤差と、別計算した裾の上界は別物です。
保存格子の最大値はそれぞれ約 $3.0\times10^{-10}$ と $4.0\times10^{-31}$ でした。
MC と決定論的参照を比較できる54行はすべて4SE内（最大2.405SE）。
図・Book・ポータルは保存データを読み、ビルド時に求積や MC を再実行しません。""")
)
cells.append(code(r"""basket_figures["basket_comparison"].show()"""))
cells.append(
    md(r"""#### 4.5.5 観測誤差と MC の不確実性を分ける

絶対相対誤差を $100\,|V_{\rm MM}-V_{\rm ref}|/|V_{\rm ref}|$（%）と定義します。
参照価格が0.5未満なら分母が小さすぎるので相対誤差の集計から除外します。
全72行のうち63行が対象で、最大絶対差は6.417395通貨単位、
最大絶対相対誤差は **66.8378%**。符号付き相対誤差の範囲は −1.9361% から +66.8378% でした。
これは合成市場格子の観測結果であり、普遍的な誤差上限ではありません。

**符号判定は参照の種類に依存します。** MC だけが参照なら $|gap|\le4SE$ の点を
符号未確定とし、過大・過小評価の向きを主張しません。$K=100$ の3資産・分散ケースは
call/put とも $|gap|=0.0144703 < 4SE=0.0183002$ です。
条件付き積分・解析参照は自身の数値誤差で符号を判定でき、**MC の誤差棒内でも符号が確定**
する場合があります。MC の SE を決定論的参照の誤差として扱わないでください。

図の棒は常に絶対値です。斜線が符号未確定、横マーカーが4SEの相対値を示します。
長期・高ボラでずれが大きい例を見せていますが、相関・保有量・配当・行使価格も分布を変えるため、
単一のボラ指標だけでは誤差の順位を決められません。""")
)
cells.append(code(r"""basket_figures["basket_error"].show()"""))
cells.append(
    md(r"""#### 4.5.6 適用範囲と理解の確認

定数パラメータ、欧州型、満期まで固定した非負保有量が対象です。相関行列は対称・対角1・
正半定値が必要で、価格・行使価格・満期は正、ボラは非負です。負の保有量ではバスケットが
負になり得るため、この対数正規近似は使えません。現金配当、時間変化するパラメータ、
途中リバランス、満期ゼロ、あらゆる入力範囲での数値安定性は今回の範囲外です。
重要な価格判断では保存例に近いというだけで誤差を保証せず、独立参照と比較します。

1. 保有量 $(0.6,0.5)$、満期価格 $(90,60)$、$K=100$ のとき、コールが0でも第2資産を保有しているのはなぜか。
2. $M_1,M_2$ が厳密でも Black 価格が近似に留まる理由を、分布の形から説明できるか。
3. 相関を上げても $M_1$ は不変なのに価格が動くのは、どの項が変わるからか。
4. 条件付き積分と近似の差が MC の4SE内にあるとき、符号未確定と即断してよいか。
5. put-call parity が通ることだけで、call と put の近似精度を保証できるか。
6. 参照価格が0.1のケースで相対誤差が大きく見えるとき、まず何を確認すべきか。

**回答の手掛かり：** 保有寄与と行使判定、2モーメントと全分布、$M_2$ の交差項、
参照ごとの誤差、両側に共通する近似誤差、小さな分母と通貨単位の絶対差を区別します。""")
)

# Cell 12: volatility and variance swaps (section 26.16)
cells.append(
    md(r"""### 4.6 ボラティリティ・スワップとバリアンス・スワップ（§26.16、GE pp.629–632）

ここまでのオプションは価格とボラティリティの両方に反応しました。§26.16 の2つのスワップは
**実現したボラティリティ（または分散）だけ**を受け渡す契約です。原典には Example 26.4（バリアンス）と
26.5（ボラティリティ）の数値例があり、以下では両方を再現してから、その前提を独立参照で測ります。

#### 4.6.1 実現ボラティリティと2つの契約

$n$ 個の日次観測 $S_1,\dots,S_n$ から、平均日次リターンを0とみなして

$$\bar\sigma=\sqrt{\frac{252}{n-2}\sum_{i=1}^{n-1}\left[\ln\frac{S_{i+1}}{S_i}\right]^2}$$

を実現ボラティリティとします（原典は $n-2$ の代わりに $n-1$ を使う場合もあると注記）。
分散率は $\bar V=\bar\sigma^2$ です。固定側を払う当事者の満期の受取は

$$\text{ボラティリティ・スワップ: } L_{\rm vol}(\bar\sigma-\sigma_K),\qquad
\text{バリアンス・スワップ: } L_{\rm var}(\bar V-V_K).$$

$L$ は想定元本（Hull の例では 100 万ドル単位）、$\sigma_K$ は年率の小数、$V_K$ は年率の分散です。
2つの想定元本は慣行として $L_{\rm var}=L_{\rm vol}/(2\sigma_K)$ で結びます。分散側の行使を
$V_K=\sigma_K^2$ とすると $\bar\sigma=\sigma_K$ での傾きが一致し、差は
$L_{\rm vol}(\bar\sigma-\sigma_K)^2/(2\sigma_K)\ge 0$（$L_{\rm vol}>0$ のとき）。
**ボラ・スワップは $\bar\sigma$ に線形、バリアンス・スワップは凸**です。""")
)
cells.append(
    code(r"""from hullkit import variance_swaps as vs
from hullkit._variance_swap_lesson import _figures as vs_figures

path = [100.0, 101.0, 99.0, 100.5, 102.0]
v_n2 = vs.realized_variance(path)
v_n1 = vs.realized_variance(path, denominator="n-1")
print(f"n=5 の実現分散（n−2）= {v_n2:.6f}")
print(f"n=5 の実現分散（n−1）= {v_n1:.6f}")
L_var = vs.variance_notional(100.0, 0.23)
print(f"L_vol=100, σ_K=23% → L_var = {L_var:.4f}")

varswap_figures = vs_figures()
varswap_figures["varswap_payoff"].show()""")
)
cells.append(
    md(r"""#### 4.6.2 静的複製：分散は OTM オプションの束で買える

連続なパスなら伊藤の公式から $\ln S_T-\ln S_0=\int_0^T dS/S-\tfrac12\int_0^T\sigma_t^2dt$。
つまり累積分散 $\bar VT$ は「$S$ を連続的に保有する取引」と「対数契約 $-2\ln(S_T/S_0)$」で作れます。
対数契約は満期給付なので、行使価格 $S^*$ を境にプットとコールの束で静的に複製でき、
リスク中立期待値は（Technical Note 22、原典の式26.6）

$$\hat E(\bar V)=\frac2T\ln\frac{F_0}{S^*}-\frac2T\left(\frac{F_0}{S^*}-1\right)
+\frac2T\int_0^{S^*}\frac{e^{rT}p(K)}{K^2}dK+\frac2T\int_{S^*}^\infty\frac{e^{rT}c(K)}{K^2}dK.$$

$F_0$ はフォワード、$c(K),p(K)$ は満期 $T$ の欧州オプション価格です。**どの $S^*$ でも同じ値**になり、
モデルの形は問いません（仮定は連続パスと連続観測）。価格の単位は通貨で、$e^{rT}p(K)\,dK/K^2$ は
無次元の累積分散、$2/T$ を掛けて年率の分散になります。

**独立参照での確認。** 本リポジトリの生成器（hullkit を import しない）で積分を数値求積しました。
一定ボラ25%では $S^*=0.8F_0$ から $1.25F_0$ の5通りすべてで $\sigma^2$ との差が $10^{-16}$ 未満。
Heston の3市場（2つは $\rho<0$ の歪んだスマイル、1つは $\rho=0$）では、Lewis 積分で求めたオプション価格からの式26.6が
閉形式 $\theta+(v_0-\theta)(1-e^{-\kappa T})/(\kappa T)$ と一致しました（差は最大 $1.5\times10^{-12}$）。
一定ボラでしか成り立たない式ではない、というのがここで確かめたことです。""")
)
cells.append(
    md(r"""#### 4.6.3 離散ストリップと Example 26.4

実際に取引される行使価格 $K_1<\dots<K_n$ しかないので、積分を和で置き換えます（式26.8）。

$$\int_0^{S^*}\frac{e^{rT}p(K)}{K^2}dK+\int_{S^*}^\infty\frac{e^{rT}c(K)}{K^2}dK
\approx\sum_{i=1}^n\frac{\Delta K_i}{K_i^2}e^{rT}Q(K_i).$$

$\Delta K_i=\tfrac12(K_{i+1}-K_{i-1})$（両端は隣との差）。$S^*$ は $F_0$ の下で最初の行使価格、
$Q(K_i)$ は $K_i<S^*$ ならプット、$K_i>S^*$ ならコール、$K_i=S^*$ なら両者の平均です。

**Example 26.4（原典の数値例）。** 3か月、指数1020、$r=4\%$、配当利回り1%、行使価格800〜1200（50刻み）の
インプライド・ボラ29%〜21%。$F_0=1027.68$、$S^*=1000$、和は0.008139、$\hat E(\bar V)=0.0621$。
0.045 を払い実現分散を受け取る元本1億ドルの契約は $100\times(0.0621-0.045)e^{-0.04\times0.25}=1.69$（百万ドル）。""")
)
cells.append(
    code(r"""S_EX, R_EX, Q_EX, T_EX = 1020.0, 0.04, 0.01, 0.25
ex_strikes = np.arange(800.0, 1201.0, 50.0)
ex_vols = np.array([29, 28, 27, 26, 25, 24, 23, 22, 21]) / 100
ex_ev = vs.fair_variance_from_implied_vols(
    S_EX, ex_strikes, ex_vols, R_EX, T_EX, Q_EX
)
ex_value = vs.variance_swap_value(ex_ev, 0.045, R_EX, T_EX, notional=100)
print(f"E(V) = {ex_ev:.6f}（原典 0.0621）; 価値 = {ex_value:.4f}（原典 1.69）")

varswap_figures["varswap_strip"].show()""")
)
cells.append(
    md(r"""離散化の誤差は2種類あります。**格子誤差**：$Q$ は $S^*$ でプットからコールへ切り替わる折れ目を持ち、
和はそれを2次精度でしか拾えないので、行使価格が十分広く並ぶとき $\Delta K$ を半分にすると誤差はほぼ1/4。
**翼の欠落**：端より外の安いオプションを落とすと、和は必ず小さくなります。次のセルは一定ボラで格子誤差を、
その次の図は Heston の歪んだスマイル（厳密 $\hat E(\bar V)=0.04$）で両方を測ったものです。
広い範囲では $\Delta K=10\to1.25$ で誤差が $3.39\times10^{-3}\to5.31\times10^{-5}$ と4分の1ずつ減り、
狭い範囲（70〜140）では $\Delta K=2.5$ から負に転じます。細かくしても翼の欠落は消えません。""")
)
cells.append(
    code(r"""# --- バリアンス・スワップ: OTM オプションのストリップで複製（Hull 式 26.6・26.8） ---
# E(V) = (2/T)ln(F0/S*) − (2/T)(F0/S* − 1) + (2/T) Σ ΔK_i/K_i² e^{rT} Q(K_i)
#   S* = F0 以下で最初の行使価格、Q は S* 未満でプット・超でコール・S* で両者の平均
from hullkit import variance_swaps

F0 = S_B * math.exp(R_B * T_B)
strikes_vs = np.arange(60.0, 145.0, 5.0)         # 狭いストリップ（翼が欠ける）
strikes_wide = np.arange(20.0, 402.5, 2.5)       # 翼まで張ったストリップ
fair_var = variance_swaps.fair_variance_from_implied_vols(S_B, strikes_vs, SIG_B, R_B, T_B)
fair_var_wide = variance_swaps.fair_variance_from_implied_vols(S_B, strikes_wide, SIG_B, R_B, T_B)
s_star_wide = variance_swaps.default_s_star(strikes_wide, F0)
# 格子バイアス: Q が S* でプット→コールに切り替わる折れ目を中点和が2次精度でしか拾えない
grid_bias = 2.5**2 * (2 * F0 - s_star_wide) / (6 * T_B * s_star_wide**3)
print(f"F0 = {F0:.4f}, S*（広いストリップ）= {s_star_wide}")
print(f"狭いストリップ 60–140（ΔK=5）  : E(V) = {fair_var:.6f}（翼の欠落で σ²={SIG_B**2:.4f} を下回る）")
print(f"広いストリップ 20–400（ΔK=2.5）: E(V) = {fair_var_wide:.6f}")
print(f"  σ² + 格子バイアス ΔK²(2F0−S*)/(6T S*³) = {SIG_B**2 + grid_bias:.6f}")
print(f"→ 公正ボラティリティ = {math.sqrt(fair_var_wide):.4%}（入力 σ={SIG_B:.0%}）")
print("VIX も同型（式 26.10 は ln を2次展開で打ち切った形）: OTM SPX オプションのストリップで30日先のバリアンスを測る")""")
)
cells.append(code(r"""varswap_figures["varswap_replication"].show()"""))
cells.append(
    md(r"""#### 4.6.4 ボラティリティ・スワップと Example 26.5

$\bar\sigma=\sqrt{\bar V}$ は凹関数なので $\hat E(\bar\sigma)<\sqrt{\hat E(\bar V)}$。平方根を $\hat E(\bar V)$ の周りで
2次まで展開すると（式26.9）

$$\hat E(\bar\sigma)\approx\sqrt{\hat E(\bar V)}\left\{1-\frac18\frac{\operatorname{var}(\bar V)}{\hat E(\bar V)^2}\right\}.$$

ボラ・スワップの価値は $L_{\rm vol}[\hat E(\bar\sigma)-\sigma_K]e^{-rT}$。**分散の分散**が必要になり、それが
満期1本のオプションの束だけからは追加の仮定なしに決まらない点が、バリアンス・スワップとの本質的な違いです。

**Example 26.5。** Example 26.4 の $\hat E(\bar V)=0.0621$、実現分散の標準偏差0.01（$\operatorname{var}=0.0001$）、
固定23%、元本1億ドル。$\hat E(\bar\sigma)=0.2484$、価値 $100\times(0.2484-0.23)e^{-0.01}=1.82$（百万ドル）。""")
)
cells.append(
    code(r"""ex_sigma = vs.expected_volatility(0.0621, 0.0001)
ex_naive = math.sqrt(0.0621)
ex_vol_value = vs.volatility_swap_value(
    ex_sigma, 0.23, R_EX, T_EX, notional=100
)
print(f"E(σ) = {ex_sigma:.6f}（原典 0.2484）; √E(V) = {ex_naive:.6f}")
print(f"価値 = {ex_vol_value:.4f}（原典 1.82、$ millions）")

varswap_figures["volswap_convexity"].show()""")
)
cells.append(
    md(r"""式26.9は近似です。図は連続観測の Heston 分散（$v_0=\theta=0.0621$、$\kappa=2$、$T=0.25$）で
$\hat E(\bar V)$ を固定し、分散過程のボラ $\xi$ だけを動かしました。厳密な $E(\sqrt{\bar V})$ は
CIR 過程のラプラス変換の積分、$\operatorname{var}(\bar V)$ は伊藤等長性から求め、
非心カイ二乗による厳密推移の MC（10万本）は3点とも4SE以内（最大1.08SE）でした。
$\xi=0.3$ では近似の誤差は $-1.9\times10^{-5}$ ですが、$\xi=1$ では $-4.6\times10^{-3}$（0.46%ポイント）に
広がります。誤差は小さい $\xi$ で $\xi^4$ に比例して増え（この格子の隣接点どうしの傾きは4.1〜4.7）、
この市場ではすべての $\xi$ で近似が厳密値を下回りました。向きは積分した分散の分布の歪みで決まり、
一般の性質ではありません。
凸性を無視した $\sqrt{\hat E(\bar V)}$ の誤差（$\xi=1$ で $+2.5\times10^{-2}$）よりはずっと小さい、というのが
式26.9の実用上の価値です。""")
)
cells.append(
    md(r"""#### 4.6.5 VIX 指数（式26.10）

式26.6の $\ln(F_0/S^*)$ を2次で打ち切ると、累積分散は

$$\hat E(\bar V)T=-\left(\frac{F_0}{S^*}-1\right)^2+2\sum_{i=1}^n\frac{\Delta K_i}{K_i^2}e^{rT}Q(K_i).$$

原典によれば 2004 年以降の VIX はこの式に基づき、30日の前後の満期で $\hat E(\bar V)T$ を計算して時間について補間し、
$365/30$ を掛けて平方根を取ります。これは原典の説明で、行使価格の選び方や分単位の満期など
CBOE の規則の細部はここでは扱いません。打ち切りによる差は
$2[\ln x-(x-1)+\tfrac12(x-1)^2]\approx\tfrac23(x-1)^3$（$x=F_0/S^*$）。Example 26.4 では
$1.38\times10^{-5}$ で、累積分散0.01553の約0.09%です。""")
)
cells.append(
    code(r"""ex_args = (S_EX, ex_strikes, R_EX, ex_vols, T_EX, Q_EX)
ex_calls, ex_puts = bsm.call_price(*ex_args), bsm.put_price(*ex_args)
ex_q = vs.otm_option_prices(ex_strikes, ex_calls, ex_puts, 1000.0)
ex_f0 = S_EX * math.exp((R_EX - Q_EX) * T_EX)
ex_cum = vs.vix_cumulative_variance(ex_strikes, ex_q, ex_f0, R_EX, T_EX)
print(f"式26.6: E(V)T = {ex_ev * 0.25:.7f}; 式26.10: {ex_cum:.7f}")
print(f"差 = {ex_ev * 0.25 - ex_cum:.2e}")
# 23日と37日の累積分散（一定ボラ20%なら補間しても20%に戻る）
t1, t2 = 23 / 365, 37 / 365
flat_vix = vs.vix_index(t1, 0.04 * t1, t2, 0.04 * t2)
print(f"一定ボラ20%の30日 VIX = {100 * flat_vix:.4f}")""")
)
cells.append(
    md(r"""累積分散は満期について線形とは限らないので、補間にも誤差があります。平均回帰する Heston 市場
（$v_0=0.09$、$\theta=0.04$、$\kappa=2$）で23日と37日から補間した30日ボラは29.312%、
閉形式の30日値は29.344%でした（差 −0.032%ポイント）。

#### 4.6.6 適用範囲と理解の確認

**前提。** 複製は連続パスを連続観測した分散を扱います（ジャンプがあると対数契約との関係が崩れ、
ここでの等式は保証されません）。実際の契約は日次の離散観測です。平均0の推定量で $n-1$ 個の
二乗リターンを $n-2$ で割ると、ドリフトが小さいとき期待値は $(n-1)/(n-2)$ 倍に膨らみます
（3か月 $n=64$、$\sigma=25\%$ で $0.063509$ 対 $\sigma^2=0.0625$、+1.6%）。行使価格の範囲と間隔、
ボラ・スワップでの $\operatorname{var}(\bar V)$ の推定も結果を左右します。上の誤差は保存した合成市場の測定で、
一般の上限ではありません。現金配当と CBOE 規則の細部は範囲外です。

1. $L_{\rm vol}=100$、$\sigma_K=23\%$ のとき、$L_{\rm var}$ はいくらで、$\bar\sigma=30\%$ での2つの給付はどれだけ違うか。
2. 式26.6の答えが $S^*$ に依存しないのはなぜか。$S^*$ を $F_0$ に取ると境界項はどうなるか。
3. 狭い行使価格の範囲で $\Delta K$ を細かくしても誤差が0に近づかないのはなぜか。
4. バリアンス・スワップはオプションの束で値付けできるのに、ボラ・スワップにはなぜ追加の仮定が要るのか。
5. 式26.9の近似が厳密値を下回ったのは、$\xi$ のどの範囲でどの程度か。それは一般的な性質といえるか。
6. 日次63リターンの実現分散を $n-2$ で割る契約と $n-1$ で割る契約では、公正な分散ストライクはどちらが高いか。

**回答の手掛かり：** 傾きをそろえる換算と凸性、対数契約の複製、翼の欠落と格子誤差、分散の分散、
合成市場での測定と一般の保証、推定量の分母を区別します。""")
)

# ===========================================================================
# Section 2: Ch.28 martingales and measures
# ===========================================================================

# Cell 14: numeraire md
cells.append(
    md(r"""## 5. マルチンゲールと測度（Ch.28）

**マルチンゲール** = ドリフトゼロの過程（$E[\theta_T] = \theta_0$）。
**同値マルチンゲール測度の定理**: トレーダブル証券 $g$（ニュメレール）を選ぶと、
任意の証券価格 $f$ について $f/g$ がマルチンゲールになる測度が存在し：

$$f_0 = g_0\,E_g\!\left[\frac{f_T}{g_T}\right] \quad \text{(28.15)}$$

ニュメレールの選び方で「便利な測度」が得られます：
マネーマーケット口座 → リスク中立測度、ゼロクーポン債 → フォワード測度。""")
)
cells.append(
    md(r"""> **核心** — 適切な測度の下で『割引価格はマルチンゲール』——これが価格理論の核。<br>
> **直感** — ニュメレールで割ると価格がドリフトを失う。だから割引期待値＝価格。<br>
> **実務** — あらゆる無裁定価格の土台。測度を選ぶ自由が計算を楽にする。

> **実務での出番 — ニュメレール変更——クオンツの『座標変換』**
>
> 同じ価格を、どの資産を基準(ニュメレール)に測るかは自由。リスク中立測度(マネーマーケット基準)で難しい期待値も、フォワード測度(債券基準)やスワップ測度に変えると一気に解ける。Black-76 がなぜ確率的金利下でも成り立つか、スワプションの Black 公式がなぜ正当か——すべて『便利な測度を選んだ』結果。クオンツの最重要テクニック。""")
)

# Cell 15: market price of risk md
cells.append(
    md(r"""## 6. 市場リスクの価格 λ（§28.1）

ある確率変数 $\theta$ に依存する**すべての**デリバティブで、無裁定なら

$$\frac{\mu - r}{\sigma} = \lambda \quad \text{(28.8)}$$

が共通に成立（$\lambda$ は $\theta, t$ のみに依存、商品によらない）。
$\lambda$ はシャープ比に相当。リスク中立測度は $\lambda$ を 0 に「移す」測度です。""")
)
cells.append(
    md(r"""> **核心** — λ＝リスク1単位あたりの超過リターン(シャープ比に相当)。<br>
> **直感** — リスク中立測度は λ を0に移す測度。実世界とリスク中立の橋渡し。<br>
> **実務** — 測度変換のドリフト補正の正体。実→Q の翻訳係数。""")
)

# Cell 16: market price of risk demo
cells.append(
    code(r"""# --- λ が2つのデリバティブで一致することの数値確認 ---
# 原資産 θ: dθ/θ = m dt + s dz。θに依存する2つのデリバティブ f1, f2 の (μ-r)/σ を比較
# BSM 世界では任意のオプションについて (μ_opt - r)/σ_opt = (μ_S - r)/σ_S = λ
S0_m, mu_S, sig_S, r_m = 100.0, 0.12, 0.20, 0.05
lam_underlying = (mu_S - r_m) / sig_S
# コールのリターン・ボラはデルタ弾性 Ω = (S/c)·Δ でスケール
for K_m, T_m in [(100.0, 0.5), (110.0, 1.0)]:
    c = bsm.call_price(S0_m, K_m, r_m, sig_S, T_m)
    delta = bsm.call_delta(S0_m, K_m, r_m, sig_S, T_m)
    omega = S0_m / c * delta  # 弾性
    sig_opt = omega * sig_S
    mu_opt = r_m + omega * (mu_S - r_m)  # CAPM 風
    lam_opt = (mu_opt - r_m) / sig_opt
    print(f"K={K_m}, T={T_m}: σ_opt={sig_opt:.3f}, (μ−r)/σ = {lam_opt:.4f}")
print(f"原資産の λ = (μ−r)/σ = {lam_underlying:.4f} ← すべて一致（無裁定）")""")
)

# Cell 17: risk-neutral & forward measure md
cells.append(
    md(r"""## 7. ニュメレールの選択（§28.4）

| ニュメレール $g$ | 測度 | 公式 |
|---|---|---|
| マネーマーケット口座 $e^{rt}$ | リスク中立 $\mathbb{Q}$ | $f_0 = \hat E[e^{-rT}f_T]$ |
| ゼロクーポン債 $P(t,T)$ | $T$-フォワード $\mathbb{Q}^T$ | $f_0 = P(0,T)E^T[f_T]$ |
| アニュイティ $A(t)$ | スワップ測度 | スワプション評価（→第11冊） |

**フォワード測度の効用**: $F(t,T) = E^T[S_T]$ — フォワード価格はフォワード測度下の
期待スポット。これが**確率的金利下でも Black-76 が成り立つ**理由です（第2冊の $q=r$ の正当化）。""")
)
cells.append(
    md(r"""> **核心** — 基準資産を賢く選ぶと、期待値が前方フォワードなどに化ける。<br>
> **直感** — フォワード測度では『フォワード価格＝期待スポット』が成り立つ。<br>
> **実務** — 確率的金利下の Black-76 の正当化(第2巻 q=r の根拠)。""")
)

# Cell 18: numeraire invariance demo
cells.append(
    code(r"""# --- ニュメレール不変性: 同じコールを3つの測度で独立評価 → MC 誤差内で一致 ---
S0_n, K_n, r_n, sig_n, T_n = 100.0, 100.0, 0.05, 0.25, 1.0
rng_n = np.random.default_rng(28)
n_paths = 400_000
# (a) リスク中立測度 Q（ニュメレール=マネーマーケット口座、ドリフト r）: c = E^Q[e^{-rT}(S_T-K)^+]（28.19）
z_q = rng_n.standard_normal(n_paths)
ST_q = S0_n * np.exp((r_n - 0.5 * sig_n**2) * T_n + sig_n * math.sqrt(T_n) * z_q)
price_q = math.exp(-r_n * T_n) * np.maximum(ST_q - K_n, 0.0).mean()
# (b) 株価ニュメレール（測度 S、ドリフト r+σ²）: c = S0 E^S[(S_T-K)^+ / S_T]
z_s = rng_n.standard_normal(n_paths)
ST_s = S0_n * np.exp((r_n + 0.5 * sig_n**2) * T_n + sig_n * math.sqrt(T_n) * z_s)
price_s = S0_n * (np.maximum(ST_s - K_n, 0.0) / ST_s).mean()
# (c) ゼロクーポン債ニュメレール P(t,T)（T-フォワード測度）: c = P(0,T) E^T[(F_T-K)^+]（28.20）
#     フォワード価格 F(t,T) = S/P(t,T) がドリフトゼロのマルチンゲール、F_T = S_T（28.21）
z_t = rng_n.standard_normal(n_paths)
P0T_n = math.exp(-r_n * T_n)
F0_n = S0_n / P0T_n
FT_t = F0_n * np.exp(-0.5 * sig_n**2 * T_n + sig_n * math.sqrt(T_n) * z_t)
payoff_t = np.maximum(FT_t - K_n, 0.0)
price_t = P0T_n * payoff_t.mean()
se_t = P0T_n * payoff_t.std(ddof=1) / math.sqrt(n_paths)
se_fwd_t = FT_t.std(ddof=1) / math.sqrt(n_paths)
bsm_n = bsm.call_price(S0_n, K_n, r_n, sig_n, T_n)
print(f"(a) リスク中立測度 Q の MC 価格       = {price_q:.4f}")
print(f"(b) 株価ニュメレールの MC 価格       = {price_s:.4f}（別測度・別サンプリング）")
print(f"(c) T-フォワード測度の MC 価格       = {price_t:.4f} ± {se_t:.4f}（SE、割引は期待値の外）")
print(f"BSM 解析値                           = {bsm_n:.4f}")
print(f"E^T[F_T] = {FT_t.mean():.4f} ／ F(0,T) = S0/P(0,T) = {F0_n:.4f}（フォワード＝T-フォワード測度での期待スポット）")
print("→ 異なる測度・異なるドリフトで独立にサンプリングしても同じ価格（測度変換の不変性）")
print("※ r が定数だと P(t,T) のボラはゼロなので Q と T-フォワード測度で S_T の分布は同じ。"
      "(a) と (c) が本質的に分かれるのは r が確率的なとき（割引 e^{-∫r} が期待値の内か外か）")""")
)

# Cell 19: Girsanov md + demo
cells.append(
    md(r"""## 8. ギルサノフの定理（§28.1）

測度変換は**ドリフトを変えるがボラティリティは保存**する：

$$dz^{\mathbb{Q}} = dz^{\mathbb{P}} + \lambda\,dt$$

実世界 $\mathbb{P}$（ドリフト $\mu$）からリスク中立 $\mathbb{Q}$（ドリフト $r$）へ移っても、
$\sigma$ は不変。これは第1冊で見た「二項ツリーで測度を変えても σ が変わらない」の
連続版です。下で同じ σ・異なるドリフトのパスを比較します。""")
)
cells.append(
    md(r"""> **核心** — 測度を変えるとドリフトは変わるが、ボラ σ は不変。<br>
> **直感** — 確率の重み付けを変えるだけ。経路の『揺れ幅』はそのまま。<br>
> **実務** — 実→リスク中立の変換の数学的保証。σ がモデル横断で測れる理由。""")
)

# Cell 20: Girsanov path demo
cells.append(
    code(r"""rng_g = np.random.default_rng(280)
z_common = rng_g.standard_normal((30, 252))
t_g = np.linspace(0.0, 1.0, 253)
dt_g = 1.0 / 252
fig6, (ax6a, ax6b) = plt.subplots(1, 2, figsize=(10.5, 4), sharey=True)
fig6.canvas.header_visible = False
for ax, mu_g, title in ((ax6a, 0.12, "実世界 P（μ=12%）"),
                        (ax6b, 0.05, "リスク中立 Q（μ=r=5%）")):
    lp = np.cumsum((mu_g - 0.5 * 0.2**2) * dt_g + 0.2 * math.sqrt(dt_g) * z_common, axis=1)
    paths_g = 100.0 * np.exp(np.column_stack([np.zeros(30), lp]))
    ax.plot(t_g, paths_g.T, lw=0.6, alpha=0.6)
    ax.plot(t_g, 100.0 * np.exp(mu_g * t_g), "k--", lw=2)
    ax.set_title(title)
    ax.set_xlabel("t")
ax6a.set_ylabel("S")
fig6.suptitle("同じ乱数・同じ σ=20%、ドリフトだけ違う（ギルサノフ）", fontsize=10)
display(fig6.canvas)
print("拡散の広がり（σ）は両測度で同一。期待成長率（点線）だけが異なる")""")
)

# Cell 21: swap measure pointer md
cells.append(
    md(r"""### スワップ測度へのポインタ（§28.4）

アニュイティ $A(t) = \sum (T_{i+1}-T_i)P(t,T_{i+1})$ をニュメレールにすると、
フォワード・スワップレート $s(t)$ がマルチンゲールになる「スワップ測度」が得られ、
**スワプションの Black 公式**が正当化されます。これは第11冊（Ch.29）で本格的に使います。""")
)

# ===========================================================================
# Section 3: verification / exercises / summary
# ===========================================================================

# Cell 22: assertion cell
cells.append(
    code(r"""# --- 検証（hullkit/tests/test_exotics.py にも同等の検証あり） ---
checks = []
checks.append(("バイナリ分解 = バニラ", aon - K_B * con, van, 1e-12))
checks.append(("バリア in+out = バニラ", cdi + cdo, van, 1e-12))
checks.append(("Margrabe 7.9656",
               exotics.exchange_option(100.0, 100.0, 0.2, 0.2, 0.5, 1.0), 7.965567, 1e-5))
checks.append(("gap call 13.1122",
               exotics.gap_call(100.0, 95.0, 100.0, 0.05, 0.20, 1.0), 13.112208, 1e-5))
checks.append(("分散スワップ複製 = σ² + 格子バイアス", fair_var_wide, SIG_B**2 + grid_bias, 1e-6))
checks.append(("アジアン < バニラ", float(a_tw < van), 1.0, 0.0))
checks.append(("ルックバック > ATM", float(lb > van), 1.0, 0.0))
checks.append(("ニュメレール不変（a≈b）", price_q, price_s, 3e-2))
checks.append(("ニュメレール不変（c: T-フォワード ≈ BSM, 4SE）", price_t, bsm_n, 4.0 * se_t))
checks.append(("T-フォワード測度で E[F_T] = F(0,T)（4SE）", float(FT_t.mean()), F0_n, 4.0 * se_fwd_t))
checks.append(("λ 一致（原資産 vs オプション）", lam_opt, lam_underlying, 1e-9))

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.6g} want={want:.6g}")
    assert ok, name
print("\n全チェック合格")""")
)

# Cell 23: exercises
cells.append(
    md(r"""## 9. 練習問題

**Q1.** ダウン・アンド・アウト・コール（H=80）の価格が 9、対応するバニラが 10。
ダウン・アンド・イン・コールの価格は？

<details><summary>解答</summary>

in + out = vanilla より、di = 10 − 9 = 1。
</details>

**Q2.** 平均価格アジアン・コールがバニラ・コールより安いのはなぜ？

<details><summary>解答</summary>

平均は経路を均すので実効ボラティリティが下がる（σ_avg < σ）。
オプション価値はボラに単調増加なので安くなる。
</details>

**Q3.** 交換オプション（Margrabe）が金利 r に依存しないのはなぜ？

<details><summary>解答</summary>

一方の資産をニュメレールに取ると、両資産の成長率上昇と割引率上昇が相殺する。
価格は相対ボラ σ̂=√(σ_U²+σ_V²−2ρσ_Uσ_V) だけで決まる。
</details>""")
)

# Cell 24: summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 |
|---|---|
| バイナリ | aon − K·con = バニラ。不連続ペイオフ |
| バリア | 8種類・連続式の全分岐。観測頻度/BGK、負のベガ、Parisian の滞在規約 |
| ルックバック | 経路最小で買える「後知恵」プレミアム |
| アジアン | 平均でボラ低下 → 安い。TW近似 or MC |
| Margrabe | 交換オプション。r 非依存、σ̂ だけで決まる |
| 測度 | f/g がマルチンゲール。ニュメレールで測度を選ぶ |
| λ | (μ−r)/σ は全商品共通。Q は λ=0 の測度 |
| ギルサノフ | 測度変換でドリフト変、σ 不変 |

**次へ**: `volumes/11_ir_derivatives_market`（Ch.29, 30 — Black モデルとスワプション）
**シリーズ**: `johnhull/ROADMAP.md` 参照""")
)

# Cell 25: closing md
cells.append(
    md(r"""---
*第10冊おわり。エキゾチックの閉形式と、その正当性を支える測度論を一巡しました。*""")
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exotics.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
