"""Generate the Laplace-transform textbook notebooks deterministically.

Run from anywhere with the package importable:

    PYTHONPATH=src python tools/build_notebooks.py

Each notebook follows the book's fixed shape (Big Picture -> Problem -> Intuition
-> Visualization -> Definition -> Computation -> Invariant -> Failure Mode ->
Application -> Exercises -> Advanced Notes) with Basic / Applied / Advanced
layers. Heavily implemented: 01, 02, 04, 05, 06. Lighter (real content + TODO):
00, 03, 07, 08. The generated .ipynb files are then executed in place so they
carry outputs (the book builds with execute_notebooks: off).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nbkit import code, md, write  # noqa: E402

NB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "notebooks")

FULL_LAYERS = [
    ("Basic", "1. Big Picture 〜 5. Definition"),
    ("Applied", "6. Computation 〜 9. Application"),
    ("Advanced", "10. Exercises / 11. Advanced Notes"),
]


def title(num_title: str, layers, intro: str):
    table = "| 層 | セクション |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in layers)
    return md(f"# {num_title}\n\n{table}\n\n> {intro}")


SETUP = code(
    r"""
# Shared setup: make laplace_book importable, fix seeds, inline + plotly rendering.
%matplotlib inline
import sys
from pathlib import Path

try:
    import laplace_book  # noqa: F401
except ModuleNotFoundError:
    for _base in (Path.cwd(), *Path.cwd().parents):
        if (_base / "src" / "laplace_book").is_dir():
            sys.path.insert(0, str(_base / "src"))
            break

import numpy as np
import matplotlib.pyplot as plt
import sympy as sp
from IPython.display import display

from laplace_book import transforms, systems, circuits, plotting, datasets, widgets
from laplace_book.transforms import t, s, L, Linv, numeric_laplace, partial_fractions

import plotly.io as pio
pio.renderers.default = "notebook_connected"

np.random.seed(0)
np.set_printoptions(precision=4, suppress=True)
sp.init_printing()
"""
)


def assemble(num_title, layers, intro, body):
    return [title(num_title, layers, intro), SETUP, *body]


# =========================================================================== #
# 00 — Overview
# =========================================================================== #
def nb00():
    body = [
        md(
            """
## 1. ラプラス変換とは何か

ラプラス変換は、**時間 $t$ の関数 $f(t)$ を、複素周波数 $s$ の関数 $F(s)$ に移す道具**です。

$$ F(s) = \\int_0^\\infty f(t)\\, e^{-st}\\, dt $$

ここで $s = \\sigma + i\\omega$ は **複素周波数**。$\\sigma$ は成長・減衰の速さ、$\\omega$ は振動の速さを表します。
つまりラプラス変換は、世の中の「成長・減衰・振動」をひとつの言葉でまとめて扱うための変換です。
"""
        ),
        md(
            """
## 2. なぜラプラス変換を学ぶのか

時間領域では難しい操作が、$s$ 領域では簡単な代数になります。これが最大の動機です。

| 時間領域 $t$ | $s$ 領域 |
|---|---|
| 微分 $\\frac{d}{dt}$ | $s$ の掛け算 |
| 畳み込み $f * g$ | 積 $F(s)G(s)$ |
| 微分方程式 (ODE) | 代数方程式 |
| 応答の形・安定性 | **極**(分母の根)の位置 |

「微分が掛け算になる」ので、微分方程式は **解く** ものから **整理する** ものに変わります。
"""
        ),
        md(
            """
## 3. 時間領域と s 領域(まず一枚の絵で)

本書で何度も出てくる中心的な対象は、**減衰しながら振動する波** $e^{\\sigma t}\\cos(\\omega t)$ と、
それに対応する **$s$ 平面上の点(極)** $\\sigma \\pm i\\omega$ の組です。下の図で両者を並べます。
"""
        ),
        code(
            r"""
tt = np.linspace(0, 12, 500)
plotting.plot_pole_and_response(sigma=-0.35, omega=3.0, t=tt)
plt.tight_layout()
"""
        ),
        md(
            """
左の点(極)の **横位置 $\\sigma$** が減衰の速さ、**縦位置 $\\omega$** が振動の速さに、そのまま対応しています。
この「$s$ 平面の点 ↔ 時間の波」の対応こそ、ラプラス変換の幾何的な核心です(01・06 章で深掘り)。
"""
        ),
        md(
            """
## 4. フーリエ変換との違い

- フーリエ変換は $s = i\\omega$(虚軸)だけを見る。つまり **純粋な振動** の世界。
- ラプラス変換は $s = \\sigma + i\\omega$ と **実部 $\\sigma$ を足した**。だから成長・減衰する信号も扱える。
- ラプラス変換は **片側**($t\\ge 0$)で定義し、**初期条件が自然に式へ入る**(02・04 章)。
- $\\sigma$ のおかげで積分が収束しやすい(**収束域 ROC**、02 章)。

一言でいえば、フーリエが「振動の分解」なら、ラプラスは「成長・減衰・振動をまとめた分解」です。
"""
        ),
        md(
            """
## 5. 接続先 と この教材の読み方

ODE・制御・電気回路・信号処理・確率の各分野が、すべて $s$ 領域でつながります。
各章は次の流れで進みます。

> 現象 → 直感 → 可視化 → 数式 → Python 実験 → 応用 → 発展

そして各章を **Basic(最低限)/ Applied(Python と応用)/ Advanced(証明・発展)** の3層で読めます。
急ぐときは Basic だけ追えば筋が通るように作っています。
"""
        ),
        md(
            """
## 6. 章構成

| Notebook | 内容 |
|---|---|
| `00_overview` | 全体像・なぜ学ぶか・$s$ 領域・読み方(本章) |
| `01_exponential_decay_complex_frequency` | 指数・成長/減衰/振動・複素指数・$s$ 平面の直感 |
| `02_definition_basic_properties` | 定義・収束域・線形性・微分/積分/シフト・初期値 |
| `03_inverse_laplace_partial_fractions` | 逆変換・変換表・部分分数(重根/複素極)・SymPy |
| `04_solving_odes_with_laplace` | ODE を代数に・1階/2階・減衰/強制振動・ステップ |
| `05_convolution_impulse_response_transfer_functions` | 畳み込み定理・インパルス応答・伝達関数・LTI |
| `06_poles_zeros_stability` | 極と零点・$s$ 平面・極と応答・安定性 |
| `07_control_systems_and_circuits` | RC/RLC・ステップ/インパルス応答・フィードバック・Bode |
| `08_applications_probability_signals_finance` | 確率の MGF・割引現在価値・待ち行列入口 |
"""
        ),
        md(
            """
## 7. Python 環境の準備

共通関数は `src/laplace_book/` にまとまっています(`transforms` / `systems` / `circuits` /
`plotting` / `widgets` / `datasets`)。上の setup セルがインポート済みです。変換表をのぞいてみましょう。
"""
        ),
        code(
            r"""
# The core transform table (forward pairs). Inverse direction is chapter 03.
transforms.transform_table_df()
"""
        ),
        md(
            """
各 Notebook は上から順に実行できます(乱数は seed 固定)。では 01 章へ。
"""
        ),
    ]
    layers = [("—", "全体像・接続・読み方(オリエンテーション)")]
    return assemble(
        "00. 全体像 — 時間を複素周波数の世界で代数にする",
        layers,
        "ラプラス変換を「変換表の暗記」ではなく「時間変化を $s$ 領域で代数的に扱う道具」として読む地図。",
        body,
    )


# =========================================================================== #
# 01 — Exponential decay & complex frequency  (FULL)
# =========================================================================== #
def nb01():
    body = [
        md(
            """
## 1. Big Picture

世の中の「時間変化」の多くは、ごく少数の **指数関数 $e^{st}$** の足し合わせで書けます。
ここで $s = \\sigma + i\\omega$ は複素数。$\\sigma$ が **成長・減衰**、$\\omega$ が **振動** を担当します。
ラプラス変換が強力なのは、この $e^{st}$ が微分の **固有関数**(微分しても形が変わらない)だからです。
"""
        ),
        md(
            """
## 2. Problem — 見かけは違うが同じもの

次の3つは、すべて $e^{st}$ ひとつで書けます。

- **預金**: 年率で増える残高 → $\\sigma > 0$ の成長
- **放射性崩壊 / RC 放電**: 一定割合で減る量 → $\\sigma < 0$ の減衰
- **おもり付きバネ**: 行ったり来たりする変位 → $\\omega \\ne 0$ の振動

違うのは $s$ の値だけ。では $s$ をどう読めばよいでしょうか。
"""
        ),
        md(
            """
## 3. Intuition — 指数は「変化の素」

実指数 $e^{\\sigma t}$ は、微分すると $\\sigma e^{\\sigma t}$。**自分の定数倍に戻る**唯一の関数です。
複素にしても $\\frac{d}{dt}e^{st} = s\\,e^{st}$。だから線形な系(微分が出てくる系)は、
$e^{st}$ を入れると掛け算 $s$ で応答が決まる。これが「微分 → 掛け算」の正体です。
"""
        ),
        md(
            """
## 4. Visualization — σ が決める成長と減衰

まず実指数 $e^{\\sigma t}$ を、いくつかの $\\sigma$ で重ねます。
"""
        ),
        code(
            r"""
tt = np.linspace(0, 4, 200)
plotting.plot_exponentials(tt, sigmas=[-0.6, -0.2, 0.0, 0.3, 0.6])
plt.tight_layout()
"""
        ),
        md(
            """
$\\sigma<0$ は減衰、$\\sigma=0$ は一定、$\\sigma>0$ は発散。次に **振動を足した** $e^{\\sigma t}\\cos(\\omega t)$ を、
減衰・持続・成長の3パターンで見ます(点線は包絡線 $\\pm e^{\\sigma t}$)。
"""
        ),
        code(
            r"""
tt = np.linspace(0, 8, 400)
fig, axes = plt.subplots(1, 3, figsize=(13, 3.6), sharey=True)
for ax, (sig, lab) in zip(axes, [(-0.4, "decaying"), (0.0, "sustained"), (0.25, "growing")]):
    plotting.plot_damped_oscillation(tt, sig, 4.0, ax=ax)
    ax.set_title(f"{lab}:  sigma = {sig:+.2f},  omega = 4.0")
fig.tight_layout()
"""
        ),
        md(
            """
## 5. Definition — 複素指数と複素周波数

$$ s = \\sigma + i\\omega, \\qquad e^{st} = e^{\\sigma t}\\,e^{i\\omega t} = e^{\\sigma t}\\big(\\cos\\omega t + i\\sin\\omega t\\big). $$

- $\\sigma = \\operatorname{Re}(s)$ : 包絡線 $e^{\\sigma t}$ の成長率(負なら減衰)
- $\\omega = \\operatorname{Im}(s)$ : 振動の角周波数

実数の信号 $e^{\\sigma t}\\cos(\\omega t)$ は、**共役な複素周波数の組** $s = \\sigma \\pm i\\omega$ に対応します。
"""
        ),
        code(
            r"""
# Euler's identity and the eigenfunction property, checked numerically.
tt = np.linspace(0, 3, 400)
sigma, omega = -0.4, 4.0
sv = sigma + 1j * omega
lhs = np.exp(sv * tt)
rhs = np.exp(sigma * tt) * (np.cos(omega * tt) + 1j * np.sin(omega * tt))
print("Euler identity, max |lhs - rhs| =", np.max(np.abs(lhs - rhs)))

deriv = np.gradient(lhs, tt)          # numerical d/dt e^{st}
rel = np.max(np.abs(deriv - sv * lhs)) / np.max(np.abs(sv * lhs))
print("eigenfunction d/dt e^{st} = s e^{st}, relative error =", rel)
"""
        ),
        md(
            """
## 6. Computation — s 平面の地図

複素周波数 $s$ を平面の点として描くと、**点の位置がそのまま時間応答の形**になります。
横軸 $\\sigma$ が減衰/成長、縦軸 $\\omega$ が振動。下は $s=-0.3+3i$(とその共役)の例です。
"""
        ),
        code(
            r"""
tt = np.linspace(0, 12, 500)
plotting.plot_pole_and_response(sigma=-0.3, omega=3.0, t=tt)
plt.tight_layout()
"""
        ),
        md(
            """
## 7. Invariant / Structure — なぜこれが効くのか

本質は **$e^{st}$ が $\\frac{d}{dt}$ の固有関数** であること。線形時不変な系に $e^{st}$ を入れると、
出てくるのは同じ $e^{st}$ の定数倍。だから複雑な微積分が、$s$ についての代数に化けます。
この一点が、02 章以降の「微分 → 掛け算」「ODE → 代数」「伝達関数」すべての土台です。
"""
        ),
        md(
            """
## 8. Failure Mode — 成長が速すぎると積分できない (Applied)

ラプラス変換は積分 $\\int_0^\\infty f(t)e^{-st}dt$。$f$ が速く増えると、$\\sigma$ を十分大きく取らないと
積分が発散します(**収束域 ROC**、02 章)。$e^{t^2}$ のように指数より速い増大は、どんな $\\sigma$ でも救えません。
下のスライダーで $\\sigma, \\omega$ を動かし、極の位置と応答が連動する様子を確かめてください
(静的な図は §6 と同じ対象です)。
"""
        ),
        code(
            r"""
# Interactive: drag sigma and omega; the pole pair (left) and the response (right) move together.
widgets.explore_complex_frequency()
"""
        ),
        md(
            """
## 9. Application

- **人口・複利**: $\\sigma>0$ の成長
- **放射性崩壊・冷却・RC 放電**: $\\sigma<0$ の減衰
- **LC 共振・振り子**: $\\omega\\ne0$ の振動、$\\sigma$ で減衰の有無

どれも「$s$ をどこに置くか」だけの違いとして統一的に読めます。
"""
        ),
        md(
            """
## 10. Exercises

- **Basic**: $\\sigma=-0.5,\\ \\omega=2$ の波を手描きし、包絡線と1周期を書き込め。
- **Applied**: `plotting.plot_pole_and_response` を使い、$|s|$ を一定にして角度だけ変え、
  減衰の速さが角度でどう変わるか観察せよ。
- **Advanced**: 半減期 $T_{1/2}$ と $\\sigma$ の関係 $\\sigma=-\\ln 2/T_{1/2}$ を導け。
"""
        ),
        md(
            """
## 11. Advanced Notes

- **固有関数の厳密化**: 線形時不変作用素 $\\mathcal{L}$ に対し $\\mathcal{L}e^{st}=H(s)e^{st}$ となる $H(s)$ が
  伝達関数(05 章)。$e^{st}$ は微分作用素の固有関数で、固有値が $s$。
- **特性根との関係**: 定数係数 ODE の特性方程式の根が、まさに $s$ 平面上の極(04・06 章)。
- **物理の複素周波数**: $\\sigma$ は減衰率(Q 値)、$\\omega$ は固有振動数。両者を1つの $s$ にまとめる見方。
"""
        ),
    ]
    return assemble(
        "01. 指数・減衰・複素周波数 — s 平面の読み方",
        FULL_LAYERS,
        "成長・減衰・振動を $e^{st}$ ひとつにまとめ、$s=\\sigma+i\\omega$ の位置で時間応答を読む。",
        body,
    )


# =========================================================================== #
# 02 — Definition & basic properties  (FULL)
# =========================================================================== #
def nb02():
    body = [
        md(
            """
## 1. Big Picture

ラプラス変換は積分ひとつで定義されます。

$$ F(s) = \\mathcal{L}\\{f\\}(s) = \\int_0^\\infty f(t)\\,e^{-st}\\,dt. $$

これは「$f$ を、減衰する波 $e^{-st}$ で測る」操作です。そして線形性・微分則などの **性質** が、
時間の微積分を $s$ の代数へ翻訳する辞書になります。本章でその辞書を作ります。
"""
        ),
        md(
            """
## 2. Problem

毎回 $e^{st}$ の重ね合わせを手で求めるのは大変です。**系統的に** 時間関数を $s$ 領域へ移し、
しかも微分・畳み込み・初期条件をきれいに扱う仕組みが欲しい。定義の積分とその性質がそれを与えます。
"""
        ),
        md(
            """
## 3. Intuition — e^{-st} は「測定プローブ」

$e^{-st}$ を掛けて積分するのは、「$f$ の中に、減衰率 $\\sigma$・振動 $\\omega$ の成分がどれだけあるか」を
測ることです。$\\sigma$ を変えると、ゆっくり減る成分・速く減る成分を選り分けられます。
"""
        ),
        md(
            """
## 4. Visualization — 被積分関数 f(t)e^{-σt} の面積が F(σ)

$f(t)=e^{-t}$ について、$f(t)e^{-\\sigma t}$ を数本の $\\sigma$ で描きます。曲線の下の面積がちょうど $F(\\sigma)$。
$\\sigma$ が大きいほど速く減衰し、面積(=$F$)が小さくなります。
"""
        ),
        code(
            r"""
tt = np.linspace(0, 8, 400)
fig, ax = plt.subplots(figsize=(6.5, 4))
for sig in [0.0, 0.5, 1.0, 2.0]:
    ax.plot(tt, np.exp(-tt) * np.exp(-sig * tt), label=f"sigma = {sig:.1f}  ->  F = {1/(1+sig):.3f}")
ax.set_title("integrand  f(t) e^{-sigma t}  for f(t)=e^{-t}   (area under = F(sigma))")
ax.set_xlabel("t"); ax.set_ylabel("f(t) e^{-sigma t}"); ax.legend(); ax.grid(alpha=0.25)
plt.tight_layout()
"""
        ),
        md(
            """
## 5. Definition と 収束域 (ROC)

$$ F(s)=\\int_0^\\infty f(t)e^{-st}\\,dt, \\qquad \\text{収束するのは } \\operatorname{Re}(s)>\\sigma_0. $$

この $\\sigma_0$(収束横座標)より右側が **収束域 (ROC)**。$f$ が $e^{\\sigma_0 t}$ 程度の増大(指数オーダー)なら
$\\sigma > \\sigma_0$ で積分が収まります。
"""
        ),
        md(
            """
## 6. Computation — 記号と数値、両方で

SymPy で記号的に、求積で数値的に求め、突き合わせます。
"""
        ),
        code(
            r"""
# Symbolic transform of f(t)=e^{-2t}: F(s)=1/(s+2).
F = L(sp.exp(-2 * t))
display(F)

# Numeric transform at s=3 should match 1/(3+2)=0.2.
print("numeric F(3)  =", numeric_laplace(lambda x: np.exp(-2 * x), 3.0))
print("symbolic F(3) =", float(F.subs(s, 3)))
"""
        ),
        md(
            """
## 7. Invariant / Structure — 翻訳辞書(基本性質)

| 時間領域 | $s$ 領域 |
|---|---|
| $a f + b g$ | $aF + bG$ (線形性) |
| $f'(t)$ | $sF(s) - f(0)$ |
| $f''(t)$ | $s^2F(s) - s f(0) - f'(0)$ |
| $\\int_0^t f$ | $F(s)/s$ |
| $f(t-a)u(t-a)$ | $e^{-as}F(s)$ (時間シフト) |
| $e^{-at}f(t)$ | $F(s+a)$ (周波数シフト) |
| 初期値定理 | $f(0^+)=\\lim_{s\\to\\infty} sF(s)$ |

主役は **微分則** $\\mathcal{L}\\{f'\\}=sF-f(0)$。微分が $s$ の掛け算になり、しかも **初期値 $f(0)$ が自動で入る**。
"""
        ),
        code(
            r"""
# Verify the derivative rule symbolically for f(t)=sin(2t).
f_expr = sp.sin(2 * t)
F = L(f_expr)
lhs = L(sp.diff(f_expr, t))            # L{f'}
rhs = s * F - f_expr.subs(t, 0)        # s F(s) - f(0)
print("L{f'} - (sF - f(0)) simplifies to:")
display(sp.simplify(lhs - rhs))
print("derivative rule holds:", transforms.verify_derivative_rule(f_expr))
"""
        ),
        code(
            r"""
# The same rule, checked numerically: f=e^{-t}, f'=-e^{-t}, at s=2.
f = lambda x: np.exp(-x)
fp = lambda x: -np.exp(-x)
s0 = 2.0
F = numeric_laplace(f, s0)
print("L{f'} numeric :", numeric_laplace(fp, s0))
print("s F - f(0)    :", s0 * F - f(0))   # both should be -1/3
"""
        ),
        md(
            """
## 8. Failure Mode — ROC を外すと積分が発散 (Applied)

$f(t)=e^{-2t}$ の収束域は $\\operatorname{Re}(s)>-2$。$s=3$ では部分積分 $\\int_0^{T}$ が $0.2$ に収束しますが、
$s=-3$ では被積分が $e^{t}$ となり、$T$ とともに発散します。
"""
        ),
        code(
            r"""
from scipy.integrate import quad

def partial_integral(s_val, t_max):
    return quad(lambda x: np.exp(-2 * x) * np.exp(-s_val * x), 0, t_max)[0]

print(f"{'t_max':>6} {'s=3 (in ROC)':>16} {'s=-3 (outside)':>18}")
for tm in [5, 10, 20, 40]:
    print(f"{tm:>6} {partial_integral(3.0, tm):>16.6f} {partial_integral(-3.0, tm):>18.3e}")
"""
        ),
        md(
            """
$s=3$ 列は $0.2$ に落ち着き、$s=-3$ 列はどんどん大きくなります。**ROC の外では変換が定義されない**、
というのを数値で確かめました。
"""
        ),
        md(
            """
## 9. Application

- **回路**: コイル・コンデンサの初期電流・初期電圧が、微分則の $f(0)$ として式へ入る(07 章)。
- **制御**: 入力のシフト $e^{-as}$ はむだ時間(遅れ)。
- **ODE**: 初期値問題がそのまま代数に(04 章)。
"""
        ),
        md(
            """
## 10. Exercises

- **Basic**: 線形性を使って $\\mathcal{L}\\{3 - 2e^{-t}\\}$ を求めよ。
- **Applied**: 周波数シフトで $\\mathcal{L}\\{e^{-t}\\cos 3t\\}$ を導き、`transforms.L` で確認せよ。
- **Advanced**: 初期値定理 $f(0^+)=\\lim_{s\\to\\infty}sF(s)$ を $f=\\cos\\omega t$ で確かめよ。
"""
        ),
        md(
            """
## 11. Advanced Notes

- **存在条件**: $f$ が区分連続かつ指数オーダー($|f(t)|\\le Me^{\\sigma_0 t}$)なら $\\operatorname{Re}(s)>\\sigma_0$ で存在。
- **初期値・最終値定理**: 最終値 $\\lim_{t\\to\\infty}f(t)=\\lim_{s\\to0}sF(s)$ は、$sF(s)$ の極がすべて左半面のときのみ有効。
- **両側変換との違い**: 本書は片側($t\\ge0$)。初期条件の扱いと因果性が片側変換の利点。
"""
        ),
    ]
    return assemble(
        "02. 定義と基本性質 — 微積分を s の代数へ翻訳する",
        FULL_LAYERS,
        "定義の積分・収束域・線形性・微分則・各種シフトという「翻訳辞書」を、記号と数値の両面で作る。",
        body,
    )


# =========================================================================== #
# 03 — Inverse Laplace & partial fractions  (lighter, real content)
# =========================================================================== #
def nb03():
    body = [
        md(
            """
## 1. Big Picture / 2. Problem

$s$ 領域で代数的に $F(s)$ を得たら、最後に **時間へ戻す** 必要があります。

$$ f(t) = \\mathcal{L}^{-1}\\{F(s)\\}. $$

実務ではほとんどの $F(s)$ が **有理関数**(多項式/多項式)。鍵は **部分分数分解** で、
変換表で逆変換できる小片に割ることです。
"""
        ),
        md(
            """
## 3. Intuition / 4. 変換表(逆向き)

| $F(s)$ | $f(t)$ |
|---|---|
| $1/(s+a)$ | $e^{-at}$ |
| $1/(s+a)^2$ | $t\\,e^{-at}$ (重根 → $t$ が掛かる) |
| $\\omega/((s+a)^2+\\omega^2)$ | $e^{-at}\\sin\\omega t$ (複素極 → 減衰振動) |
| $(s+a)/((s+a)^2+\\omega^2)$ | $e^{-at}\\cos\\omega t$ |

**単純極 → 指数**、**重根 → $t^k$ 付き**、**複素共役極 → 減衰振動**、と覚えると見通しが良いです。
"""
        ),
        md(
            """
## 5. Definition / 6. Computation — 単純極

$F(s)=\\dfrac{s+3}{(s+1)(s+2)}$ を部分分数に割り、各片を逆変換します。
"""
        ),
        code(
            r"""
F = (s + 3) / ((s + 1) * (s + 2))
print("partial fractions:")
display(partial_fractions(F))      # 2/(s+1) - 1/(s+2)
print("inverse transform f(t):")
display(Linv(F))                   # 2 e^{-t} - e^{-2t}
"""
        ),
        md(
            """
## 7. 重根の場合

$F(s)=\\dfrac{1}{(s+1)^2}$ のような重根は、$t$ が掛かった項を生みます。
"""
        ),
        code(
            r"""
display(Linv(1 / (s + 1) ** 2))            # t e^{-t}
display(Linv(1 / (s * (s + 1) ** 2)))      # mixes a constant, e^{-t}, and t e^{-t}
"""
        ),
        md(
            """
## 8. 複素極の場合 → 減衰振動

分母が実根を持たない2次式 $s^2+2s+5=(s+1)^2+4$ は、複素共役極 $s=-1\\pm2i$。逆変換は減衰振動です。
"""
        ),
        code(
            r"""
F = 1 / (s**2 + 2 * s + 5)
f = sp.simplify(Linv(F))
display(f)                                  # e^{-t} sin(2t)/2

tt = np.linspace(0, 8, 400)
yfun = transforms.as_function(f)
plotting.plot_time_responses(tt, [yfun(tt)], labels=["L^{-1}{1/((s+1)^2+4)}"],
                             title="complex poles -> damped oscillation")
plt.tight_layout()
"""
        ),
        md(
            """
## 9. Application / 10. Failure Mode — 逆変換の注意点

- **一意性**: 片側ラプラス変換では $t\\ge0$ で(良い条件のもとで)一意。ただし両側変換や ROC を無視すると別解が出る。
- **数値逆変換は難しい**: ブロムウィッチ積分の直接数値化は悪条件。実務では部分分数 + 表が基本。
- 本書では SymPy の記号逆変換を主に使う(`Linv`)。
"""
        ),
        md(
            """
## 11. Exercises / Advanced & TODO

- **演習**: $\\dfrac{2s+1}{s^2+s}$、$\\dfrac{1}{(s+2)^3}$、$\\dfrac{s}{s^2+4}$ を逆変換せよ。
- **Advanced**: 留数(residue)による逆変換 $f(t)=\\sum \\operatorname{Res}[F(s)e^{st}]$ をまとめよ。

> **TODO(今後の拡張)**: ヘヴィサイドの展開定理の手計算、`scipy.signal.residue` による数値部分分数、
> むだ時間 $e^{-as}$ を含む像の逆変換(時間シフト)を追加。
"""
        ),
    ]
    return assemble(
        "03. 逆ラプラス変換と部分分数分解 — s 領域から時間へ戻す",
        FULL_LAYERS,
        "有理関数 $F(s)$ を部分分数に割り、単純極・重根・複素極を表で時間へ戻す。",
        body,
    )


# =========================================================================== #
# 04 — Solving ODEs with Laplace  (FULL)
# =========================================================================== #
def nb04():
    body = [
        md(
            """
## 1. Big Picture — 4 ステップのパイプライン

ラプラス変換は、初期値問題を次の流れで「解く」のではなく「整理する」ことに変えます。

> 1. ODE を $s$ 領域へ変換(微分則で $f(0)$ が自動で入る) →
> 2. $Y(s)$ について **代数的に** 解く →
> 3. 部分分数に割る →
> 4. 逆変換で $y(t)$ へ戻す。
"""
        ),
        md(
            """
## 2. Problem / 3. Intuition

$$ a y'' + b y' + c y = g(t), \\qquad y(0),\\ y'(0)\\ \\text{与えられる}. $$

時間領域では同次解 + 特解 + 初期条件合わせ、と手順が多い。$s$ 領域なら微分が掛け算になり、
$$ Y(s) = \\frac{G(s) + (\\text{初期値の項})}{as^2 + bs + c} $$
と **一発で** 書けます。分母 $as^2+bs+c$ が系の素性(極)を決めます。
"""
        ),
        md(
            """
## 5. Definition / 6. Computation — 1階(まず手で)

$y' + a y = 0,\\ y(0)=y_0$。変換すると $sY - y_0 + aY = 0 \\Rightarrow Y=\\dfrac{y_0}{s+a} \\Rightarrow y=y_0e^{-at}$。
"""
        ),
        code(
            r"""
a, y0 = sp.symbols("a", positive=True), sp.symbols("y0")
Y = y0 / (s + a)
display(Linv(Y))           # y0 e^{-a t}
"""
        ),
        md(
            """
**強制つき1階**: $y' + y = 1$(ステップ入力)、$y(0)=0$。
$sY + Y = 1/s \\Rightarrow Y=\\dfrac{1}{s(s+1)} \\Rightarrow y = 1 - e^{-t}$。
"""
        ),
        code(
            r"""
Y = 1 / (s * (s + 1))
display(partial_fractions(Y))     # 1/s - 1/(s+1)
display(Linv(Y))                  # 1 - e^{-t}
"""
        ),
        md(
            """
## 6b. 2階 — 減衰の自由振動(手計算と数値の一致)

$y'' + 3y' + 2y = 0,\\ y(0)=1,\\ y'(0)=0$。微分則より
$(s^2+3s+2)Y = s\\,y(0) + y'(0) + 3y(0) = s + 3$。よって $Y=\\dfrac{s+3}{(s+1)(s+2)}$。
"""
        ),
        code(
            r"""
y0v, yp0v = 1.0, 0.0
Y = (s * y0v + yp0v + 3 * y0v) / (s**2 + 3 * s + 2)
yt = sp.simplify(Linv(Y))
print("Laplace solution y(t) ="); display(yt)            # 2 e^{-t} - e^{-2t}

# Cross-check against a direct numerical ODE solve.
from scipy.integrate import solve_ivp
tt = np.linspace(0, 6, 300)
sol = solve_ivp(lambda tau, yv: [yv[1], -3 * yv[1] - 2 * yv[0]],
                (0, 6), [1.0, 0.0], t_eval=tt, rtol=1e-9, atol=1e-12)
yfun = transforms.as_function(yt)
print("max |Laplace - solve_ivp| =", np.max(np.abs(yfun(tt) - sol.y[0])))

plotting.plot_time_responses(tt, [yfun(tt), sol.y[0]],
                             labels=["Laplace: 2e^{-t}-e^{-2t}", "solve_ivp"],
                             title="ODE via Laplace vs numerical")
plt.tight_layout()
"""
        ),
        md(
            """
## 7. Invariant / Structure — 強制振動と減衰の3様相

質量-バネ-ダンパ $y'' + 2\\zeta\\omega_n y' + \\omega_n^2 y = \\omega_n^2 u(t)$(ステップ強制)の応答は、
減衰比 $\\zeta$ で姿が変わります。極 $s=-\\zeta\\omega_n\\pm\\omega_n\\sqrt{\\zeta^2-1}$ の素性そのものです。
"""
        ),
        code(
            r"""
tt = np.linspace(0, 14, 600)
fig, ax = plt.subplots(figsize=(7, 4.2))
for zeta in [0.2, 0.5, 1.0, 2.0]:
    sys = systems.second_order(wn=1.5, zeta=zeta)
    ax.plot(tt, systems.step_response(sys, tt), label=f"zeta = {zeta}")
ax.axhline(1.0, color="gray", ls=":", lw=1)
ax.set_title("step response of  wn^2/(s^2 + 2*zeta*wn*s + wn^2),  wn=1.5")
ax.set_xlabel("t"); ax.set_ylabel("y(t)"); ax.legend(); ax.grid(alpha=0.25)
plt.tight_layout()
"""
        ),
        md(
            """
$\\zeta<1$ は行き過ぎて振動(underdamped)、$\\zeta=1$ が最速で行き過ぎない(critical)、
$\\zeta>1$ はゆっくり(overdamped)。すべて分母(極)で決まります(06 章)。
"""
        ),
        md(
            """
## 8. Failure Mode

- 分母 $as^2+bs+c$ の根が **右半面** にあると $y(t)$ が発散(不安定、06 章)。
- 入力 $g(t)$ が系の固有周波数と一致すると **共振**(虚軸極 + 同じ虚軸の入力)。
- 初期条件を入れ忘れると、過渡応答を取り違える。
"""
        ),
        md(
            """
## 9. Application

RC/RLC 回路の過渡(07 章)、サスペンションの乗り心地、サーボの位置決め、いずれも本章のパイプラインそのもの。
"""
        ),
        md(
            """
## 10. Exercises

- **Basic**: $y'+2y=0,\\ y(0)=3$ を $s$ 領域で解け。
- **Applied**: $y''+y=\\sin t,\\ y(0)=y'(0)=0$ の共振解を `Linv` で求め、振幅が $t$ に比例することを見よ。
- **Advanced**: 一般の $ay''+by'+cy=g$ の $Y(s)$ を導き、初期値項と強制項に分けて意味づけよ。
"""
        ),
        md(
            """
## 11. Advanced Notes

- **零状態応答 + 零入力応答**: $Y(s)=\\underbrace{H(s)G(s)}_{\\text{zero-state}} + \\underbrace{\\frac{\\text{初期値項}}{as^2+bs+c}}_{\\text{zero-input}}$。
  前者は伝達関数(05 章)、後者は初期条件由来。
- **共振の像**: 虚軸上の入力極が系の極と重なると重根化し、$t\\sin\\omega t$ が現れる。
"""
        ),
    ]
    return assemble(
        "04. ラプラス変換で ODE を解く — 微分方程式を代数にする",
        FULL_LAYERS,
        "初期値問題を「変換 → 代数で $Y(s)$ → 部分分数 → 逆変換」の4ステップに落とし、数値解と一致を確認。",
        body,
    )


# =========================================================================== #
# 05 — Convolution, impulse response, transfer functions  (FULL)
# =========================================================================== #
def nb05():
    body = [
        md(
            """
## 1. Big Picture

線形時不変(LTI)な系は、たった1つの関数 **インパルス応答 $h(t)$**(または **伝達関数 $H(s)$**)で
完全に決まります。任意入力 $x$ への出力は

$$ y(t) = (h * x)(t) \\quad\\Longleftrightarrow\\quad Y(s) = H(s)\\,X(s). $$

**時間では畳み込み、$s$ では掛け算**。これが本章の主題です。
"""
        ),
        md(
            """
## 2. Problem / 3. Intuition — 畳み込みとは

畳み込み

$$ (f * g)(t) = \\int_0^t f(\\tau)\\,g(t-\\tau)\\,d\\tau $$

は「入力を少しずつ流し込み、過去の影響が尾を引きながら混ざる」操作。直感的には難しいのに、
$s$ 領域に移すと **ただの掛け算** $F(s)G(s)$ になります(畳み込み定理)。
"""
        ),
        md(
            """
## 4. Visualization — 時間の畳み込み

入力パルス $f$ とインパルス応答 $g(t)=e^{-2t}$ の畳み込みを描きます。
"""
        ),
        code(
            r"""
dt = 0.01
tt = np.arange(0, 10, dt)
f = datasets.unit_step(tt, 0.5) - datasets.unit_step(tt, 1.5)   # a rectangular pulse
g = np.exp(-2 * tt)                                             # exponential response
conv = systems.convolve(f, g, dt)
plotting.plot_convolution(tt, f, g, conv)
plt.tight_layout()
"""
        ),
        md(
            """
## 5. Definition / 6. Computation — 畳み込み定理を確かめる

$f=e^{-t},\\ g=e^{-2t}$。畳み込み定理より $\\mathcal{L}\\{f*g\\}=\\dfrac{1}{(s+1)(s+2)}$、
よって $(f*g)(t)=e^{-t}-e^{-2t}$。時間で直接畳み込んだ結果と一致するはずです。
"""
        ),
        code(
            r"""
dt = 0.005
tt = np.arange(0, 12, dt)
conv_time = systems.convolve(np.exp(-tt), np.exp(-2 * tt), dt)     # time-domain

F, G = 1 / (s + 1), 1 / (s + 2)
prod = sp.apart(F * G, s)
display(prod)                                                      # 1/(s+1) - 1/(s+2)
conv_s = transforms.as_function(Linv(F * G))(tt)                   # via s-domain product

print("max |time-domain conv - s-domain product| =", np.max(np.abs(conv_time - conv_s)))
plotting.plot_time_responses(tt, [conv_time, conv_s],
                             labels=["np.convolve (time)", "L^{-1}{F(s)G(s)}"],
                             title="convolution theorem:  time conv == s-domain product")
plt.tight_layout()
"""
        ),
        md(
            """
## 7. Invariant / Structure — インパルス応答と伝達関数

$x(t)=\\delta(t)$ を入れると $X(s)=1$ なので $Y(s)=H(s)$。逆変換した $h(t)=\\mathcal{L}^{-1}\\{H\\}$ が
**インパルス応答**。これが系の「指紋」で、任意入力の出力は $h$ との畳み込みで出ます。下で
「`lsim` による出力」と「インパルス応答との畳み込み」が一致することを確かめます。
"""
        ),
        code(
            r"""
dt = 0.01
tt = np.arange(0, 12, dt)
sys = systems.first_order(tau=1.0)            # H(s) = 1/(s+1)
h = systems.impulse_response(sys, tt)         # h(t) = e^{-t}
u = np.ones_like(tt)                          # unit step input

y_lsim = systems.forced_response(sys, u, tt)  # output via state-space simulation
y_conv = systems.convolve(u, h, dt)           # output via convolution with h

print("max |lsim - (h * u)| =", np.max(np.abs(y_lsim - y_conv)))
plotting.plot_time_responses(tt, [y_lsim, y_conv],
                             labels=["lsim output", "convolution h * u"],
                             title="output = impulse response convolved with input")
plt.tight_layout()
"""
        ),
        md(
            """
## 8. 伝達関数 H(s) = Y(s)/X(s)

ステップ入力 $X(s)=1/s$ を $H(s)=1/(s+1)$ に通すと $Y=\\dfrac{1}{s(s+1)}\\to y=1-e^{-t}$。
入力(像)に伝達関数を掛けて逆変換、というのが LTI 系の基本動作です。
"""
        ),
        code(
            r"""
H = 1 / (s + 1)
X = 1 / s                      # unit step
Y = H * X
display(Linv(Y))               # 1 - e^{-t}
"""
        ),
        md(
            """
## 9. Application / 10. Failure Mode

- **応用**: フィルタ(平滑化 = 低域通過)、残響(エコー = 畳み込み)、系の同定(入出力から $H$ を推定)。
- **注意**: 畳み込み定理は **LTI かつ因果・初期静止** が前提。非線形系や時変系では成り立たない。
"""
        ),
        md(
            """
## 11. Exercises / Advanced

- **Basic**: $H=1/(s+2)$ のインパルス応答とステップ応答を求めよ。
- **Applied**: 2つの1次系の直列 $H_1H_2$ のインパルス応答を畳み込みで作り、`systems.series` と比べよ。
- **Advanced**: LTI 性(線形 + 時不変)から、出力が必ず畳み込みで書けることを示せ。
"""
        ),
    ]
    return assemble(
        "05. 畳み込み・インパルス応答・伝達関数 — 入力を出力に変える",
        FULL_LAYERS,
        "時間の畳み込み = $s$ の積。インパルス応答 $h$ と伝達関数 $H$ が LTI 系を完全に決める。",
        body,
    )


# =========================================================================== #
# 06 — Poles, zeros, stability  (FULL)
# =========================================================================== #
def nb06():
    body = [
        md(
            """
## 1. Big Picture

伝達関数 $H(s)=\\dfrac{N(s)}{D(s)}$ の **極**(分母 $D(s)=0$ の根)が、時間応答の形と安定性を決めます。
極の位置を $s$ 平面で読むだけで、減衰するか・振動するか・発散するかが分かります。
"""
        ),
        md(
            """
## 2. Problem / 3. Intuition

各極 $s_k=\\sigma_k+i\\omega_k$ は、応答に項 $e^{\\sigma_k t}\\,(\\cos/\\sin\\,\\omega_k t)$ を1つ持ち込みます(01 章の $e^{st}$)。
だから「極の実部 $\\sigma_k$ の符号」がそのまま安定性、「虚部 $\\omega_k$」が振動の速さになります。
"""
        ),
        md(
            """
## 4. Visualization — 極の位置と応答の形

代表的な4つの極配置と、それぞれの応答を並べます。
"""
        ),
        code(
            r"""
tt = np.linspace(0, 12, 500)
cases = [
    (-0.8, 0.0, "LHP real: pure decay"),
    (-0.3, 3.0, "LHP complex: damped oscillation"),
    (0.0, 3.0, "imaginary axis: sustained oscillation"),
    (0.25, 3.0, "RHP complex: growing oscillation"),
]
fig, axes = plt.subplots(2, 2, figsize=(12, 7))
for ax, (sig, om, lab) in zip(axes.ravel(), cases):
    y = np.exp(sig * tt) * np.cos(om * tt)
    ax.plot(tt, y, color=plotting.ACCENT)
    ax.plot(tt, np.exp(sig * tt), "--", color="gray", lw=1)
    ax.plot(tt, -np.exp(sig * tt), "--", color="gray", lw=1)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_title(f"s = {sig:+.2f} +/- {om:.0f}i   ({lab})")
    ax.set_xlabel("t"); ax.grid(alpha=0.25)
fig.tight_layout()
"""
        ),
        md(
            """
## 5. Definition / 6. Computation — 極・零点と s 平面

- **零点**: $N(s)=0$ の根(応答を弱める方向)。
- **極**: $D(s)=0$ の根(応答の形を決める)。

例として $H(s)=\\dfrac{s+1}{s^2+s+4}$ の極・零点を $s$ 平面に描きます。
"""
        ),
        code(
            r"""
H = systems.tf([1.0, 1.0], [1.0, 1.0, 4.0])
print("poles:", systems.poles(H))
print("zeros:", systems.zeros(H))
print("stability:", systems.classify_stability(H))
plotting.plot_s_plane(poles=systems.poles(H), zeros=systems.zeros(H), title="poles (x) and zeros (o)")
plt.tight_layout()
"""
        ),
        md(
            """
## 6b. |F(s)| を s 平面上の地形として見る (Applied, interactive)

$|H(s)|$ を $s$ 平面上の高さとして描くと、**極が山のように尖ります**。下は $H=1/((s+1)^2+9)$、
極 $s=-1\\pm3i$。マウスで回して、尖りの真下に極があることを確かめてください。
"""
        ),
        code(
            r"""
H_eval = lambda S: 1.0 / ((S + 1.0) ** 2 + 9.0)   # poles at s = -1 +/- 3i
fig = plotting.surface_abs_F(H_eval, sigma_range=(-3, 1), omega_range=(-7, 7), n=70)
fig
"""
        ),
        md(
            """
## 7. Invariant / Structure — 安定性の判定

- **左半面 (LHP, $\\sigma<0$)**: すべての極がここなら **安定**(過渡応答は消える)。
- **虚軸上 ($\\sigma=0$)**: 持続振動の **臨界**(marginal)。
- **右半面 (RHP, $\\sigma>0$)**: 1つでもあれば **不安定**(発散)。

`systems.classify_stability` がこの判定を行います。
"""
        ),
        code(
            r"""
examples = {
    "1/(s+1)        ": systems.first_order(1.0),
    "1/(s^2+s+4)    ": systems.tf([1.0], [1.0, 1.0, 4.0]),
    "1/(s^2+4)      ": systems.tf([1.0], [1.0, 0.0, 4.0]),
    "1/(s-1)        ": systems.tf([1.0], [1.0, -1.0]),
}
for name, sysk in examples.items():
    print(f"{name}: poles={np.round(systems.poles(sysk), 3)}  ->  {systems.classify_stability(sysk)}")
"""
        ),
        md(
            """
## 8. Failure Mode / 過渡応答 と 定常応答

ステップ応答は **過渡(極が決める、やがて消える)** と **定常(入力の極 $s=0$ が決める、残る)** の和。
減衰比 $\\zeta$ を動かして、極の位置(左の図)と応答(右の図)の連動を見ます。
"""
        ),
        code(
            r"""
# Interactive: wn and zeta move the pole pair and reshape the step response.
widgets.explore_second_order()
"""
        ),
        md(
            """
## 9. Application

- **制御設計**: 望む応答(速さ・行き過ぎ)になるよう、極を左半面の狙った位置へ動かす(07 章)。
- **共振回避**: 虚軸近くの極は鋭い共振 → ダンピングで左へ。
"""
        ),
        md(
            """
## 10. Exercises / 11. Advanced

- **Basic**: $1/((s+2)^2+9)$ の極を求め、減衰の速さと振動数を読め。
- **Applied**: $1/(s^2+bs+1)$ の $b$ を $0\\to3$ と変え、極の軌跡(根軌跡の一種)を $s$ 平面に描け。
- **Advanced**: Routh-Hurwitz 判定法で、係数だけから右半面極の有無を判定する方法をまとめよ。
- **Advanced**: 零点は応答の **形** に効くが安定性には効かない理由を説明せよ。
"""
        ),
    ]
    return assemble(
        "06. 極・零点・安定性 — 極の位置が応答と安定性を決める",
        FULL_LAYERS,
        "極 $D(s)=0$ の位置(左半面/虚軸/右半面)が、減衰・持続・発散をそのまま決める。",
        body,
    )


# =========================================================================== #
# 07 — Control systems & circuits  (lighter, real content)
# =========================================================================== #
def nb07():
    body = [
        md(
            """
## 1. Big Picture / 2. Problem

回路や制御系は「入力 → 出力」を持つ **システム**。$s$ 領域でインピーダンス($R,\\ sL,\\ 1/sC$)を書くと、
分圧の規則がそのまま伝達関数になります。本章は RC/RLC とフィードバックを通して 04〜06 章を実機に接続します。
"""
        ),
        md(
            """
## 3. RC 回路 — 1次系のステップ応答

低域通過 RC: $H(s)=\\dfrac{1}{RCs+1}$、時定数 $\\tau=RC$。ステップ応答は $1-e^{-t/\\tau}$ で、
$t=\\tau$ で約 63% に到達します。
"""
        ),
        code(
            r"""
R, C = 1000.0, 1e-6           # tau = RC = 1 ms
sys = circuits.rc_lowpass(R, C)
tau = R * C
tt = np.linspace(0, 6 * tau, 400)
y = systems.step_response(sys, tt)
ax = plotting.plot_time_responses(tt, [y], labels=[f"step response, tau={tau*1e3:.1f} ms"],
                                  title="RC low-pass step response")
ax.axhline(1.0, color="gray", ls=":"); ax.axvline(tau, color="r", ls="--", lw=1)
ax.axhline(1 - np.exp(-1), color="r", ls=":", lw=1)   # ~63% at t = tau
plt.tight_layout()
print("DC gain:", systems.dc_gain(sys), " time constant:", systems.time_constant(sys))
"""
        ),
        md(
            """
## 4. RLC 回路 — 2次系の過渡

直列 RLC(コンデンサ出力): $H(s)=\\dfrac{1}{LCs^2+RCs+1}$。$\\omega_n=1/\\sqrt{LC}$、$\\zeta=\\tfrac{R}{2}\\sqrt{C/L}$。
$R$ を変えると underdamped / critical / overdamped が切り替わります。
"""
        ),
        code(
            r"""
L, C = 1e-3, 1e-6
tt = np.linspace(0, 4e-3, 600)
fig, ax = plt.subplots(figsize=(7, 4.2))
for R in [20.0, 63.2, 200.0]:
    sys = circuits.rlc_series_vc(R, L, C)
    p = circuits.rlc_params(R, L, C)
    ax.plot(tt * 1e3, systems.step_response(sys, tt), label=f"R={R:g} ({p['regime']}, zeta={p['zeta']:.2f})")
ax.axhline(1.0, color="gray", ls=":")
ax.set_title("series RLC (output across C): step response")
ax.set_xlabel("t [ms]"); ax.set_ylabel("v_C / V_in"); ax.legend(); ax.grid(alpha=0.25)
plt.tight_layout()
"""
        ),
        md(
            """
## 5. フィードバック — 閉ループ伝達関数

負帰還の閉ループは

$$ H_{\\mathrm{closed}}(s)=\\frac{G(s)}{1+G(s)K(s)}. $$

フィードバックは **極を動かし**、応答の速さと安定性を変えます。下のスライダーでループゲイン $K$ を上げ、
閉ループ極が左へ動いて応答が速くなる一方、上げすぎると振動的になる様子を見ます。
"""
        ),
        code(
            r"""
# Interactive: loop gain K reshapes the closed-loop poles and step response.
widgets.explore_feedback()
"""
        ),
        md(
            """
## 6. Bode 線図の入口

周波数応答 $H(i\\omega)$ の大きさ・位相を対数で描くのが Bode 線図。RC 低域通過のロールオフを見ます。
"""
        ),
        code(
            r"""
sys = circuits.rc_lowpass(1000.0, 1e-6)
w = np.logspace(1, 6, 400)
plotting.plot_bode(sys, w=w)
plt.tight_layout()
"""
        ),
        md(
            """
## 7〜11. Application / Exercises / Advanced & TODO

- **応用**: アンチエイリアスフィルタ、サスペンション、サーボ位置決め、温度制御。
- **演習(Basic)**: RC で時定数を半分にするには $R,C$ をどうする?
- **演習(Applied)**: `systems.feedback` で $G=1/(s(s+1))$ の閉ループ極を $K$ について追え。
- **Advanced**: 比例 + 積分(PI)制御 $K(s)=K_p+K_i/s$ が定常偏差を消す理由を最終値定理で示せ。

> **TODO(今後の拡張)**: PID 制御の設計例、根軌跡(root locus)の作図、位相余裕・ゲイン余裕、
> オペアンプ回路の伝達関数、ナイキスト線図を追加。
"""
        ),
    ]
    return assemble(
        "07. 制御系と回路 — 伝達関数とフィードバック",
        FULL_LAYERS,
        "RC/RLC の過渡応答とフィードバックの閉ループを通して、04〜06 章を実際のシステムに接続する。",
        body,
    )


# =========================================================================== #
# 08 — Applications: probability, signals, finance  (lighter, real content)
# =========================================================================== #
def nb08():
    body = [
        md(
            """
## 1. Big Picture

「$e^{-st}$ で重みづけて積分する」という同じ形が、確率・信号・金融に何度も現れます。本章はその接続を
直感的に示します(深入りはしません)。
"""
        ),
        md(
            """
## 2. 確率分布のラプラス変換 と モーメント母関数

非負確率変数 $X$ の密度 $f_X$ に対し $\\varphi(s)=\\mathbb{E}[e^{-sX}]=\\int_0^\\infty f_X(x)e^{-sx}dx$ は
まさにラプラス変換。モーメント母関数 $M_X(\\theta)=\\mathbb{E}[e^{\\theta X}]=\\varphi(-\\theta)$ と表裏一体で、
$$ \\mathbb{E}[X]=-\\varphi'(0),\\qquad \\mathbb{E}[X^2]=\\varphi''(0). $$
指数分布 $f_X=\\lambda e^{-\\lambda x}$ で確かめます。
"""
        ),
        code(
            r"""
lam = sp.symbols("lambda", positive=True)
phi = lam / (s + lam)                       # Laplace transform of the exponential pdf
display(phi)
EX = sp.simplify(-sp.diff(phi, s).subs(s, 0))
EX2 = sp.simplify(sp.diff(phi, s, 2).subs(s, 0))
print("E[X]  =", EX, "   (= 1/lambda)")
print("E[X^2]=", EX2, "   (= 2/lambda^2)")
print("Var   =", sp.simplify(EX2 - EX**2))
"""
        ),
        md(
            """
## 3. 割引現在価値 (PV) — 金融の中のラプラス変換

連続割引の現在価値

$$ PV=\\int_0^\\infty c(t)\\,e^{-rt}\\,dt $$

は、キャッシュフロー $c(t)$ のラプラス変換を $s=r$ で評価したもの。一定 $c$ なら $PV=c/r$、
成長率 $g$ の $c(t)=c_0e^{gt}$ なら $PV=\\dfrac{c_0}{r-g}$(**Gordon 成長モデル**)。
ここで収束条件 $r>g$ は、まさにラプラス変換の **収束域(ROC)** です。
"""
        ),
        code(
            r"""
r, g, c0 = 0.08, 0.03, 100.0
pv_numeric = numeric_laplace(lambda x: c0 * np.exp(g * x), r, t_max=400).real
print("PV numeric        :", pv_numeric)
print("PV analytic c0/(r-g):", c0 / (r - g))     # Gordon growth; requires r > g (the ROC)
"""
        ),
        md(
            """
$r\\le g$ だと積分が発散し、PV が定義できません。これは「ROC の外」と同じことで、
**割引率が成長率を上回らねばならない** という金融の常識が、収束域として自然に出てきます。
"""
        ),
        md(
            """
## 4. 信号処理 / 待ち行列の入口

- **信号処理**: フィルタは畳み込み = $s$ での積(05 章)。連続系は $s$、離散系は $z$ 変換へ拡張。
- **待ち行列**: M/M/1 などの待ち時間分布は **ラプラス-スティルチェス変換** で解析される(本書では入口のみ)。
"""
        ),
        md(
            """
## 5. Failure Mode / 注意点

- 金融でのラプラス変換は **万能な予測器ではない**。割引・現在価値・待ち時間分布との接続を整理する道具。
- 確率過程・SDE は入口だけ。深入りは専門書へ。
"""
        ),
        md(
            """
## 6. Exercises / Advanced & TODO

- **Basic**: 一定キャッシュフロー $c$ の永久債 $PV=c/r$ を積分で確かめよ。
- **Applied**: ガンマ分布 $f_X=\\frac{\\lambda^k x^{k-1}e^{-\\lambda x}}{(k-1)!}$ のラプラス変換 $\\big(\\frac{\\lambda}{s+\\lambda}\\big)^k$ を導け。
- **Advanced**: 合成分布(独立和)のラプラス変換が積になることを、畳み込み定理(05 章)から説明せよ。

> **TODO(今後の拡張)**: ラプラス-スティルチェス変換と M/M/1 待ち時間、複利・債券価格の期間構造、
> 特性関数(フーリエ)との対応、SDE の生成作用素との関係を追加。
"""
        ),
    ]
    return assemble(
        "08. 応用 — 確率・信号・金融",
        FULL_LAYERS,
        "MGF とモーメント、割引現在価値(Gordon 成長と ROC)、待ち行列の入口で、$e^{-st}$ 重みの普遍性を見る。",
        body,
    )


BUILDERS = {
    "00_overview": nb00,
    "01_exponential_decay_complex_frequency": nb01,
    "02_definition_basic_properties": nb02,
    "03_inverse_laplace_partial_fractions": nb03,
    "04_solving_odes_with_laplace": nb04,
    "05_convolution_impulse_response_transfer_functions": nb05,
    "06_poles_zeros_stability": nb06,
    "07_control_systems_and_circuits": nb07,
    "08_applications_probability_signals_finance": nb08,
}


def main():
    os.makedirs(NB_DIR, exist_ok=True)
    for name, builder in BUILDERS.items():
        path = os.path.join(NB_DIR, name + ".ipynb")
        cells = builder()
        write(cells, path)
        print(f"wrote {path}  ({len(cells)} cells)")


if __name__ == "__main__":
    main()
