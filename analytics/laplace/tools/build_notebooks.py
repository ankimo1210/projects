"""Generate the Laplace-transform textbook notebooks deterministically.

Run from anywhere with the package importable:

    PYTHONPATH=src python tools/build_notebooks.py

Each notebook follows the book's fixed shape (Big Picture -> Problem -> Intuition
-> Visualization -> Definition -> Computation -> Invariant -> Failure Mode ->
Application -> Exercises -> Advanced Notes) with Basic / Applied / Advanced
layers. 00 stays a short map of the book; every other chapter is fully worked.
The generated .ipynb files are then executed in place so they carry outputs
(the book builds with execute_notebooks: off).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nbkit import code, md, write

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

from laplace_book import transforms, systems, circuits, plotting, datasets, widgets, discrete
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
下の4枚は、本書が1つの言語($e^{st}$)で束ねる現象たち。
"""
        ),
        code(
            r"""
tt = np.linspace(0, 8, 400)
panels = [
    ("growth:  s = +0.30", 0.30, 0.0),
    ("decay:  s = -0.50", -0.50, 0.0),
    ("oscillation:  s = +/- 3i", 0.0, 3.0),
    ("damped osc:  s = -0.35 +/- 3i", -0.35, 3.0),
]
fig, axes = plt.subplots(2, 2, figsize=(11, 6))
for ax, (lab, sig, om) in zip(axes.ravel(), panels):
    env = np.exp(sig * tt)
    ax.plot(tt, env * np.cos(om * tt), color=plotting.ACCENT)
    ax.plot(tt, env, "--", color="gray", lw=1)
    ax.plot(tt, -env, "--", color="gray", lw=1)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_title(lab)
    ax.set_xlabel("t")
    ax.grid(alpha=0.25)
fig.suptitle("Four phenomena, one language:  e^{st} with s = sigma + i*omega")
fig.tight_layout()
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
## 5b. 両側変換とフーリエの関係 (Advanced)

$s=\\sigma+i\\omega$ の **虚軸**($\\sigma=0$)に制限すると、ラプラス変換はフーリエ変換になる。
因果信号 $f(t)$($t\\ge0$、減衰)なら虚軸が収束域に入り、$|F(i\\omega)|$ がそのまま **振幅スペクトル**。
下では $f=e^{-2t}$ で $F(i\\omega)=1/(2+i\\omega)$ を数値確認する。両側変換($t<0$ も含む積分)は
フーリエを一般化した枠組みで、収束域の **帯** で表現が決まる。
"""
        ),
        code(
            r"""
omega = np.linspace(-15, 15, 200)
F_iw = numeric_laplace(lambda x: np.exp(-2 * x), 1j * omega)   # Laplace on the imaginary axis
F_exact = 1.0 / (2.0 + 1j * omega)                            # = Fourier transform of e^{-2t} u(t)
print("max |numeric F(iw) - 1/(2+iw)| =", np.max(np.abs(F_iw - F_exact)))

fig, ax = plt.subplots(figsize=(6.5, 4))
ax.plot(omega, np.abs(F_exact), color=plotting.ACCENT, label="|F(i omega)|  (amplitude spectrum)")
ax.set_xlabel("omega"); ax.set_ylabel("|F(i omega)|")
ax.set_title("Laplace on the imaginary axis = Fourier transform of e^{-2t} u(t)")
ax.grid(alpha=0.25); ax.legend()
plt.tight_layout()
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
## 6b. 部分分数 = モードの重ね合わせ (Applied)

部分分数分解は、$F(s)$ を **単純なモードの和** に割ること。各片の逆変換 $f_i(t)$ を足すと元の $f(t)$ に戻る。
$F(s)=\\dfrac{1}{s(s+1)(s+2)}$ を3つのモード(定数・$e^{-t}$・$e^{-2t}$)に分けて重ね合わせる。
"""
        ),
        code(
            r"""
Fsup = 1 / (s * (s + 1) * (s + 2))
parts = partial_fractions(Fsup).as_ordered_terms()    # the additive pieces
tt = np.linspace(0, 6, 400)
fig, ax = plt.subplots(figsize=(7, 4.2))
total = np.zeros_like(tt)
for term in parts:
    yk = transforms.as_function(sp.simplify(Linv(term)))(tt)
    yk = np.broadcast_to(yk, tt.shape).astype(float)  # constants -> full array
    total += yk
    ax.plot(tt, yk, "--", lw=1.2, label=f"mode: {sp.simplify(Linv(term))}")
ax.plot(tt, total, color="k", lw=2.5, label="sum = f(t)")
ax.set_title("partial fractions = superposition of modes")
ax.set_xlabel("t"); ax.set_ylabel("f(t)"); ax.legend(fontsize=8); ax.grid(alpha=0.25)
plt.tight_layout()
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
## 9b. 数値逆ラプラス変換 (Applied)

$F(s)$ が記号で扱えない・複雑なときは、$F(s)$ を **数値的に** 時間へ戻す方法がある。本書は2つを用意:

- **Gaver-Stehfest** (`inverse_laplace_stehfest`): 実軸上の $F(s)$ だけを使う簡便法。なめらかで減衰する
  $f(t)$ には強いが、振動には弱い。
- **Talbot** (`inverse_laplace_talbot`): 積分路を左半面へ変形する方法。振動・減衰のどちらにも強い。

既知ペアで比べ、「なぜ数値逆変換が難しいか」を体感する。
"""
        ),
        code(
            r"""
tt = np.linspace(0.3, 4, 200)

# Smooth/decaying target e^{-t}: both methods are accurate.
exact = np.exp(-tt)
y_st = transforms.inverse_laplace_stehfest(lambda S: 1 / (S + 1), tt)
y_tb = transforms.inverse_laplace_talbot(lambda S: 1 / (S + 1), tt)
print("e^{-t} :  Stehfest max err =", np.max(np.abs(y_st - exact)),
      "| Talbot max err =", np.max(np.abs(y_tb - exact)))

# Oscillatory target sin(3t): Stehfest struggles, Talbot stays accurate.
exact_o = np.sin(3 * tt)
o_st = transforms.inverse_laplace_stehfest(lambda S: 3 / (S**2 + 9), tt)
o_tb = transforms.inverse_laplace_talbot(lambda S: 3 / (S**2 + 9), tt)
print("sin(3t):  Stehfest max err =", np.max(np.abs(o_st - exact_o)),
      "| Talbot max err =", np.max(np.abs(o_tb - exact_o)))

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(tt, exact_o, "k", lw=2, label="exact sin(3t)")
ax.plot(tt, o_st, "--", label="Gaver-Stehfest (struggles on oscillation)")
ax.plot(tt, o_tb, ":", lw=2.5, label="Talbot (accurate)")
ax.set_xlabel("t"); ax.set_ylabel("f(t)"); ax.legend(); ax.grid(alpha=0.25)
ax.set_title("numerical inverse Laplace: oscillation is the hard case")
plt.tight_layout()
"""
        ),
        md(
            r"""
## 10b. ヘヴィサイドの展開定理 — 手計算と `scipy.signal.residue` を突き合わせる (Applied)

単純極 $p$ の係数は「その極を掛けて代入する」だけで取れます(cover-up 法):

$$
r = \lim_{s\to p}(s-p)F(s).
$$

$m$ 重極なら、掛けたあとに微分してから代入します。これがヘヴィサイドの展開定理です:

$$
r_j = \frac{1}{(m-j)!}\,\lim_{s\to p}\frac{d^{\,m-j}}{ds^{\,m-j}}\Big[(s-p)^m F(s)\Big],
\qquad j=1,\dots,m .
$$

$F(s)=\dfrac{s+3}{(s+1)(s+2)^2}$ で手を動かすと、$s=-1$ で $r=2$、
$s=-2$(2 重)で $\frac{d}{ds}\frac{s+3}{s+1}\big|_{-2}=-2$ と $\frac{s+3}{s+1}\big|_{-2}=-1$ なので

$$
F(s)=\frac{2}{s+1}-\frac{2}{s+2}-\frac{1}{(s+2)^2},
\qquad f(t)=2e^{-t}-2e^{-2t}-t\,e^{-2t}.
$$

これを `systems.partial_fraction_numeric`(中身は `scipy.signal.residue`)と突き合わせます。
"""
        ),
        code(
            r"""
# Heaviside cover-up by hand vs scipy.signal.residue, on a repeated pole.
from scipy import signal

num, den = [1.0, 3.0], [1.0, 5.0, 8.0, 4.0]        # (s+3) / ((s+1)(s+2)^2)
r, p, k = systems.partial_fraction_numeric(num, den)
print("scipy residues:", np.round(r, 6), " poles:", np.round(p, 6), " direct:", k)
print("by hand       : [ 2. -2. -1.]  at poles [-1. -2. -2.]")

# invres reassembles the pieces -- a round trip is the cleanest check of the split.
b_back, a_back = signal.invres(r, p, k)
print("round trip num:", np.round(b_back, 10), " den:", np.round(a_back, 10))

tt = np.linspace(0.05, 8, 300)                     # Talbot divides by t, so start past 0
f_hand = 2 * np.exp(-tt) - 2 * np.exp(-2 * tt) - tt * np.exp(-2 * tt)
f_num = transforms.inverse_laplace_talbot(lambda S: (S + 3) / ((S + 1) * (S + 2) ** 2), tt)
print("max |hand - numeric inverse| =", float(np.max(np.abs(f_hand - f_num))))

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(tt, f_hand, "k", lw=2, label="hand expansion: 2e^-t - 2e^-2t - t e^-2t")
ax.plot(tt[::8], f_num[::8], "o", ms=4, color=plotting.ACCENT, label="numerical inverse (Talbot)")
ax.set_xlabel("t"); ax.set_ylabel("f(t)"); ax.legend(); ax.grid(alpha=0.25)
ax.set_title("repeated pole: the t e^{-2t} term is what the derivative formula buys")
plt.tight_layout()
"""
        ),
        md(
            r"""
重根が $t\,e^{-2t}$ を生むところが要点です。単純極だけを見る cover-up 法では
この項が落ち、$t$ が大きいところで合わなくなります。

## 10c. むだ時間 $e^{-as}$ — 時間シフト則と、数値逆変換の限界 (Applied)

$$
\mathcal{L}\{f(t-a)\,u(t-a)\} = e^{-as}F(s) \qquad (a>0)
$$

なので、像に $e^{-as}$ が掛かっていたら **時間軸を $a$ だけ右へずらす** だけです。
輸送遅れ・通信遅延・測定の遅れなど、「入力が効き始めるまでに $a$ 秒かかる」系はすべてこの形。

一方これは数値逆変換にとって難しい入力です。$a$ で不連続に立ち上がるため、
有限個の点から復元する近似は、その段差をなまします。
"""
        ),
        code(
            r"""
# Dead time: e^{-as}F(s) is a pure shift in t. Exact answer is free; the
# numerical inverter has to earn it, and visibly smears the jump.
a = 2.0
t2 = np.linspace(0.05, 8, 200)
exact = np.where(t2 >= a, np.exp(-(t2 - a)), 0.0)
# Talbot is unusable here: its contour reaches deep into Re(s) < 0, where e^{-as} overflows.
approx = transforms.inverse_laplace_stehfest(lambda S: np.exp(-a * S) / (S + 1), t2)

err = np.abs(approx - exact)
print("max error overall               :", float(err.max()))
print("max error away from the jump    :", float(err[np.abs(t2 - a) > 1.0].max()))

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(t2, exact, "k", lw=2, label="exact: e^{-(t-a)} u(t-a)")
ax.plot(t2, approx, "--", lw=2, color=plotting.ACCENT, label="Gaver-Stehfest")
ax.axvline(a, color="#d62728", ls=":", lw=1.2, label=f"dead time a = {a}")
ax.set_xlabel("t"); ax.set_ylabel("f(t)"); ax.legend(); ax.grid(alpha=0.25)
ax.set_title("the shift theorem is exact; numerical inversion rounds the corner")
plt.tight_layout()
"""
        ),
        md(
            """
## 11. Exercises / Advanced Notes

- **演習**: $\\dfrac{2s+1}{s^2+s}$、$\\dfrac{1}{(s+2)^3}$、$\\dfrac{s}{s^2+4}$ を逆変換せよ。
- **Advanced**: 留数(residue)による逆変換 $f(t)=\\sum \\operatorname{Res}[F(s)e^{st}]$ をまとめ、
  §10b の重根の公式が留数の定義そのものであることを確かめよ。
- **Advanced**: むだ時間 $e^{-as}$ は有理関数ではないので、極・零点の言葉で直接扱えない。
  制御では Padé 近似 $e^{-as}\\approx\\frac{1-as/2}{1+as/2}$ で有理化する(07 章の位相余裕に効く)。
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
## 7b. 減衰比の幾何 (Applied)

上の $\\zeta$ は、極の位置の **幾何** そのもの。2次系の極は半径 $\\omega_n$ の円上にあり、負の実軸からの
角度 $\\theta$ が $\\cos\\theta=\\zeta$。$\\zeta$ が小さい(極が虚軸寄り)ほど振動的になる。
"""
        ),
        code(
            r"""
plotting.plot_damping_geometry(wn=1.5, zetas=(0.2, 0.5, 0.85, 1.0))
plt.tight_layout()
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
## 8b. 共振のアニメーション (Applied)

軽い減衰の2次系をいろいろな駆動周波数 $\\omega$ で揺らす。$\\omega$ が固有振動数 $\\omega_n$ に近づくと
応答振幅が跳ね上がる(**共振**)。各フレームのタイトルに $|H(i\\omega)|$ を表示。
"""
        ),
        code(
            r"""
from IPython.display import HTML

anim = plotting.animate_resonance(omega_n=3.0, zeta=0.05)
html = anim.to_jshtml(fps=8)
plt.close("all")   # close the figure so the inline backend does not also show a static frame
HTML(html)
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
## 4b. 畳み込みのアニメーション (Applied)

畳み込みの定番の見方:応答 $g$ を **反転して滑らせ**、各 $t$ での重なり(積 $f(\\tau)g(t-\\tau)$ の面積)が
$(f*g)(t)$。下段にその出力が描かれていく。
"""
        ),
        code(
            r"""
from IPython.display import HTML

dt = 0.05
tt = np.arange(0, 9, dt)
f = datasets.unit_step(tt, 0.5) - datasets.unit_step(tt, 1.5)   # rectangular pulse
g = np.exp(-2 * tt)                                             # exponential response
anim = plotting.animate_convolution(f, g, tt)
html = anim.to_jshtml(fps=8)
plt.close("all")
HTML(html)
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
## 7b. Routh-Hurwitz — 係数だけで安定判定 (Advanced)

極を数値で求めなくても、分母の **係数だけ** から右半面極の数が分かるのが Routh-Hurwitz 判定。
Routh 表の第1列の符号変化の回数 = 右半面極の数(0 なら安定)。`systems.routh_hurwitz` が判定・極数・表を返す。
"""
        ),
        code(
            r"""
for den in ([1, 6, 11, 6], [1, 1, 1, 6], [1, 6, 11, 106]):
    stable, n_rhp, _ = systems.routh_hurwitz(den)
    truth = int(np.sum(np.roots(den).real > 1e-9))   # cross-check against the actual roots
    print(f"den={den}:  Routh n_rhp={n_rhp} (roots say {truth})  ->  {'stable' if stable else 'unstable'}")
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
## 8b. 安定境界をまたぐアニメーション (Applied)

共役な極対の実部 $\\sigma$ を負から正へ動かすと、極が虚軸を横切り、応答が **減衰 → 持続 → 発散** と
変わる。安定性の境界(虚軸)を目で追う。
"""
        ),
        code(
            r"""
from IPython.display import HTML

anim = plotting.animate_pole_crossing(omega=3.0)
html = anim.to_jshtml(fps=8)
plt.close("all")
HTML(html)
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
- **Advanced**: `systems.routh_hurwitz`(§7b)で $1/(s^2+bs+1)$ を判定し、$b<0$ で不安定になることを確かめよ。
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
## 5b. 根軌跡 — ゲインで閉ループ極が描く軌跡

ループゲイン $k$ を $0\\to\\infty$ と動かすと、閉ループ極(特性方程式 $D_G(s)+k\\,N_G(s)=0$ の根)が
$s$ 平面に **軌跡** を描く。$k=0$ で開ループ極(×)から出発し、増やすと開ループ零点(○)や無限遠へ向かう。
古典例 $G(s)=1/(s(s+1))$ では2極が $-0.5$ で合流し、虚軸と平行に上下へ抜ける。
"""
        ),
        code(
            r"""
G = systems.tf([1.0], [1.0, 1.0, 0.0])      # 1 / (s(s+1))
plotting.plot_root_locus(G, np.linspace(0, 12, 200))
plt.tight_layout()

# A 3-pole plant loses stability past a finite gain (a branch crosses into the RHP).
G3 = systems.tf([1.0], np.poly([-1.0, -2.0, -3.0]))   # 1/((s+1)(s+2)(s+3))
ks = np.arange(0, 120, 5)
_, loc3 = systems.root_locus(G3, ks)
max_re = np.array([r.real.max() for r in loc3])
kcross = ks[np.argmax(max_re > 0)]
print(f"3-pole plant: closed loop becomes unstable around k = {kcross}  (Routh bound: k < 60)")
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
## 6b. 安定余裕と Nyquist 線図 (Applied)

開ループ $L(s)$ が単位負帰還で安定かは、**ゲイン余裕**(あと何倍ゲインを上げられるか)と
**位相余裕**(あと何度位相が遅れてよいか)で測る。`systems.gain_phase_margin` が両者を返す。
**Nyquist 線図** は $L(j\\omega)$ の軌跡で、点 $-1$ の周りの回り方が閉ループ安定性を決める。
"""
        ),
        code(
            r"""
G3 = systems.tf([1.0], np.poly([-1.0, -2.0, -3.0]))   # 1/((s+1)(s+2)(s+3))
m = systems.gain_phase_margin(G3)
print(f"gain  margin = {m['gain_margin']:.1f} x      at w = {m['wpc']:.2f}")
print(f"phase margin = {m['phase_margin_deg']:.1f} deg   at w = {m['wgc']:.2f}")
# the gain margin ~60 matches the instability gain from the root locus (section 5b).
plotting.plot_nyquist(G3, w=np.logspace(-2, 2, 1500))
plt.tight_layout()
"""
        ),
        md(
            """
## 6c. PI 制御で定常偏差を消す (Applied)

比例(P)制御だけだと一定の定常偏差が残る。**積分項**(PI 制御 $K(s)=K_p+K_i/s$)を足すと、入力の極 $s=0$
により閉ループの DC ゲインが 1 になり、ステップ目標への **定常偏差がゼロ** になる(最終値定理)。
"""
        ),
        code(
            r"""
plant = systems.tf([1.0], [2.0, 1.0])     # 1/(2s+1)
tt = np.linspace(0, 25, 600)
fig, ax = plt.subplots(figsize=(7, 4.2))
for label, K in [("P (Kp=2)", systems.pid(kp=2.0)), ("PI (Kp=2,Ki=3)", systems.pid(kp=2.0, ki=3.0))]:
    closed = systems.feedback(systems.series(plant, K))
    ax.plot(tt, systems.step_response(closed, tt),
            label=f"{label}: DC gain = {systems.dc_gain(closed):.3f}")
ax.axhline(1.0, color="gray", ls=":", lw=1)
ax.set_title("P leaves a steady-state error; PI removes it")
ax.set_xlabel("t"); ax.set_ylabel("output"); ax.legend(); ax.grid(alpha=0.25)
plt.tight_layout()
"""
        ),
        md(
            r"""
## 6d. 実装できる PID — 微分にフィルタを付ける (Applied)

教科書の PID $K(s)=K_p+\dfrac{K_i}{s}+K_d s$ は、そのままでは **実装できません**。
分子の次数が分母より高い(プロパーでない)ため、物理的に実現できず、
何より $K_d s$ の周波数応答は $|K_d\omega|$ で **高周波を無限に増幅** します。
測定ノイズはたいてい高周波なので、これは致命的です。

実務では微分に 1 次のローパスを噛ませます:

$$
K(s) = K_p + \frac{K_i}{s} + \frac{K_d N s}{s + N}.
$$

$N$ が微分の効く上限周波数。$N\to\infty$ で理想の微分に戻り、同時にノイズ増幅も戻ってきます。
"""
        ),
        code(
            r"""
# Filtered derivative: N is the knob between "ideal D" and "quiet D".
def filtered_pid(kp, ki, kd, N):
    # kp + ki/s + kd*N*s/(s+N), put over the common denominator s(s+N).
    num = np.polyadd(np.polyadd(np.polymul([kp], [1.0, N, 0.0]),
                                np.polymul([ki], [1.0, N])),
                     np.polymul([kd * N, 0.0], [1.0, 0.0]))
    return systems.tf(num, [1.0, N, 0.0])

kp, ki, kd = 2.0, 1.0, 0.5
w = np.logspace(-1, 3, 400)
fig, (axm, axn) = plt.subplots(1, 2, figsize=(11.5, 4.4))
for N, color in [(5.0, "#1f77b4"), (50.0, "#2ca02c"), (500.0, "#d62728")]:
    _, mag, _ = systems.bode(filtered_pid(kp, ki, kd, N), w=w)
    axm.semilogx(w, mag, color=color, label=f"N = {N:.0f}")
axm.semilogx(w, 20 * np.log10(kd * w), "k--", lw=1, label="ideal K_d s")
axm.set_xlabel("w [rad/s]"); axm.set_ylabel("|K(jw)| [dB]"); axm.grid(alpha=0.25, which="both")
axm.legend(fontsize=8); axm.set_title("larger N -> closer to the ideal derivative")

# What that costs on a noisy measurement.
tt = np.linspace(0, 6, 1201)
rng = np.random.default_rng(0)
u = np.sin(2 * tt) + 0.02 * rng.standard_normal(tt.size)
for N, color in [(5.0, "#1f77b4"), (500.0, "#d62728")]:
    y = systems.forced_response(filtered_pid(kp, ki, kd, N), u, tt)
    axn.plot(tt, y, color=color, lw=1.1, label=f"N = {N:.0f}, peak |y| = {np.abs(y).max():.2f}")
axn.set_xlabel("t"); axn.set_ylabel("controller output"); axn.grid(alpha=0.25)
axn.legend(fontsize=8); axn.set_title("2% measurement noise, amplified by the D term")
plt.tight_layout()
"""
        ),
        md(
            r"""
$N$ を 5 から 500 に上げると、正弦波の追従は変わらないのに出力のピークだけが跳ね上がります。
**微分ゲインの上限 $N$ は、ノイズ増幅の上限そのもの** です。

## 6e. 状態空間表現 — 同じ系のもう一つの書き方 (Advanced)

伝達関数 $G(s)=\dfrac{b(s)}{a(s)}$ は、1 階の連立系

$$
\dot{\mathbf{x}} = A\mathbf{x} + B u, \qquad y = C\mathbf{x} + D u
$$

に書き直せます($\mathbf{x}$ は内部状態)。両者は同じ系の別表現で、
**$A$ の固有値 = 伝達関数の極**。ODE 書 03 章の $\dot{\mathbf{x}}=A\mathbf{x}$ と、
本書の極が同じものだったことがここで分かります。
"""
        ),
        code(
            r"""
# Same system, two descriptions: eig(A) must reproduce the poles.
from scipy import signal

plant = systems.tf([1.0], [2.0, 1.0])                      # 1/(2s+1)
closed = systems.feedback(systems.series(plant, systems.pid(kp=2.0, ki=3.0)))
A, B, C, D = signal.tf2ss(closed.num, closed.den)
print("A =\n", np.round(A, 4))
print("eig(A) :", np.round(np.linalg.eigvals(A), 6))
print("poles  :", np.round(closed.poles, 6))

tt = np.linspace(0, 12, 400)
y_tf = systems.step_response(closed, tt)
_, y_ss = signal.step((A, B, C, D), T=tt)
print("max |transfer function - state space| =", float(np.max(np.abs(y_tf - y_ss))))
"""
        ),
        md(
            r"""
状態空間が要るのは、**多入力多出力**、**内部状態の推定(オブザーバ)**、
**最適制御(LQR)** に進むときです。ODE 書 09 章の `lqr` / `place_poles` はこの表現の上に立っています。

## 6f. 離散化 — コントローラを計算機に載せる (Advanced)

実装はサンプル周期 $T$ ごとに走る計算機の上です。連続の $K(s)$ を離散の $K(z)$ に直す必要があり、
その写像が 11 章の $z=e^{sT}$ です。閉ループ極も同じ規則で移ります:

$$
s\ \text{平面の極}\ p \ \longrightarrow\ z\ \text{平面の極}\ e^{pT}.
$$

$T$ を大きくすると極は原点へ寄って一見「速く」見えますが、
サンプル間の情報が捨てられるぶん実際の応答は荒くなります。
"""
        ),
        code(
            r"""
# Zero-order hold: discrete poles land exactly on exp(p T).
for T in (0.05, 0.5, 1.5):
    num_d, den_d, _ = signal.cont2discrete((closed.num, closed.den), T, method="zoh")
    # trim the leading zero cont2discrete leaves in the numerator (it is a no-op
    # coefficient, but scipy warns about the conditioning if it is kept)
    dz = signal.TransferFunction(np.trim_zeros(np.squeeze(num_d), "f"), den_d, dt=T)
    print(f"T = {T:4.2f}:  |z| = {np.round(np.abs(dz.poles), 4)}"
          f"   |exp(pT)| = {np.round(np.abs(np.exp(closed.poles * T)), 4)}"
          f"   stable = {discrete.is_stable_discrete(dz)}")

fig, ax = plt.subplots(figsize=(7, 4.2))
ax.plot(tt, y_tf, "k", lw=2, label="continuous")
for T, color in [(0.5, "#2ca02c"), (1.5, "#d62728")]:
    num_d, den_d, _ = signal.cont2discrete((closed.num, closed.den), T, method="zoh")
    dz = signal.TransferFunction(np.trim_zeros(np.squeeze(num_d), "f"), den_d, dt=T)
    k_idx, y_d = discrete.discrete_step_response(dz, n=int(12 / T))
    ax.step(np.asarray(k_idx).ravel() * T, np.asarray(y_d).ravel(), where="post",
            color=color, lw=1.4, label=f"sampled, T = {T}")
ax.axhline(1.0, color="gray", ls=":", lw=1)
ax.set_xlabel("t"); ax.set_ylabel("output"); ax.legend(fontsize=8); ax.grid(alpha=0.25)
ax.set_title("the same loop, sampled: coarse T costs fidelity, not stability here")
plt.tight_layout()
"""
        ),
        md(
            """
## 7〜11. Application / Exercises / Advanced Notes

- **応用**: アンチエイリアスフィルタ、サスペンション、サーボ位置決め、温度制御。
- **演習(Basic)**: RC で時定数を半分にするには $R,C$ をどうする?
- **演習(Applied)**: `systems.feedback` で $G=1/(s(s+1))$ の閉ループ極を $K$ について追え。
- **Advanced**: PI 制御が定常偏差を消す理由(§6c)を、最終値定理 $\\lim_{s\\to0}sE(s)$ から示せ。
- **Advanced**: §6d の $N$ を上げていくと、閉ループの位相余裕(§6b)はどう動くか。
  ノイズ増幅と安定余裕のどちらが先に問題になるかを、対象プラント次第で論じよ。
- **Advanced**: §6f の離散化を `method="bilinear"` に替えると極の写り方がどう変わるか(11 章 §7d)。

> 根軌跡は §5b、安定余裕/Nyquist は §6b、PI は §6c、フィルタ付き微分・状態空間・離散化は
> §6d〜§6f で実装済み。むだ時間の Padé 近似だけは 03 章 §10c の Advanced に置いてある。
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
## 2b. 指数分布とそのモーメント (Applied)

指数分布 $\\lambda e^{-\\lambda x}$ の平均は $1/\\lambda$。$\\lambda$ を変えて密度と平均を描く。
"""
        ),
        code(
            r"""
x = np.linspace(0, 6, 400)
fig, ax = plt.subplots(figsize=(6.5, 4))
for lam_v in [0.5, 1.0, 2.0]:
    ax.plot(x, lam_v * np.exp(-lam_v * x), label=f"lambda={lam_v}: mean=1/lambda={1 / lam_v:.2f}")
    ax.axvline(1 / lam_v, color="gray", ls=":", lw=1)
ax.set_title("Exponential pdf  lambda e^{-lambda x}  (mean = 1/lambda)")
ax.set_xlabel("x"); ax.set_ylabel("density"); ax.legend(); ax.grid(alpha=0.25)
plt.tight_layout()
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
## 3b. PV は r → g で発散する (Applied)

成長率 $g$ を固定して割引率 $r$ を動かすと、$PV=c_0/(r-g)$ は $r\\to g^+$ で発散する。
発散の境界 $r=g$ が、ちょうどラプラス変換の **収束域(ROC)の縁** にあたる。
"""
        ),
        code(
            r"""
g_fixed, c0v = 0.03, 100.0
r_vals = np.linspace(0.035, 0.15, 300)
fig, ax = plt.subplots(figsize=(6.5, 4))
ax.plot(r_vals, c0v / (r_vals - g_fixed), color=plotting.ACCENT)
ax.axvline(g_fixed, color="#d62728", ls="--", label=f"r = g = {g_fixed} (ROC boundary)")
ax.set_ylim(0, 8000)
ax.set_title("Gordon growth: PV = c0/(r-g) blows up as r -> g")
ax.set_xlabel("discount rate r"); ax.set_ylabel("present value"); ax.legend(); ax.grid(alpha=0.25)
plt.tight_layout()
"""
        ),
        md(
            r"""
## 4. 信号処理 / 待ち行列

- **信号処理**: フィルタは畳み込み = $s$ での積(05 章)。連続系は $s$、離散系は $z$ 変換へ拡張(11 章)。
- **待ち行列**: 待ち時間分布は **ラプラス–スティルチェス変換(LST)** で扱います。以下で M/M/1 を実測します。

## 4b. ラプラス–スティルチェス変換と M/M/1 の待ち時間 (Applied)

分布関数 $F_X$ に対する LST は

$$
\tilde{F}_X(s) = \int_{[0,\infty)} e^{-sx}\,dF_X(x) = \mathbb{E}\!\left[e^{-sX}\right].
$$

密度がある部分では通常のラプラス変換と一致し、**質量点も同じ式で拾える** のが違いです。
待ち時間は「まったく待たない確率」という質量点を $0$ に持つので、この形が要ります。

到着率 $\lambda$、サービス率 $\mu$、利用率 $\rho=\lambda/\mu<1$ の M/M/1(FCFS)では、
待ち時間 $W$ は確率 $1-\rho$ で $0$、残りが率 $\mu-\lambda$ の指数分布になり

$$
\mathbb{E}\!\left[e^{-sW}\right] = (1-\rho) + \rho\,\frac{\mu-\lambda}{s+\mu-\lambda},
\qquad \mathbb{E}[W] = \frac{\rho}{\mu-\lambda}.
$$

Lindley の再帰 $W_{k+1}=\max(0,\,W_k+S_k-A_{k+1})$ で待ち行列を回し、
シミュレーションの $\mathbb{E}[e^{-sW}]$ と突き合わせます。
"""
        ),
        code(
            r"""
# M/M/1 by Lindley's recursion; the LST is just a sample mean of exp(-sW).
lam, mu = 0.7, 1.0
rho = lam / mu
rng = np.random.default_rng(0)
n = 200_000
inter = rng.exponential(1 / lam, n)      # interarrival times
serve = rng.exponential(1 / mu, n)       # service times

W = np.zeros(n)
for k in range(1, n):
    W[k] = max(0.0, W[k - 1] + serve[k - 1] - inter[k])
W = W[n // 10:]                          # discard the burn-in

print(f"P(W = 0) : simulated {np.mean(W == 0):.4f}   theory {1 - rho:.4f}")
print(f"E[W]     : simulated {W.mean():.4f}   theory {rho / (mu - lam):.4f}")
print("\n   s     E[e^-sW] simulated      theory")
for sv in (0.2, 0.5, 1.0, 2.0):
    theory = (1 - rho) + rho * (mu - lam) / (sv + mu - lam)
    print(f"{sv:5.1f}   {np.mean(np.exp(-sv * W)):18.5f} {theory:11.5f}")
"""
        ),
        code(
            r"""
# The mass at 0 is what forces the Stieltjes form: the CDF jumps there.
fig, (axh, axl) = plt.subplots(1, 2, figsize=(11.5, 4.2))
axh.hist(W[W > 0], bins=60, density=True, alpha=0.55, color=plotting.ACCENT,
         label=f"simulated W | W > 0")
wg = np.linspace(0, np.quantile(W[W > 0], 0.995), 300)
axh.plot(wg, (mu - lam) * np.exp(-(mu - lam) * wg), "k", lw=2,
         label="exponential(mu - lam)")
axh.set_xlabel("waiting time"); axh.set_ylabel("density"); axh.legend(fontsize=8)
axh.set_title(f"P(W = 0) = {np.mean(W == 0):.3f} sits outside this histogram")

sv = np.linspace(0.05, 3.0, 60)
axl.plot(sv, [np.mean(np.exp(-x * W)) for x in sv], "o", ms=3.5, color=plotting.ACCENT,
         label="simulated E[e^-sW]")
axl.plot(sv, (1 - rho) + rho * (mu - lam) / (sv + mu - lam), "k", lw=2, label="LST formula")
axl.axhline(1 - rho, color="#d62728", ls=":", lw=1.2, label=f"s -> inf limit = 1 - rho = {1 - rho:.2f}")
axl.set_xlabel("s"); axl.set_ylabel("E[e^-sW]"); axl.legend(fontsize=8); axl.grid(alpha=0.25)
axl.set_title("the LST does not decay to 0: that residue IS the atom at 0")
plt.tight_layout()
"""
        ),
        md(
            r"""
$s\to\infty$ で LST が $0$ ではなく $1-\rho$ に落ち着くところが、通常のラプラス変換との違いです。
**密度だけなら $0$ に減衰するはずの量が残る = 原点に質量がある**。これを一つの式で扱えるのが LST の値打ちです。

## 4c. 期間構造 — 債券価格は現金流の LST (Applied)

割引率が一定 $r$ なら、時点 $T_i$ の現金 $c_i$ の現在価値は $c_i e^{-rT_i}$。合計すると

$$
P(r) = \sum_i c_i e^{-rT_i} = \int_{[0,\infty)} e^{-rT}\,dC(T)
$$

で、これは現金流の測度 $C$ の LST そのもの(離散配当は質量点)。
すると 2 節の「MGF を微分するとモーメントが出る」がそのまま使えて、

$$
-\frac{1}{P}\frac{dP}{dr} = \frac{\sum_i T_i\,c_i e^{-rT_i}}{\sum_i c_i e^{-rT_i}}
$$

は **割引現金流を重みにした平均回収時間** — 金融でいう **デュレーション** です。
「変換の微分 = 1 次モーメント」が、そのまま金利感応度の指標になっています。
"""
        ),
        code(
            r"""
# Duration two ways: as a weighted mean time, and as -dP/dr / P.
coupon, face, r0 = 3.0, 100.0, 0.04
times = np.arange(1.0, 11.0)
cash = np.full(times.size, coupon)
cash[-1] += face

def price(r):
    return float(np.sum(cash * np.exp(-r * times)))

weights = cash * np.exp(-r0 * times) / price(r0)
eps = 1e-6
print("price P(r)                    :", round(price(r0), 6))
print("duration as weighted mean time:", round(float(np.sum(times * weights)), 6))
print("duration as -(dP/dr)/P        :", round(-(price(r0 + eps) - price(r0 - eps)) / (2 * eps) / price(r0), 6))

fig, (axw, axp) = plt.subplots(1, 2, figsize=(11.5, 4.0))
axw.bar(times, weights, width=0.5, color=plotting.ACCENT)
axw.axvline(float(np.sum(times * weights)), color="#d62728", ls="--", label="duration")
axw.set_xlabel("T (years)"); axw.set_ylabel("weight c e^{-rT} / P"); axw.legend(fontsize=8)
axw.set_title("the cash-flow measure, discounted")
rr = np.linspace(0.0, 0.15, 200)
axp.plot(rr, [price(x) for x in rr], color=plotting.ACCENT)
axp.plot(r0, price(r0), "o", color="#d62728")
axp.set_xlabel("discount rate r"); axp.set_ylabel("price"); axp.grid(alpha=0.25)
axp.set_title("price is the transform, evaluated at s = r")
plt.tight_layout()
"""
        ),
        md(
            r"""
金利が期間ごとに違う(期間構造 $r(T)$)場合も形は変わりません。$e^{-rT}$ を割引因子
$D(T)=\exp\!\big(-\int_0^T f(u)\,du\big)$ に替えるだけで、価格は同じ「重み付き和」です。
変わるのは重みであって、構造ではありません。

## 4d. 特性関数との対応 — 虚軸に乗せるとフーリエになる (Advanced)

密度 $f_X$ のラプラス変換 $F(s)=\mathbb{E}[e^{-sX}]$ に $s=-iu$ を代入すると

$$
F(-iu) = \mathbb{E}\!\left[e^{iuX}\right] = \varphi_X(u)
$$

で、確率論の **特性関数** になります。01 章で見た「$s=\sigma+i\omega$ の虚軸がフーリエ」が、
確率の言葉ではそのまま「ラプラス変換の虚軸が特性関数」。
指数分布 $\mathrm{Exp}(\lambda)$ なら $F(s)=\lambda/(s+\lambda)$ なので $\varphi(u)=\lambda/(\lambda-iu)$ です。
"""
        ),
        code(
            r"""
# phi(u) = F(-i u): check the analytic continuation numerically.
from scipy import integrate

lam_e = 1.5
print("   u        quadrature              lam/(lam - i u)")
for uu in (0.5, 1.0, 2.0):
    re, _ = integrate.quad(lambda x: np.cos(uu * x) * lam_e * np.exp(-lam_e * x), 0, 60)
    im, _ = integrate.quad(lambda x: np.sin(uu * x) * lam_e * np.exp(-lam_e * x), 0, 60)
    print(f"{uu:5.1f}   {re + 1j * im:>22.6f}   {lam_e / (lam_e - 1j * uu):>18.6f}")

uu = np.linspace(-8, 8, 400)
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(uu, (lam_e / (lam_e - 1j * uu)).real, color=plotting.ACCENT, label="Re phi(u)")
ax.plot(uu, (lam_e / (lam_e - 1j * uu)).imag, color="#d62728", label="Im phi(u)")
ax.set_xlabel("u"); ax.set_ylabel("characteristic function"); ax.legend(); ax.grid(alpha=0.25)
ax.set_title("Exp(1.5): the Laplace transform read along the imaginary axis")
plt.tight_layout()
"""
        ),
        md(
            r"""
> **本書の範囲外**: SDE の生成作用素($\mathcal{L}u = b u' + \tfrac{1}{2}\sigma^2 u''$)と
> レゾルベント $(\alpha-\mathcal{L})^{-1}=\int_0^\infty e^{-\alpha t}P_t\,dt$ の関係は、
> 見た目のとおり「ラプラス変換の作用素版」ですが、確率過程論の準備が要ります。
> 本書では踏み込まず、[`../differential_equation/sde-book`](../differential_equation/sde-book/) に譲ります。
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
## 6. Exercises / Advanced Notes

- **Basic**: 一定キャッシュフロー $c$ の永久債 $PV=c/r$ を積分で確かめよ。
- **Applied**: ガンマ分布 $f_X=\\frac{\\lambda^k x^{k-1}e^{-\\lambda x}}{(k-1)!}$ のラプラス変換 $\\big(\\frac{\\lambda}{s+\\lambda}\\big)^k$ を導け。
- **Advanced**: 合成分布(独立和)のラプラス変換が積になることを、畳み込み定理(05 章)から説明せよ。

> ラプラス–スティルチェス変換と M/M/1 は §4b、債券価格と期間構造は §4c、
> 特性関数との対応は §4d に実装済み。SDE の生成作用素だけは範囲外(§4d 末尾)。
"""
        ),
    ]
    return assemble(
        "08. 応用 — 確率・信号・金融",
        FULL_LAYERS,
        "MGF とモーメント、割引現在価値(Gordon 成長と ROC)、待ち行列の入口で、$e^{-st}$ 重みの普遍性を見る。",
        body,
    )


# =========================================================================== #
# 09 — Capstone: one system through three lenses  (FULL)
# =========================================================================== #
def nb09():
    body = [
        md(
            """
## 1. Big Picture — 1つの系を3つのレンズで

これまでの道具を1つの系で束ねる。質量-バネ-ダンパ(ステップ強制・初期静止)

$$ \\ddot y + 3\\dot y + 2y = 2\\,u(t), \\qquad y(0)=\\dot y(0)=0 $$

を、(1) ODE をラプラスで解く、(2) インパルス応答と畳み込み、(3) 極と安定性、の3レンズで見る。
**3つとも同じ $y(t)$** に行き着くことを確かめる。
"""
        ),
        md(
            """
## 2. Lens 1 — ODE をラプラスで代数化

微分則で $s$ 領域へ移すと $Y(s)=\\dfrac{2}{s(s^2+3s+2)}=\\dfrac{2}{s(s+1)(s+2)}$。部分分数 → 逆変換。
"""
        ),
        code(
            r"""
Y = 2 / (s * (s + 1) * (s + 2))
display(partial_fractions(Y))          # 1/s - 2/(s+1) + 1/(s+2)
y1 = sp.simplify(Linv(Y))
display(y1)                            # 1 - 2 e^{-t} + e^{-2t}
"""
        ),
        md(
            """
## 3. Lens 2 — インパルス応答と畳み込み

伝達関数 $H(s)=\\dfrac{2}{s^2+3s+2}$、インパルス応答 $h=\\mathcal{L}^{-1}\\{H\\}=2(e^{-t}-e^{-2t})$。
ステップ応答は $h$ とステップの畳み込み。Lens 1 と一致するはず。
"""
        ),
        code(
            r"""
dt = 0.005
tt = np.arange(0, 12, dt)
H = systems.tf([2.0], [1.0, 3.0, 2.0])                  # 2 / (s^2 + 3s + 2)
h = systems.impulse_response(H, tt)                     # 2(e^{-t} - e^{-2t})
step_conv = systems.convolve(h, np.ones_like(tt), dt)   # h * u
step_lsim = systems.step_response(H, tt)
y1fun = transforms.as_function(y1)
print("Lens1 (Laplace) vs Lens2 (h*u)  max err:", np.max(np.abs(y1fun(tt) - step_conv)))
print("Lens2  lsim     vs Lens2 (h*u)  max err:", np.max(np.abs(step_lsim - step_conv)))
"""
        ),
        md(
            """
## 4. Lens 3 — 極と安定性(過渡 + 定常)

$H$ の極は $-1,-2$(ともに左半面 → 安定)。応答は **過渡**(極由来、$e^{-t},e^{-2t}$ で消える)と
**定常**(入力の極 $s=0$ 由来、DC ゲイン $=1$)の和。
"""
        ),
        code(
            r"""
print("poles:", systems.poles(H), "->", systems.classify_stability(H))
print("steady-state value (DC gain):", systems.dc_gain(H))
print("transient part  y(t) - 1 =", sp.simplify(y1 - 1))   # -2 e^{-t} + e^{-2t} -> 0
"""
        ),
        md(
            """
## 5. 3つのレンズ、ひとつの答え
"""
        ),
        code(
            r"""
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
plotting.plot_s_plane(poles=systems.poles(H), ax=axes[0], title="poles of H (both LHP -> stable)")
plotting.plot_time_responses(
    tt, [y1fun(tt), step_conv, step_lsim],
    labels=["Lens1: Laplace ODE", "Lens2: h * u", "Lens2: lsim"],
    ax=axes[1], title="three lenses, one answer", ylabel="y(t)")
axes[1].axhline(1.0, color="gray", ls=":", lw=1)
plt.tight_layout()
"""
        ),
        md(
            """
## 6. 何が違うのか — レンズごとの問い

| レンズ | 答える問い | 道具(章) |
|---|---|---|
| ODE/ラプラス | 解の **時間の式** は? | 微分則・部分分数・逆変換(02–04) |
| 畳み込み/インパルス応答 | 任意入力への **応答** は? | $h$, $Y=HX$(05) |
| 極・安定性 | **形・安定性・速さ** は? | 極の位置(06) |

同じ $y(t)=1-2e^{-t}+e^{-2t}$ を3つの角度から読んだ。これがラプラス変換の統一力。
"""
        ),
        md(
            """
## 7. Exercises / Advanced

- **Basic**: 同じ系を $y(0)=1,\\ \\dot y(0)=0$ で解き直し、零入力応答が加わることを3レンズで確認せよ。
- **Applied**: ダンピングを $3\\to1$ に下げ(underdamped)、極が複素になり応答が振動することを示せ。
- **Advanced**: 入力を $u(t)=\\sin\\omega t$ にし、定常応答の振幅が $|H(i\\omega)|$ で決まることを確かめよ。
"""
        ),
    ]
    return assemble(
        "09. キャップストーン — 1つの系を3つのレンズで",
        FULL_LAYERS,
        "1つの2次系を ODE/ラプラス・畳み込み・極の3視点で解き、同じ $y(t)$ に到達することを確かめる。",
        body,
    )


# =========================================================================== #
# 10 — Exercise solutions  (appendix)
# =========================================================================== #
def nb10():
    body = [
        md(
            """
## このノートについて

01〜08 章の演習の **解答例**。各章 1 セルで代表的な問いを `laplace_book` と SymPy で解く。
"""
        ),
        md("## 01 章 — 半減期と複素周波数"),
        code(
            r"""
# Half-life: e^{sigma*T}=1/2  ->  sigma = -ln2 / T_half
T_half = 5.0
sigma = -np.log(2) / T_half
print("sigma =", sigma, " check e^{sigma*T_half} =", np.exp(sigma * T_half))   # 0.5
"""
        ),
        md("## 02 章 — 線形性・周波数シフト・初期値定理"),
        code(
            r"""
display(L(3 - 2 * sp.exp(-t)))               # 3/s - 2/(s+1)
display(L(sp.exp(-t) * sp.cos(3 * t)))       # (s+1)/((s+1)^2 + 9)
w = sp.symbols("omega", positive=True)
print("initial value of cos(wt):", sp.limit(s * L(sp.cos(w * t)), s, sp.oo))   # 1
"""
        ),
        md("## 03 章 — 逆変換(単純極・重根・複素極)"),
        code(
            r"""
for F in [(2 * s + 1) / (s**2 + s), 1 / (s + 2) ** 3, s / (s**2 + 4)]:
    display(sp.simplify(Linv(F)))            # 1 + e^{-t};  t^2 e^{-2t}/2;  cos(2t)
"""
        ),
        md("## 04 章 — ODE と共振"),
        code(
            r"""
display(Linv(3 / (s + 2)))                   # y'+2y=0, y(0)=3 -> 3 e^{-2t}
# y'' + y = sin t, zero IC: Y = 1/(s^2+1)^2 -> resonance (amplitude grows with t)
display(sp.simplify(Linv(1 / (s**2 + 1) ** 2)))   # (sin t - t cos t)/2
"""
        ),
        md("## 05 章 — インパルス応答とステップ応答"),
        code(
            r"""
display(Linv(1 / (s + 2)))                       # impulse response: e^{-2t}
display(sp.simplify(Linv(1 / (s * (s + 2)))))    # step response: (1 - e^{-2t})/2
"""
        ),
        md("## 06 章 — 極・安定性と零点の役割"),
        code(
            r"""
H = systems.tf([1.0], [1.0, 4.0, 13.0])       # 1/((s+2)^2 + 9): poles -2 +/- 3i
print("poles:", systems.poles(H))
H2 = systems.tf([1.0, 1.0], [1.0, 4.0, 13.0]) # same poles, extra zero at -1
print("stability without/with zero:", systems.classify_stability(H), systems.classify_stability(H2))
"""
        ),
        md("## 07 章 — 時定数とフィードバックの定常偏差"),
        code(
            r"""
# Halving tau = RC moves the pole left (faster response).
print("tau=1.0ms pole:", systems.poles(circuits.rc_lowpass(1000.0, 1e-6)))
print("tau=0.5ms pole:", systems.poles(circuits.rc_lowpass(500.0, 1e-6)))
# PI control K(s)=2 + 1/s on plant 1/(s+1): closed-loop DC gain = 1 -> zero steady-state step error.
plant = systems.tf([1.0], [1.0, 1.0])
Kpi = systems.tf([2.0, 1.0], [1.0, 0.0])
closed = systems.feedback(systems.series(plant, Kpi))
print("PI closed-loop DC gain:", systems.dc_gain(closed), "-> steady-state step error = 0")
"""
        ),
        md("## 08 章 — 永久債・ガンマ分布"),
        code(
            r"""
c0, r = sp.symbols("c0 r", positive=True)
display(sp.laplace_transform(c0, t, r, noconds=True))   # c0/r  (perpetuity present value)
lam = sp.symbols("lambda", positive=True)
display(L(lam**2 * t * sp.exp(-lam * t)))               # lambda^2/(s+lambda)^2  (Gamma, k=2)
"""
        ),
        md(
            """
> すべて記号/数値で再現可能。詳しい解説は各章本文を参照。
"""
        ),
    ]
    return assemble(
        "10. 演習解答",
        [("—", "01〜08 章 演習の解答例")],
        "各章の演習を `laplace_book` と SymPy で解いた解答集(付録)。",
        body,
    )


# =========================================================================== #
# 11 — z-transform: the discrete bridge  (extension)
# =========================================================================== #
def nb11():
    body = [
        md(
            """
## 1. Big Picture — サンプリングと z 変換

連続信号を一定間隔 $T$ で **標本化** すると、時間は数列 $x[k]=x(kT)$ になる。連続のラプラス変換に
対応するのが **z 変換**

$$ X(z) = \\sum_{k=0}^{\\infty} x[k]\\, z^{-k}, $$

そして両者は $z=e^{sT}$ で結ばれる。本章はラプラスから離散の世界への橋渡し(入口)。
"""
        ),
        md(
            """
## 2. Problem / 3. Intuition

離散の漸化式(差分方程式)も $z$ 領域では代数になる(微分が掛け算になったのと同じ構図)。
$z^{-1}$ は **1サンプルの遅延**。連続の固有関数 $e^{st}$ の役を、離散では $z^k=e^{skT}$ が担う。
"""
        ),
        md(
            """
## 4. Definition と 幾何級数ペア

最重要ペアは幾何数列 $a^k$:

$$ \\sum_{k=0}^{\\infty} a^k z^{-k} = \\frac{z}{z-a} \\quad (|z|>|a|). $$

連続の $e^{-\\alpha t}\\leftrightarrow 1/(s+\\alpha)$ の離散版。`discrete.numeric_ztransform` で確認する。
"""
        ),
        code(
            r"""
seq = discrete.geometric_sequence(0.5, 300)        # 0.5^k
for z in [2.0, 1.5, 1.0 + 1j]:
    num = discrete.numeric_ztransform(seq, z)
    exact = complex(z) / (complex(z) - 0.5)
    print(f"z={z}:  numeric={num:.4f}   z/(z-a)={exact:.4f}")
"""
        ),
        md(
            """
## 5. s 平面 → z 平面($z=e^{sT}$)

$z=e^{sT}$ は s 平面を z 平面へ巻きつける写像。一定 $\\sigma$ の縦線は半径 $e^{\\sigma T}$ の円になり、
**左半面($\\sigma<0$)→ 単位円の内側**、**虚軸 → 単位円**、右半面 → 外側。
"""
        ),
        code(
            r"""
dt = 1.0
omega = np.linspace(-np.pi, np.pi, 240)            # one Nyquist band
fig, (axs, axz) = plt.subplots(1, 2, figsize=(11, 4.6))
for sig in [-0.8, -0.4, 0.0, 0.4]:
    s = sig + 1j * omega
    axs.plot(s.real, s.imag, label=f"sigma={sig}")
    z = discrete.s_to_z(s, dt)
    axz.plot(z.real, z.imag)
th = np.linspace(0, 2 * np.pi, 240)
axz.plot(np.cos(th), np.sin(th), "k--", lw=1, alpha=0.6, label="unit circle")
axs.axvline(0, color="k", lw=1); axs.set_title("s-plane: lines of constant sigma")
axs.set_xlabel("Re s"); axs.set_ylabel("Im s"); axs.legend(fontsize=8); axs.grid(alpha=0.2)
axz.set_title("z = e^{s*dt}: LHP -> inside the unit circle")
axz.set_xlabel("Re z"); axz.set_ylabel("Im z"); axz.set_aspect("equal")
axz.legend(fontsize=8); axz.grid(alpha=0.2)
plt.tight_layout()
"""
        ),
        md(
            """
## 6. 離散の安定性とステップ応答

連続では「極が左半面」で安定。離散では **極が単位円の内側** $|z|<1$ なら安定。
`discrete.is_stable_discrete` が判定する。
"""
        ),
        code(
            r"""
fig, ax = plt.subplots(figsize=(7, 4))
for a, lab in [(0.5, "a=0.5 (stable)"), (0.9, "a=0.9 (stable, slow)"), (1.1, "a=1.1 (unstable)")]:
    b = (1.0 - a) if a < 1 else 0.1                # gain so a stable system has DC gain 1
    sysd = discrete.discrete_tf([b], [1.0, -a], dt=1.0)
    k, y = discrete.discrete_step_response(sysd, n=30)
    ax.step(k, y, where="post", label=f"{lab}, |z|={a}, stable={discrete.is_stable_discrete(sysd)}")
ax.axhline(1.0, color="gray", ls=":"); ax.set_ylim(-0.3, 2.5)
ax.set_xlabel("k (sample)"); ax.set_ylabel("y[k]")
ax.set_title("discrete step: pole inside |z|<1 settles, outside diverges")
ax.legend(fontsize=8); ax.grid(alpha=0.25)
plt.tight_layout()
"""
        ),
        md(
            """
## 7. ラプラスとの対応(まとめ)

| 連続(ラプラス) | 離散(z 変換) |
|---|---|
| $\\mathcal{L}\\{f\\}=\\int_0^\\infty f e^{-st}dt$ | $X(z)=\\sum_k x[k] z^{-k}$ |
| $e^{-\\alpha t}\\leftrightarrow 1/(s+\\alpha)$ | $a^k \\leftrightarrow z/(z-a)$ |
| 微分 → $s$ 倍 | 1サンプル遅延 → $z^{-1}$ 倍 |
| 安定 ⇔ 極が左半面 | 安定 ⇔ 極が単位円内 |
| 虚軸 = フーリエ変換 | 単位円 = 離散時間フーリエ(DTFT) |

橋は $z=e^{sT}$。以下でサンプリング定理・DTFT/DFT・双一次変換まで見ます。
"""
        ),
        md(
            r"""
## 7b. サンプリング定理とエイリアシング

$z=e^{sT}$ は $s$ と $s+i\frac{2\pi}{T}k$ を **同じ $z$ に写します**。
つまり周波数は $2\pi/T$ を法としてしか区別できません。これがエイリアシングで、
区別が付く上限 $f_s/2$ が **ナイキスト周波数**、区別が付く条件が **サンプリング定理** です。

サンプリング周波数 $f_s$ で標本化された正弦波 $f$ は、見かけ上

$$
f_{\text{alias}} = \big|\,f - f_s\,\mathrm{round}(f/f_s)\,\big|
$$

の正弦波と区別が付きません。
"""
        ),
        code(
            r"""
# Three different sinusoids, one sample set: aliasing made visible.
fs = 10.0
dt_s = 1.0 / fs
k = np.arange(0, 21)
t_fine = np.linspace(0, 2.0, 2000)

fig, ax = plt.subplots(figsize=(8, 4.4))
for f_hz, color, ls in [(2.0, "#1f77b4", "-"), (8.0, "#2ca02c", "--"), (12.0, "#d62728", ":")]:
    alias = abs(f_hz - fs * round(f_hz / fs))
    ax.plot(t_fine, np.sin(2 * np.pi * f_hz * t_fine), ls, color=color, lw=1.2,
            alpha=0.8, label=f"{f_hz:.0f} Hz  -> alias {alias:.0f} Hz")
ax.plot(k * dt_s, np.sin(2 * np.pi * 2.0 * k * dt_s), "ko", ms=6, zorder=5,
        label=f"samples at fs = {fs:.0f} Hz")
ax.set_xlim(0, 1.0); ax.set_xlabel("t [s]"); ax.set_ylabel("x(t)")
ax.legend(fontsize=8, loc="upper right"); ax.grid(alpha=0.25)
ax.set_title("2, 8 and 12 Hz produce identical samples at fs = 10 Hz")
plt.tight_layout()

print("Nyquist frequency =", fs / 2, "Hz")
for f_hz in (2.0, 8.0, 12.0, 23.0):
    print(f"  {f_hz:5.1f} Hz looks like {abs(f_hz - fs * round(f_hz / fs)):5.1f} Hz")
"""
        ),
        md(
            r"""
2 Hz・8 Hz・12 Hz が同じ点列を出します。**標本からは元の周波数を復元できない** ——
だから標本化の前にアンチエイリアスフィルタで $f_s/2$ 以上を落とす、という実務が要ります。

## 7c. DTFT と DFT — 単位円上の z 変換

$X(z)$ を単位円 $z=e^{i\omega}$ の上で読むと **離散時間フーリエ変換(DTFT)**:

$$
X(e^{i\omega}) = \sum_k x[k]\,e^{-i\omega k}.
$$

さらに $\omega$ を $N$ 等分点 $\omega_n = 2\pi n/N$ だけ拾うと **DFT**(= `np.fft.fft`)。
つまり DFT は DTFT の標本、DTFT は z 変換の単位円への制限で、3 つは同じものの別の切り口です。
"""
        ),
        code(
            r"""
# The unit circle is where the z-transform becomes a Fourier transform.
seq = discrete.geometric_sequence(0.8, 64)                 # x[k] = 0.8^k

w_grid = np.linspace(-np.pi, np.pi, 401)
X_dtft = discrete.numeric_ztransform(seq, np.exp(1j * w_grid))
closed = 1.0 / (1.0 - 0.8 * np.exp(-1j * w_grid))          # sum of the infinite series
print("DTFT vs closed form, max err  :", float(np.max(np.abs(X_dtft - closed))))

w_dft = 2 * np.pi * np.arange(seq.size) / seq.size
print("np.fft.fft vs z on the circle :",
      float(np.max(np.abs(np.fft.fft(seq) - discrete.numeric_ztransform(seq, np.exp(1j * w_dft))))))

fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.plot(w_grid, np.abs(X_dtft), color=plotting.ACCENT, lw=2, label="|X(e^{i w})| (DTFT)")
w_c = np.where(w_dft > np.pi, w_dft - 2 * np.pi, w_dft)
ax.plot(w_c, np.abs(np.fft.fft(seq)), "o", ms=3.5, color="#d62728", label="DFT samples (N = 64)")
ax.set_xlabel("w [rad/sample]"); ax.set_ylabel("magnitude"); ax.legend(fontsize=8); ax.grid(alpha=0.25)
ax.set_title("the DFT is the DTFT sampled; the DTFT is the z-transform on |z| = 1")
plt.tight_layout()
"""
        ),
        md(
            r"""
残差が $3.1\times10^{-6}$ 残るのは、$0.8^k$ を 64 項で打ち切っているからです。
捨てた尾の絶対値は $\sum_{k\ge 64}0.8^k = 0.8^{64}/(1-0.8)\approx 3.14\times10^{-6}$ —
実測値と一致します。**閉形式との差は打ち切り誤差そのもの** で、実装のバグではありません。

## 7d. 双一次変換 — 連続の設計を離散に載せる

$z=e^{sT}$ は超越関数なので、有理な $K(s)$ を有理な $K(z)$ に直せません。
そこで 1 次のパデ近似にあたる **双一次(Tustin)変換**

$$
s \;\longleftarrow\; \frac{2}{T}\,\frac{z-1}{z+1}
$$

を使います。これは左半面を単位円の内側に **正確に** 写すので、**安定性が保存** されます。
代償が **周波数ワーピング** で、連続の $\omega_a$ は離散の

$$
\omega_d = \frac{2}{T}\arctan\!\Big(\frac{\omega_a T}{2}\Big)
$$

に移ります。低周波ではほぼ一致し、$f_s/2$ に近づくほど圧縮されます。
"""
        ),
        code(
            r"""
# Bilinear transform: exact stability mapping, warped frequency axis.
from scipy import signal

T_s = 0.1
wc = 5.0
b_z, a_z = signal.bilinear([wc], [1.0, wc], fs=1 / T_s)     # lowpass wc/(s+wc)
print("H(z) numerator:", np.round(b_z, 6), " denominator:", np.round(a_z, 6))

print("\n analog w   ->  digital w    warp")
for w_a in (1.0, 5.0, 15.0, 30.0):
    w_d = 2 / T_s * np.arctan(w_a * T_s / 2)
    print(f"{w_a:8.1f}   ->  {w_d:8.4f}   {100 * (w_d - w_a) / w_a:+6.1f}%")

w_a = np.logspace(-1, np.log10(np.pi / T_s), 400)
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.semilogx(w_a, 20 * np.log10(np.abs(wc / (1j * w_a + wc))), "k", lw=2, label="analog wc/(s+wc)")
w_dig, h_dig = signal.freqz(b_z, a_z, worN=w_a * T_s)
ax.semilogx(w_a, 20 * np.log10(np.abs(h_dig)), color=plotting.ACCENT, lw=2,
            label="bilinear H(z), T = 0.1 s")
ax.axvline(np.pi / T_s, color="#d62728", ls=":", lw=1.2, label="Nyquist")
ax.set_xlabel("w [rad/s]"); ax.set_ylabel("magnitude [dB]"); ax.legend(fontsize=8)
ax.grid(alpha=0.25, which="both")
ax.set_title("bilinear squeezes the infinite analog axis into one Nyquist band")
plt.tight_layout()
"""
        ),
        md(
            r"""
高周波が押し込められるので、離散側の減衰はナイキストで急に落ち込みます。
狙いの遮断周波数を合わせたいときは、あらかじめ $\omega_a \to \frac{2}{T}\tan(\omega_d T/2)$ と
**プリワープ** してから変換します。

最後に、07 章 §6c で作った PI コントローラを Tustin で離散化し、
サンプル周期の粗さがステップ応答にどう出るかを見ます。
"""
        ),
        code(
            r"""
# Discretizing the chapter-07 PI controller, closing the loop in z.
plant = systems.tf([1.0], [2.0, 1.0])
ctrl = systems.pid(kp=2.0, ki=3.0)
closed_c = systems.feedback(systems.series(plant, ctrl))
tt = np.linspace(0, 12, 601)
y_c = systems.step_response(closed_c, tt)

fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.plot(tt, y_c, "k", lw=2, label=f"continuous, overshoot {y_c.max():.3f}")
for T_c, color in [(0.05, "#2ca02c"), (0.4, "#d62728")]:
    cn, cd, _ = signal.cont2discrete((ctrl.num, ctrl.den), T_c, method="bilinear")
    pn, pd, _ = signal.cont2discrete((plant.num, plant.den), T_c, method="zoh")
    ol_num = np.trim_zeros(np.polymul(np.squeeze(cn), np.squeeze(pn)), "f")
    ol_den = np.polymul(np.squeeze(cd), np.squeeze(pd))
    cl = signal.TransferFunction(
        ol_num, np.polyadd(ol_den, np.pad(ol_num, (ol_den.size - ol_num.size, 0))), dt=T_c
    )
    k_idx, y_d = discrete.discrete_step_response(cl, n=int(12 / T_c))
    ax.step(np.asarray(k_idx).ravel() * T_c, np.asarray(y_d).ravel(), where="post",
            color=color, lw=1.4,
            label=f"T = {T_c}, overshoot {np.max(y_d):.3f}, stable={discrete.is_stable_discrete(cl)}")
ax.axhline(1.0, color="gray", ls=":", lw=1)
ax.set_xlabel("t [s]"); ax.set_ylabel("output"); ax.legend(fontsize=8); ax.grid(alpha=0.25)
ax.set_title("the same PI loop, sampled: coarse T adds overshoot")
plt.tight_layout()
"""
        ),
        md(
            """
サンプル周期を粗くすると行き過ぎ量が増えます。連続で設計した余裕が、
離散化で目減りしているためです(実務では「連続で設計 → 十分速く標本化 → 離散で検証」の順で扱う)。

## 8. Exercises / Advanced Notes

- **Basic**: $x[k]=2^{-k}$ の z 変換を求め、収束域 $|z|>1/2$ を述べよ。
- **Applied**: 差分方程式 $y[k]-0.8\\,y[k-1]=x[k]$ の伝達関数 $H(z)=1/(1-0.8z^{-1})$ を作り、
  `discrete` でステップ応答を描け。
- **Advanced**: 双一次変換 $s=\\frac{2}{T}\\frac{z-1}{z+1}$ が左半面を単位円内へ写すことを、
  $s=\\sigma+i\\omega$ を代入して $|z|<1 \\iff \\sigma<0$ の形で示せ。
- **Advanced**: §7d のプリワープ $\\omega_a=\\frac{2}{T}\\tan(\\omega_d T/2)$ を実装し、
  狙った遮断周波数が離散側で正確に出ることを確かめよ。

> サンプリング定理・エイリアシングは §7b、DTFT/DFT は §7c、双一次変換とコントローラ離散化は
> §7d に実装済み。
"""
        ),
    ]
    return assemble(
        "11. z 変換 — 離散の世界への橋渡し",
        [("—", "サンプリング・z 変換・s→z 写像・離散の安定性")],
        "サンプリングで連続→離散へ。$z=e^{sT}$ が s 平面を z 平面へ写し、左半面 → 単位円内、安定性も対応する。",
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
    "09_capstone_three_lenses": nb09,
    "10_exercise_solutions": nb10,
    "11_z_transform_discrete_bridge": nb11,
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
