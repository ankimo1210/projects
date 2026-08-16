"""Generate the Fourier-analysis textbook notebooks deterministically.

Run from anywhere with the package importable:

    PYTHONPATH=src python tools/build_notebooks.py

Each notebook follows the book's fixed shape (Big Picture -> Problem -> Intuition
-> Visualization -> Definition -> Computation -> Invariant -> Failure Mode ->
Application -> Exercises -> Advanced Notes) with Basic / Applied / Advanced
layers. Heavily implemented: 01, 02, 03, 06, 08. Lighter (real content + TODO):
00, 04, 05, 07, 09. The generated .ipynb files are then executed in place so they
carry outputs (the book builds with execute_notebooks: off).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nbkit import code, md, write

NB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "notebooks")

SETUP = """\
# Shared setup: make fourier_book importable, fix seeds, inline rendering.
%matplotlib inline
import sys
from pathlib import Path

try:
    import fourier_book  # noqa: F401
except ModuleNotFoundError:
    for _base in (Path.cwd(), *Path.cwd().parents):
        if (_base / "src" / "fourier_book").is_dir():
            sys.path.insert(0, str(_base / "src"))
            break

import matplotlib.pyplot as plt
import numpy as np

from fourier_book import datasets, filters, plotting, signals, spectral, transforms, widgets

np.set_printoptions(precision=3, suppress=True)
"""


def write_nb(name, cells):
    os.makedirs(NB_DIR, exist_ok=True)
    path = os.path.join(NB_DIR, name + ".ipynb")
    write(cells, path)
    print(f"wrote {os.path.relpath(path)}  ({len(cells)} cells)")


# ========================================================================== #
# 00 — overview
# ========================================================================== #
write_nb(
    "00_overview",
    [
        md("""# 00. 全体像 — フーリエ解析は「波で関数を読み解く言語」

この教材は、フーリエ解析を **関数を直交する波の基底で展開する理論** として学ぶ
Jupyter Notebook 教科書です。単なる FFT 入門や信号処理のレシピ集ではありません。
中心にあるのは次の見方です。

> 複雑な関数や信号を、単純な振動成分に分解し、
> **構造・エネルギー・滑らかさ・時間変化** を読み解く。

定義から始めません。まず「なぜ波に分解したいのか」「分解すると何が見えるのか」
から入り、現象 → 直感 → 可視化 → 数式 → Python 実験 → 応用 → 発展 の順に進みます。"""),
        md("""## なぜ波に分解するのか

正弦波は「最も単純な振動」です。複雑に見える信号も、周波数の違う正弦波を
足し合わせたものとして表せます。波に分解すると、時間の波形を眺めていては
見えない構造が見えてきます。

- **構造**: どの周波数成分が含まれるか(和音・周期・トレンド)
- **エネルギー**: 各成分にどれだけのエネルギーがあるか(Parseval)
- **滑らかさ**: 滑らかな関数ほど高周波成分が速く小さくなる
- **時間変化**: 周波数が時間とともにどう変わるか(STFT)"""),
        md("""## 時間領域と周波数領域

同じ信号を 2 通りに見ます。**時間領域**(横軸 = 時刻)では「いつ何が起きたか」、
**周波数領域**(横軸 = 周波数)では「どの振動がどれだけ含まれるか」が見えます。
下の図は、3 つの正弦波を足した信号(左)と、その振幅スペクトル(右)です。
左の波形からは読み取りにくい「3 本の周波数成分」が、右にははっきり立ちます。"""),
        code(SETUP),
        code("""\
# A signal built from three pure tones, viewed in both domains.
fs = 500.0
t, x = datasets.make_multitone(fs=fs, duration=1.0, freqs=(5, 12, 30), amps=(1.0, 0.6, 0.3))
freqs, amp = transforms.amplitude_spectrum(x, fs)
plotting.plot_time_and_freq(t, x, freqs, amp, xlim_freq=(0, 50))
plt.show()"""),
        md(r"""## フーリエ級数・フーリエ変換・DFT・FFT の違い

| 道具 | 対象 | 周波数 | 式の中心 |
|---|---|---|---|
| フーリエ級数 | **周期**関数 | 離散(整数倍音) | $f(x)=\sum_n c_n e^{inx}$ |
| フーリエ変換 | **非周期**関数 | 連続スペクトル | $\hat f(\xi)=\int f(x)e^{-2\pi i x\xi}dx$ |
| DFT | **有限個**の標本 | 離散ビン | $X_k=\sum_n x_n e^{-2\pi i kn/N}$ |
| FFT | DFT と同じ | 同じ | DFT を $O(N\log N)$ で計算する**アルゴリズム** |

級数は「周期関数を倍音の和に」、変換は「非周期関数を連続スペクトルに」、
DFT は「有限データを離散周波数に」分けます。FFT は DFT の高速計算法であって、
別の変換ではありません。"""),
        md(r"""## 線形代数・微分積分・PDE との接続

本書を貫く一番大事な見方は **「フーリエ解析は関数版の線形代数」** です。

- 正弦波・余弦波・複素指数関数 $e^{inx}$ は、関数空間の **基底** のように働く
- 関数の内積 $\langle f,g\rangle=\int f\overline{g}\,dx$ で「成分の大きさ」を測る
- フーリエ係数は、関数を各基底方向へ **射影** した成分
- 微分は周波数領域では $ik$ 倍 → PDE はモードごとに分離される(08 章)

線形代数(`analytics/linear_algebra`)の内積・正射影・固有値分解を知っていると、
本書の見通しが一気に良くなります。"""),
        md("""## この教材の読み方 / 3 層構成

各 Notebook は原則として **Big Picture → Problem → Intuition → Visualization →
Definition → Computation → Invariant/Energy → Failure Mode → Application →
Exercises → Advanced Notes** の流れで構成されます。各章には 3 つの層を入れています。

- **Basic**: 初学者が最低限理解すべき内容
- **Applied**: Python 実装・応用例
- **Advanced**: 証明・発展理論・実務上の注意(厳密な収束条件などはここに分離)

### 章構成

| Notebook | 内容 |
|---|---|
| `00_overview` | 全体像・時間/周波数領域・読み方・環境準備 |
| `01_waves_complex_numbers_inner_products` | 正弦波・複素指数・関数の内積・直交性 |
| `02_fourier_series_periodic_functions` | フーリエ級数・矩形波・Gibbs 現象 |
| `03_convergence_energy_parseval` | 収束・エネルギー・Parseval・係数減衰 |
| `04_fourier_transform_nonperiodic_functions` | フーリエ変換・不確定性 |
| `05_convolution_filtering_distributions` | 畳み込み・フィルタ・畳み込み定理 |
| `06_dft_fft_sampling_aliasing` | DFT/FFT・標本化・aliasing・窓関数 |
| `07_time_frequency_stft_wavelets_intro` | STFT・スペクトログラム・wavelet 入口 |
| `08_pde_spectral_methods` | 熱・波動方程式・スペクトル法 |
| `09_applications_signal_image_finance_ml` | 音・画像 2D FFT・金融時系列・ML |

### Python 環境の準備

リポジトリルート `~/projects` の uv workspace を使う場合:

```bash
cd ~/projects
make install          # = uv sync --all-packages(fourier を members に追加後)
uv run jupyter lab analytics/fourier/notebooks/
```

単体で使う場合は `analytics/fourier/README.md` を参照してください。
共通関数はすべて `src/fourier_book/` にあり、上の setup セルで読み込んでいます。"""),
        md("""## まとめ

- フーリエ解析は、関数を **直交する波の基底** で展開する理論
- 時間領域と周波数領域は同じ信号の二つの顔
- 級数 / 変換 / DFT は「対象」が違うだけ、FFT は DFT の高速計算法
- 次章 `01` では、その基底となる **正弦波・複素指数・内積・直交性** を作る"""),
    ],
)
# ========================================================================== #
# 01 — waves, complex numbers, inner products
# ========================================================================== #
write_nb(
    "01_waves_complex_numbers_inner_products",
    [
        md(r"""# 01. 波・複素数・関数の内積

**この章のゴール**: フーリエ解析の「基底」を作る。正弦波の 3 つのパラメータ、
複素指数関数 $e^{i\theta}$、そして関数の内積と直交性を、図と計算で掴む。"""),
        md(r"""## Big Picture

フーリエ解析は **関数版の線形代数** です。ベクトルを基底ベクトルの和で表すように、
関数を **波の和** で表します。そのために必要な道具は 3 つだけです。

1. **正弦波** — 最も単純な振動(基底の「向き」)
2. **複素指数関数** $e^{i\theta}$ — 正弦・余弦をまとめて扱う回転(Euler の公式)
3. **関数の内積** — 「その波がどれだけ含まれるか」を測るものさし"""),
        md(r"""## Problem

複雑な信号 $f(t)$ から「周波数 $f_0$ の成分がどれだけ含まれるか」を取り出したい。
ベクトルなら内積 $\langle v, e_k\rangle$ で第 $k$ 成分が取れた。関数でも同じことを
したい — そのための内積と、互いに混ざらない基底(直交性)が必要になる。"""),
        md(r"""## Intuition — 正弦波の 3 パラメータ

$$ x(t) = A\sin(2\pi f t + \phi) $$

- **振幅 $A$**: 波の大きさ
- **周波数 $f$**: どれくらい速く振動するか(Hz = 1 秒あたりの回数)
- **位相 $\phi$**: 波の横ずれ

下のスライダー(JupyterLab で動作)で 3 つを動かすと、波がどう変わるか体感できます。
静的環境では、その下の図が代表例(周波数・位相違い)を示します。"""),
        code(SETUP),
        code("""\
# Interactive (JupyterLab): drag amplitude / frequency / phase.
try:
    widgets.interactive_sine()
except Exception as e:
    print("interactive demo needs JupyterLab:", e)"""),
        code("""\
# Static fallback: same idea, three sines differing in frequency and phase.
t, _ = signals.time_grid(1.0, 500.0)
comps = [
    signals.sine(t, freq=2, amp=1.0, phase=0.0),
    signals.sine(t, freq=5, amp=0.7, phase=0.0),
    signals.sine(t, freq=2, amp=1.0, phase=np.pi / 2),  # phase-shifted = cosine
]
plotting.plot_components(t, comps, labels=["2 Hz", "5 Hz", "2 Hz, +90deg (=cos)"])
plt.show()"""),
        md(r"""## Visualization — 複素指数関数は「回転」

Euler の公式

$$ e^{i\theta} = \cos\theta + i\sin\theta $$

は、$e^{i\theta}$ が複素平面上の **単位円を回る点** であることを意味します。
実部が余弦、虚部が正弦。だから $e^{i2\pi f t}$ は「周波数 $f$ で回転する位相子(phasor)」で、
正弦と余弦を一度に運ぶ便利な基底になります。"""),
        code("""\
# The phasor exp(2πi f t): real & imaginary parts in time, and the unit circle.
t = np.linspace(0, 1, 400)
z = signals.complex_exponential(t, freq=3.0)

fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
ax[0].plot(t, z.real, label="cos = Re", color="#1f77b4")
ax[0].plot(t, z.imag, label="sin = Im", color="#d62728")
ax[0].set_title("exp(2πi·3·t): real and imaginary parts")
ax[0].set_xlabel("time t [s]"); ax[0].legend(fontsize=8); ax[0].grid(alpha=0.25)

ax[1].plot(z.real, z.imag, color="#9467bd")
ax[1].scatter([1], [0], color="black", zorder=5)
ax[1].set_aspect("equal"); ax[1].set_title("traces the unit circle |z| = 1")
ax[1].set_xlabel("Re"); ax[1].set_ylabel("Im"); ax[1].grid(alpha=0.25)
plt.show()

print("max |exp| =", np.abs(z).max(), " (always 1)")"""),
        md(r"""## Definition — 関数の内積と直交性

ベクトルの内積 $\langle u,v\rangle=\sum_k u_k\overline{v_k}$ を、関数に拡張します。

$$ \langle f, g \rangle = \int_a^b f(x)\,\overline{g(x)}\,dx $$

これで関数の「長さ」 $\|f\|=\sqrt{\langle f,f\rangle}$ と「角度」が定義できます。
区間 $[0,2\pi)$ 上で、複素指数の族 $\{e^{inx}\}_{n\in\mathbb{Z}}$ は **直交** します:

$$ \frac{1}{2\pi}\int_0^{2\pi} e^{imx}\,\overline{e^{inx}}\,dx = \delta_{mn} $$

直交とは「別々の成分が互いに混ざらずに測れる」性質です。これがあるから、
各周波数成分を内積一発で取り出せます。"""),
        md(r"""## Computation — 直交性を数値で確かめる

基底 $e^{inx}$ を格子上でサンプリングし、内積(= 正規化した和)の行列(Gram 行列)を
作ると、**単位行列**になるはずです。"""),
        code("""\
# Gram matrix of {exp(i n x)} on [0, 2π): should be the identity (orthonormal).
N = 512
x = np.linspace(0, 2 * np.pi, N, endpoint=False)
ns = np.arange(-4, 5)
B = np.array([np.exp(1j * n * x) for n in ns])      # (9, N)
G = (B @ B.conj().T) / N                            # <e_m, e_n> with 1/(2π)∫ normalization

fig, ax = plt.subplots(figsize=(4.6, 4))
im = ax.imshow(G.real, cmap="RdBu_r", vmin=-1, vmax=1,
               extent=[ns[0] - .5, ns[-1] + .5, ns[-1] + .5, ns[0] - .5])
ax.set_title("Gram matrix Re<e_m, e_n>")
ax.set_xlabel("n"); ax.set_ylabel("m")
plt.colorbar(im, ax=ax, fraction=0.046)
plt.show()

print("max off-diagonal magnitude:", np.abs(G - np.eye(len(ns))).max())"""),
        md(r"""## Invariant / Energy — ノルムは「波のエネルギー」

$\|f\|^2=\langle f,f\rangle=\int |f|^2 dx$ は信号のエネルギーに対応します。
正弦波 $A\sin(2\pi f t)$ の 1 周期平均パワーは $A^2/2$ です。直交基底では、
全体のエネルギーが各成分のエネルギーの和になります(Parseval、03 章)。"""),
        md(r"""## Failure Mode — 「1 周期分」で測らないと直交が崩れる

直交性は **積分区間が周期の整数倍** のときに成り立ちます。半端な区間で切り取ると
成分同士が混ざり(内積が 0 にならない)、後の章で出る **スペクトル漏れ**(06)の
原因になります。下で、整数周期と半端な区間の内積を比べてみます。"""),
        code("""\
# <sin(2x), sin(3x)> over a full period (≈0) vs a truncated interval (≠0).
def inner(f, g, x):
    return np.trapezoid(f * g, x)

x_full = np.linspace(0, 2 * np.pi, 2000)
x_part = np.linspace(0, 2.3, 2000)            # not an integer number of periods
print("full period :", inner(np.sin(2 * x_full), np.sin(3 * x_full), x_full))
print("truncated   :", inner(np.sin(2 * x_part), np.sin(3 * x_part), x_part))"""),
        md(r"""## Application — 1 つの内積 = 1 つのフーリエ係数

信号を 1 つの基底波へ射影すると、その周波数成分の量(= フーリエ係数)が得られます。
例として $f(x)=3+2\cos 2x-\sin 5x$ から、$\cos 2x$ 成分の係数 $a_2=2$ を取り出します。"""),
        code("""\
# Project f onto cos(2x): a_2 = (1/π) ∫ f(x) cos(2x) dx  ->  expect 2.
x = np.linspace(0, 2 * np.pi, 4096, endpoint=False)
f = 3 + 2 * np.cos(2 * x) - np.sin(5 * x)
a2 = 2 * np.mean(f * np.cos(2 * x))       # mean over a period = (1/2π)∫, ×2 for the trig norm
a0 = np.mean(f)                           # DC component
print("a0 (mean)      =", a0)             # -> 3
print("a2 (cos2 amp)  =", a2)             # -> 2
print("via trig_coeffs:", transforms.trig_coeffs(lambda t: 3 + 2*np.cos(2*t) - np.sin(5*t), 5)[0][2])"""),
        md(r"""### 射影としてのフーリエ係数(可視化)

係数 $a_2$ は、信号 $f$ を基底波 $\cos 2x$ へ **射影** した成分の量です。赤が射影された成分
$a_2\cos 2x$ — 「$f$ の中にどれだけ $\cos 2x$ が含まれるか」を図にしたもの。"""),
        code("""\
# A Fourier coefficient is a projection: the red curve is the cos(2x) content of f.
xx = np.linspace(0, 2 * np.pi, 600, endpoint=False)
f = 3 + 2 * np.cos(2 * xx) - np.sin(5 * xx)
a2 = 2 * np.mean(f * np.cos(2 * xx))
plotting.plot_projection(xx, f, np.cos(2 * xx), a2, basis_label="cos 2x")
plt.show()"""),
        md(r"""## Exercises

1. **位相と余弦**: $\sin(\theta+\pi/2)=\cos\theta$ を Euler の公式から示し、数値でも確認せよ。
2. **直交の破れ**: 上の Gram 行列を区間 $[0, 2.3)$ で作ると単位行列からどれだけずれるか。
3. **エネルギー**: $A\sin(2\pi f t)$ の 1 周期平均パワーが $A^2/2$ になることを数値で確かめよ。
4. **射影**: $f(x)=x$($-\pi<x<\pi$、周期 $2\pi$)の $b_n=\langle f,\sin nx\rangle$ を数値計算し、
   $b_n=2(-1)^{n+1}/n$ と比べよ(のこぎり波、02 章への布石)。"""),
        md(r"""## Advanced Notes

```{admonition} ヒルベルト空間 $L^2$
:class: note
内積 $\langle f,g\rangle=\int f\overline{g}$ を備えた二乗可積分関数の空間 $L^2[0,2\pi]$ は
**完備**(Cauchy 列が必ず収束する)で、$\{e^{inx}/\sqrt{2\pi}\}$ はその **正規直交基底**を成す。
「関数を波で展開する」とは、この基底による座標表示にほかならない。複素内積では
共役 $\overline{g}$ を取る点に注意(順序で複素共役が入れ替わる)。
```

- 直交性は「周期の整数倍」で積分するという条件に強く依存する。
- 完備性(基底が「足りている」こと)は、部分和が元の関数に $L^2$ で収束する根拠(03 章)。"""),
    ],
)
# ========================================================================== #
# 02 — Fourier series of periodic functions
# ========================================================================== #
write_nb(
    "02_fourier_series_periodic_functions",
    [
        md(r"""# 02. フーリエ級数 — 周期関数を波の和で表す

**この章のゴール**: 周期関数を三角関数(または複素指数)の和で表す **フーリエ級数** を作り、
矩形波・のこぎり波・三角波で係数を計算し、不連続点に現れる **Gibbs 現象** を観察する。"""),
        md(r"""## Big Picture

周期 $2\pi$ の関数 $f$ は、基本波とその倍音の重ね合わせで書けます。

$$ f(x) \sim \frac{a_0}{2} + \sum_{n=1}^{\infty}\bigl(a_n\cos nx + b_n\sin nx\bigr)
        = \sum_{n=-\infty}^{\infty} c_n e^{inx} $$

01 章の直交性のおかげで、各係数は内積一発で取り出せます。"""),
        md(r"""## Problem

カクカクした **矩形波** を、滑らかな正弦波だけで表せるでしょうか。
直感的には無理そうですが、無限に倍音を足せば近づきます。何が起き、どこで破綻するかを見ます。"""),
        md(r"""## Intuition — 基本波に倍音を足していく

矩形波(period $2\pi$)は奇関数なので、**奇数次の正弦波だけ**で作れます。

$$ \text{square}(x) = \frac{4}{\pi}\sum_{k=0}^{\infty}\frac{\sin\bigl((2k+1)x\bigr)}{2k+1} $$

倍音を足すほど角が立ち、矩形に近づきます。下の図とスライダーで確かめましょう。"""),
        code(SETUP),
        code("""\
# Build a square wave from its odd harmonics; more terms -> sharper corners.
t, _ = signals.time_grid(1.0, 2000.0)
target = signals.square_wave(t, freq=3.0)
orders = [1, 3, 9, 30]
partials = [signals.square_wave_partial_sum(t, 3.0, k) for k in orders]
plotting.plot_partial_sums(t, partials, orders, target=target)
plt.show()"""),
        code("""\
# Interactive (JupyterLab): slide the number of odd harmonics.
try:
    widgets.interactive_square_partial_sum()
except Exception as e:
    print("interactive demo needs JupyterLab:", e)"""),
        md(r"""### 部分和の収束を一望(小分割)

倍音数 $N$ を増やすほど角が立ち、矩形波に近づく様子を並べて見る。"""),
        code("""\
# Small multiples: the square wave emerges as more odd harmonics are added.
t, _ = signals.time_grid(1.0, 2000.0)
target = signals.square_wave(t, 3.0)
fig, axes = plt.subplots(2, 3, figsize=(11, 5), sharex=True, sharey=True)
for ax, N in zip(axes.ravel(), [1, 3, 5, 9, 15, 40], strict=True):
    ax.plot(t, target, color="gray", lw=0.8)
    ax.plot(t, signals.square_wave_partial_sum(t, 3.0, N), color="#d62728", lw=1.2)
    ax.set_title(f"N = {N}", fontsize=9)
    ax.set_xlim(0, 0.5)
    ax.grid(alpha=0.2)
fig.suptitle("square wave: more harmonics -> sharper corners")
fig.tight_layout()
plt.show()"""),
        md(r"""## Definition — 三角級数と複素級数

$$ a_n = \frac{1}{\pi}\int_{-\pi}^{\pi} f(x)\cos nx\,dx, \qquad
   b_n = \frac{1}{\pi}\int_{-\pi}^{\pi} f(x)\sin nx\,dx $$

複素形では

$$ c_n = \frac{1}{2\pi}\int_{-\pi}^{\pi} f(x)\,e^{-inx}\,dx, \qquad
   c_n = \tfrac{1}{2}(a_n - i b_n)\ (n>0). $$

**偶関数**なら $b_n=0$(余弦だけ)、**奇関数**なら $a_n=0$(正弦だけ)。
$a_0/2$ は平均値(DC 成分)です。"""),
        md(r"""## Computation — 係数を数値で求める

`transforms.trig_coeffs` で矩形波の係数を計算します。奇数次の $b_n$ が
$\tfrac{4}{\pi n}$ に一致し、偶数次と $a_n$ がほぼ 0 になることを確認します。"""),
        code("""\
# Trig coefficients of a period-2π square wave: b_n = 4/(π n) for odd n, else 0.
square_2pi = lambda x: np.sign(np.sin(x))
a, b = transforms.trig_coeffs(square_2pi, n_max=15, period=2 * np.pi)
n = np.arange(len(b))
theory = np.where(n % 2 == 1, 4 / (np.pi * np.where(n == 0, 1, n)), 0.0)

fig, ax = plt.subplots(figsize=(8, 3))
ax.stem(n, b, basefmt=" ", linefmt="C0-", markerfmt="C0o", label="numerical b_n")
ax.plot(n, theory, "rx", ms=9, label="4/(π n), n odd")
ax.set_xlabel("harmonic n"); ax.set_title("square wave: b_n"); ax.legend(); ax.grid(alpha=0.25)
plt.show()
print("max |a_n| (should be ~0):", np.abs(a).max())"""),
        md(r"""## Invariant / Energy — DC 成分と対称性

$a_0/2$ は 1 周期の平均。奇対称なら正弦のみ、偶対称なら余弦のみ、という対称性は
係数の半分をゼロにします。次に、矩形・のこぎり・三角の **係数の減衰の速さ** を比べます。
これが 03 章の「滑らかさ ↔ 係数減衰」に直結します。"""),
        code("""\
# Coefficient decay: square (~1/n), sawtooth (~1/n), triangle (~1/n^2).
period = 2 * np.pi
f_sq  = lambda x: signals.square_wave(x, 1 / period)
f_saw = lambda x: signals.sawtooth_wave(x, 1 / period)
f_tri = lambda x: signals.triangle_wave(x, 1 / period)

n_max = 40
ns = np.arange(1, n_max + 1)
mags = {}
for name, f in [("square", f_sq), ("sawtooth", f_saw), ("triangle", f_tri)]:
    a, b = transforms.trig_coeffs(f, n_max=n_max, period=period)
    mags[name] = np.hypot(a[1:], b[1:])

fig, ax = plt.subplots(figsize=(8, 3.4))
for name in mags:
    ax.loglog(ns, mags[name] + 1e-18, "o-", ms=3, label=name)
ax.loglog(ns, 1 / ns, "k--", alpha=.5, label="1/n")
ax.loglog(ns, 1 / ns**2, "k:", alpha=.5, label="1/n²")
ax.set_xlabel("harmonic n"); ax.set_ylabel("|coeff|"); ax.legend(fontsize=8)
ax.set_title("smoother wave -> faster coefficient decay"); ax.grid(alpha=.25, which="both")
plt.show()"""),
        md(r"""## Failure Mode — Gibbs 現象

不連続点の近くでは、いくら倍音を足しても **約 9% の行き過ぎ(overshoot)** が残ります。
これは消えず、ジャンプの高さに対して一定比 $\approx 1.0895$(半ジャンプの約 18%)に収束します。
平均二乗では収束しても、各点・最大値では収束しないことの典型例です(03 章で再訪)。"""),
        code("""\
# Gibbs overshoot near a jump does not shrink with more terms.
t, _ = signals.time_grid(1.0, 8000.0)
approx = signals.square_wave_partial_sum(t, freq=3.0, n_terms=80)
print("peak of partial sum:", approx.max(), " (target is 1.0; ~1.0895 overshoot)")

jump = 1 / 6  # first jump of a 3 Hz square wave
sel = (t > jump - 0.02) & (t < jump + 0.02)
fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(t[sel], signals.square_wave(t, 3.0)[sel], color="gray", lw=1, label="square")
ax.plot(t[sel], approx[sel], color="#d62728", lw=1.4, label="N = 80")
ax.axhline(1.0, color="black", ls=":", lw=1)
ax.set_title("Gibbs overshoot near the jump"); ax.set_xlabel("time t [s]")
ax.legend(fontsize=8); ax.grid(alpha=0.25)
plt.show()"""),
        md(r"""## Application — 波形合成(音色)

倍音の振幅の配り方が **音色** を決めます。同じ基本周波数でも、矩形・のこぎり・三角は
倍音構成が違うので違う音に聞こえます。複素級数からの再構成も確認しておきます。"""),
        code("""\
# Reconstruct the square wave from complex coefficients c_n.
ns, c = transforms.fourier_series_coeffs(square_2pi, n_max=25, period=2 * np.pi)
xx = np.linspace(0, 2 * np.pi, 1000, endpoint=False)
rec = transforms.reconstruct_complex(ns, c, xx, period=2 * np.pi)

fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(xx, square_2pi(xx), color="gray", lw=1, label="square")
ax.plot(xx, rec, color="#1f77b4", lw=1.4, label="reconstruction (|n|≤25)")
ax.set_title("reconstruction from complex coefficients"); ax.set_xlabel("x")
ax.legend(fontsize=8); ax.grid(alpha=0.25)
plt.show()"""),
        md(r"""## Exercises

1. **のこぎり波**: $f(x)=x$($-\pi<x<\pi$)の $b_n=2(-1)^{n+1}/n$ を `trig_coeffs` で確認せよ。
2. **三角波の滑らかさ**: 三角波の係数が $1/n^2$ で減衰することを log-log 図で確かめ、
   矩形波($1/n$)との違いを説明せよ。
3. **偶奇分解**: 任意の関数を偶部 $\tfrac{1}{2}(f(x)+f(-x))$ と奇部に分け、
   前者が余弦のみ・後者が正弦のみで表せることを数値で示せ。
4. **Gibbs**: 倍音数 $N$ を変えても overshoot 比が一定に近づくことを表で示せ。"""),
        md(r"""## Advanced Notes

```{admonition} Dirichlet の収束定理(要約)
:class: note
$f$ が区分的に滑らかなら、フーリエ級数は連続点で $f(x)$ に、跳びの点では
左右極限の平均 $\tfrac{1}{2}(f(x^+)+f(x^-))$ に **各点収束** する。Gibbs の overshoot は
この各点収束と矛盾しない — overshoot の位置がジャンプに限りなく近づくため。
```

- Gibbs の overshoot 比は $\frac{1}{\pi}\int_0^\pi \frac{\sin t}{t}dt \approx 1.0895$(半ジャンプ基準)。
- 緩和策: Fejér 平均(部分和の算術平均)や $\sigma$-近似(Lanczos)で overshoot を抑えられる。"""),
    ],
)
# ========================================================================== #
# 03 — convergence, energy, Parseval
# ========================================================================== #
write_nb(
    "03_convergence_energy_parseval",
    [
        md(r"""# 03. 収束・エネルギー・Parseval

**この章のゴール**: フーリエ級数が「どの意味で」収束するのかを区別し、
エネルギー保存則 **Parseval の等式** を確かめ、**滑らかさが係数の減衰速度として現れる**
ことを観察する。"""),
        md(r"""## Big Picture

部分和 $S_N f$ が元の $f$ に「近づく」と言うとき、近づき方には種類があります。

- **平均二乗(L²)収束**: 誤差のエネルギー $\|f-S_Nf\|_2^2 \to 0$
- **各点収束**: 各 $x$ で $S_Nf(x)\to f(x)$(跳びの点では平均値)
- **一様(sup)収束**: 最大誤差 $\max_x|f-S_Nf|\to 0$(不連続があると **成り立たない**)

そして **Parseval**: 時間領域のエネルギーと周波数領域のエネルギーは等しい。"""),
        md(r"""## Problem

矩形波の部分和は、倍音を増やせば本当に矩形波に「収束」するのでしょうか。
答えは「平均二乗では Yes、最大誤差では No(Gibbs)」。この食い違いを数値で見ます。"""),
        code(SETUP),
        md(r"""## Definition — ノルムと Parseval

エネルギー(L² ノルムの 2 乗):

$$ \|f\|_2^2 = \int_{-\pi}^{\pi} |f(x)|^2\,dx. $$

**Parseval の等式**(複素係数版):

$$ \frac{1}{2\pi}\int_{-\pi}^{\pi}|f(x)|^2\,dx = \sum_{n=-\infty}^{\infty} |c_n|^2. $$

離散版(DFT)では

$$ \sum_{n=0}^{N-1}|x_n|^2 = \frac{1}{N}\sum_{k=0}^{N-1}|X_k|^2. $$

「エネルギーは領域を移っても保存する」— これが Parseval の意味です。"""),
        md(r"""## Computation — Parseval を数値で確かめる

まず離散版。任意の信号で、時間領域のエネルギーと周波数領域のエネルギーが
一致することを確認します。"""),
        code("""\
# Discrete Parseval: time-domain energy == frequency-domain energy / N.
fs = 500.0
t, x = datasets.make_multitone(fs=fs, duration=1.0, freqs=(5, 12, 30), amps=(1.0, .6, .3), snr_db=10)
X = np.fft.fft(x)
e_time = np.sum(x**2)
e_freq = np.sum(np.abs(X) ** 2) / len(x)
print(f"time energy = {e_time:.6f}")
print(f"freq energy = {e_freq:.6f}")
print(f"difference  = {abs(e_time - e_freq):.2e}")"""),
        md(r"""次に **エネルギーの積み上げ**。矩形波(period $2\pi$、$\overline{f^2}=1$)では、
係数のエネルギー和 $\tfrac{1}{2}\sum b_n^2$ が全エネルギー 1 に収束します(Parseval)。"""),
        code("""\
# Series energy accumulates to the total: (1/2)Σ b_n^2 -> mean(square^2) = 1.
square_2pi = lambda x: np.sign(np.sin(x))
a, b = transforms.trig_coeffs(square_2pi, n_max=80, period=2 * np.pi)
energy_cum = np.cumsum(0.5 * (a**2 + b**2))  # a[0] handled below
energy_cum += (a[0] / 2) ** 2                 # DC term (0 here)

fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(np.arange(len(energy_cum)), energy_cum, color="#2ca02c")
ax.axhline(1.0, color="black", ls="--", label="total energy = 1")
ax.set_xlabel("harmonics included N"); ax.set_ylabel("accumulated energy")
ax.set_title("Parseval: energy fills up as N grows"); ax.legend(); ax.grid(alpha=.25)
plt.show()"""),
        md(r"""### エネルギーは少数の倍音に集中する

各倍音のエネルギー $\tfrac12(a_n^2+b_n^2)$ と、その累積が全エネルギー(=1)へ達する様子(Parseval)。"""),
        code("""\
# Energy per harmonic and its cumulative sum reaching the total (Parseval).
sq = lambda x: np.sign(np.sin(x))
a, b = transforms.trig_coeffs(sq, n_max=15, period=2 * np.pi)
e = 0.5 * (a**2 + b**2)
e[0] = (a[0] / 2) ** 2
fig, ax = plt.subplots(1, 2, figsize=(10, 3.2))
ax[0].bar(np.arange(len(e)), e, color="#1f77b4")
ax[0].set_title("energy per harmonic"); ax[0].set_xlabel("n")
ax[1].plot(np.arange(len(e)), np.cumsum(e), "o-", color="#2ca02c")
ax[1].axhline(1.0, color="black", ls="--", label="total = 1")
ax[1].set_title("cumulative energy -> 1"); ax[1].set_xlabel("harmonics included"); ax[1].legend(fontsize=8)
for a_ in ax:
    a_.grid(alpha=0.25)
plt.show()"""),
        md(r"""## Invariant / Energy — 平均二乗誤差は単調に減る

部分和の次数 $N$ を上げると、平均二乗誤差は **単調に減少して 0** に向かいます
(L² 収束)。これは「エネルギーの意味では確かに収束する」ことを示します。"""),
        code("""\
# Mean-square error of the square-wave partial sums decreases to 0.
t, _ = signals.time_grid(1.0, 4000.0)
target = signals.square_wave(t, 3.0)
Ns = np.arange(1, 60)
mse = [np.mean((signals.square_wave_partial_sum(t, 3.0, k) - target) ** 2) for k in Ns]

fig, ax = plt.subplots(figsize=(8, 3))
ax.semilogy(Ns, mse, "o-", ms=3, color="#1f77b4")
ax.set_xlabel("number of harmonics N"); ax.set_ylabel("mean-square error (log)")
ax.set_title("L² convergence: MSE -> 0"); ax.grid(alpha=.25, which="both")
plt.show()"""),
        md(r"""## 滑らかさ ↔ 係数減衰(本章の主役)

**関数が滑らかなほど、高周波成分が速く小さくなります。**

- 不連続(矩形波): $|c_n|\sim 1/n$
- 連続だが折れ点あり(三角波): $|c_n|\sim 1/n^2$
- 無限回微分可能($e^{\sin x}$): $|c_n|$ は **指数的**に減衰

一般に「$k$ 回連続微分可能なら $|c_n| = O(1/n^{k+1})$」。
これは後で「滑らかな信号はローパスで失うものが少ない=圧縮しやすい」に直結します。"""),
        code("""\
# Decay rate encodes smoothness. Left: power laws (log-log). Right: exponential (semilog).
period = 2 * np.pi
funcs = {
    "square (jump)":     lambda x: signals.square_wave(x, 1 / period),
    "triangle (kink)":   lambda x: signals.triangle_wave(x, 1 / period),
    "exp(sin x) (C∞)":   lambda x: np.exp(np.sin(x)),
}
n_max = 30
ns = np.arange(1, n_max + 1)
mags = {}
for name, f in funcs.items():
    a, b = transforms.trig_coeffs(f, n_max=n_max, period=period)
    mags[name] = np.hypot(a[1:], b[1:])

fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
for name, m in mags.items():
    ax[0].loglog(ns, m + 1e-18, "o-", ms=3, label=name)
ax[0].loglog(ns, 1 / ns, "k--", alpha=.4); ax[0].loglog(ns, 1 / ns**2, "k:", alpha=.4)
ax[0].set_title("log-log: power-law decay"); ax[0].set_xlabel("n"); ax[0].legend(fontsize=7)
ax[0].grid(alpha=.25, which="both")
for name, m in mags.items():
    ax[1].semilogy(ns, m + 1e-18, "o-", ms=3, label=name)
ax[1].set_title("semilog: C∞ decays exponentially (straight line)")
ax[1].set_xlabel("n"); ax[1].grid(alpha=.25, which="both")
plt.show()"""),
        md(r"""## Failure Mode — Gibbs は sup ノルムでは消えない

MSE は 0 に向かうのに、**最大誤差は 0 に向かいません**。不連続の近くの overshoot 比は
$N$ を増やしても $\approx 0.0895$(ジャンプ高さ 2 に対して片側 0.0895)に張り付きます。
「収束した」と言うときは、どのノルムでの話かを必ず意識してください。"""),
        code("""\
# Sup-norm error stays ~0.0895 even as MSE -> 0.
t, _ = signals.time_grid(1.0, 16000.0)
target = signals.square_wave(t, 3.0)
print(f"{'N':>5} {'MSE':>12} {'max error':>12}")
for N in [10, 40, 160, 640]:
    approx = signals.square_wave_partial_sum(t, 3.0, N)
    print(f"{N:5d} {np.mean((approx - target) ** 2):12.2e} {np.max(np.abs(approx - target)):12.4f}")"""),
        md(r"""## Application — エネルギー圧縮と圧縮の予感

Parseval により「少数の大きな係数」が全エネルギーの大半を担うなら、
残りを捨てても誤差(エネルギー)は小さい。これが JPEG など **変換符号化** の原理で、
09 章の画像圧縮につながります。"""),
        md(r"""## Exercises

1. **Basel 問題**: 矩形波の Parseval から $\sum_{n\ \text{odd}} 1/n^2 = \pi^2/8$ を導け。
2. **三角波のエネルギー**: 三角波で Parseval を数値確認し、累積エネルギー図を描け。
3. **収束の意味**: ある $N$ で「MSE は小さいが max error は大きい」例を作り、図で示せ。
4. **滑らかさ**: $f(x)=|\sin x|$ の係数減衰の次数を測り、滑らかさ($C^0$ で折れ点)と整合するか調べよ。"""),
        md(r"""## Advanced Notes

```{admonition} 収束の階層と完備性
:class: note
$L^2$ では Riesz–Fischer により部分和は常に $L^2$ 収束する(基底が完備だから)。
各点収束はより繊細で、連続関数ですら全点では収束しない例がある一方、
**Carleson の定理**(1966)は $L^2$ 関数のフーリエ級数が **ほとんど至るところ**
各点収束することを保証する。一様収束は $f$ が連続かつ有界変動などの追加条件を要する。
```

- Bessel の不等式 $\sum|c_n|^2 \le \frac{1}{2\pi}\int|f|^2$ は任意の正規直交系で成立、
  等号(Parseval)は系が **完備** なときに限る。
- 係数減衰 ↔ 滑らかさは双対的(時間の滑らかさ = 周波数の速い減衰)で、04 章の
  不確定性原理と同じ精神。"""),
    ],
)
# ========================================================================== #
# 06 — DFT, FFT, sampling, aliasing
# ========================================================================== #
write_nb(
    "06_dft_fft_sampling_aliasing",
    [
        md(r"""# 06. DFT・FFT・標本化・aliasing

**この章のゴール**: 有限個の標本に対する **DFT** を定義し、それが行列(あるいは FFT)で
計算できることを確かめ、標本化に伴う **aliasing** と **スペクトル漏れ** という 2 つの落とし穴を
体験する。"""),
        md(r"""## Big Picture

連続信号を測れるのは有限個の点だけです。$N$ 個の標本 $x_0,\dots,x_{N-1}$ を
$N$ 個の周波数成分に分けるのが **離散フーリエ変換(DFT)**:

$$ X_k = \sum_{n=0}^{N-1} x_n\,e^{-2\pi i kn/N}, \qquad
   x_n = \frac{1}{N}\sum_{k=0}^{N-1} X_k\,e^{2\pi i kn/N}. $$

**FFT** はこの DFT を $O(N\log N)$ で計算する **アルゴリズム**(別の変換ではない)。"""),
        md(r"""## Problem

連続の世界を離散で覗くと何が変わるのか。とくに「速すぎる振動」を粗く標本化すると
何が起きるのか(aliasing)、「半端な周波数」をどう見えてしまうのか(漏れ)を調べます。"""),
        md(r"""## Intuition / Definition — DFT は行列、FFT は速い行列

DFT は行列 $W$($W_{kj}=e^{-2\pi i kj/N}$)による掛け算 $X=Wx$ と同じです。
`fourier_book.transforms` には、定義どおりの $O(N^2)$ 版 `dft`(= `W @ x`)と、
`numpy.fft` を使う高速版があり、両者は一致します。"""),
        code(SETUP),
        code("""\
# The naive O(N^2) DFT equals numpy's FFT; the DFT matrix is what FFT computes fast.
rng = np.random.default_rng(0)
x = rng.standard_normal(8)
print("dft == np.fft.fft :", np.allclose(transforms.dft(x), np.fft.fft(x)))

W = transforms.dft_matrix(16)
fig, ax = plt.subplots(1, 2, figsize=(9, 3.8))
ax[0].imshow(W.real, cmap="RdBu_r"); ax[0].set_title("Re W (DFT matrix, N=16)")
ax[1].imshow(W.imag, cmap="RdBu_r"); ax[1].set_title("Im W")
for a in ax:
    a.set_xlabel("n"); a.set_ylabel("k")
plt.show()"""),
        md(r"""## 周波数ビンと Nyquist 周波数

標本化周波数 $f_s$、長さ $N$ のとき、ビン $k$ は周波数 $k\,f_s/N$ に対応します。
表現できる最高周波数は **Nyquist 周波数** $f_s/2$。実信号では振幅スペクトルを片側(0〜$f_s/2$)で見ます。"""),
        code("""\
# Real amplitude spectrum of a multitone; nothing exists above Nyquist = fs/2.
fs = 1000.0
t, x = datasets.make_multitone(fs=fs, duration=1.0, freqs=(50, 120, 200), amps=(1.0, .6, .3))
freqs, amp = transforms.amplitude_spectrum(x, fs)
fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(freqs, amp, color="#d62728")
ax.axvline(fs / 2, color="black", ls="--", label="Nyquist fs/2")
ax.set_xlabel("frequency f [Hz]"); ax.set_ylabel("amplitude")
ax.set_title("one-sided amplitude spectrum"); ax.legend(); ax.grid(alpha=.25)
plt.show()"""),
        md(r"""## Failure Mode 1 — aliasing(エイリアシング)

標本化が遅すぎる($f_s < 2f$)と、**高周波が低周波になりすまします**。
18 Hz の正弦波を 20 Hz で標本化すると、$|18-20|=2$ Hz の波と区別できません。
標本点が両方の波の上に乗ることを確認します。"""),
        code("""\
# An 18 Hz tone sampled at 20 Hz looks identical to a 2 Hz tone.
fs = 20.0
ts, _ = signals.time_grid(1.0, fs)
xs = signals.sine(ts, 18.0)

dense = np.linspace(0, 1, 1000)
true_wave = signals.sine(dense, 18.0)
alias_wave = signals.sine(dense, 2.0)        # |18 - 20| = 2 Hz

fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(dense, true_wave, color="lightgray", lw=1, label="true 18 Hz")
ax.plot(dense, alias_wave, color="#1f77b4", lw=1.4, ls="--", label="alias 2 Hz")
ax.scatter(ts, xs, color="black", zorder=5, label="samples @ 20 Hz")
ax.set_xlabel("time t [s]"); ax.set_title("aliasing: samples sit on both curves")
ax.legend(fontsize=8); ax.grid(alpha=.25)
plt.show()"""),
        md(r"""## Failure Mode 2 — スペクトル漏れと窓関数

DFT は信号が「丁度ビンに乗る」周期だと仮定します。半端な周波数(例 10.5 Hz、
ビンは 1 Hz 刻み)だと、エネルギーが隣のビンへ **漏れ** ます。
**窓関数**(端を滑らかに 0 へ落とす)を掛けると漏れの裾が減ります
(代わりに山が少し太る、というトレードオフ)。"""),
        code("""\
# Leakage: a 10.5 Hz tone (off-bin) smears; a Hann window tames the skirts.
fs = 128.0
t, _ = signals.time_grid(1.0, fs)             # N=128, 1 Hz bins
on_bin = signals.sine(t, 10.0)
off_bin = signals.sine(t, 10.5)
win = np.hanning(len(t))

def norm_spec(sig):
    f, a = transforms.amplitude_spectrum(sig, fs)
    return f, a / a.max()                      # normalise to peak for shape comparison

f0, s_on = norm_spec(on_bin)
_, s_off = norm_spec(off_bin)
_, s_off_w = norm_spec(off_bin * win)

fig, ax = plt.subplots(figsize=(8, 3.2))
ax.plot(f0, s_on, "o-", ms=3, label="10.0 Hz (on bin)")
ax.plot(f0, s_off, "s-", ms=3, label="10.5 Hz (leakage)")
ax.plot(f0, s_off_w, "^-", ms=3, label="10.5 Hz + Hann")
ax.set_xlim(4, 17); ax.set_xlabel("frequency f [Hz]"); ax.set_ylabel("normalized amplitude")
ax.set_title("spectral leakage and windowing"); ax.legend(fontsize=8); ax.grid(alpha=.25)
plt.show()"""),
        md(r"""### 窓関数の比較

主葉の幅(周波数分解能)と側葉の高さ(漏れ)はトレードオフ。矩形窓は主葉が最も狭いが側葉が最悪。"""),
        code("""\
# Window shapes and their side-lobe behaviour (the resolution vs leakage trade-off).
plotting.plot_window_comparison(n=128)
plt.show()"""),
        md(r"""## Invariant / Energy — DFT でも Parseval

DFT でもエネルギーは保存します: $\sum_n |x_n|^2 = \tfrac{1}{N}\sum_k |X_k|^2$(03 章)。
窓を掛けると総エネルギーが変わるため、振幅の絶対値を比較するときは
**窓の利得補正** が要ります(上では形だけ比べるため peak 正規化しました)。"""),
        md(r"""## Application — 実務での DFT

- 録音・センサ・株価など、現実のデータはすべて離散標本 → 解析はすべて DFT/FFT。
- 解析の前に「$f_s$ は十分か(anti-alias フィルタ)」「窓は何を使うか」を必ず考える。
- 周波数分解能は $\Delta f=f_s/N$。細かく見たいなら **長く** 測る(ゼロ詰めは見かけだけ)。"""),
        md(r"""## Exercises

1. **ビンの周波数**: $f_s=1000,\ N=250$ のとき各ビンの周波数刻みは何 Hz か。数値で確認せよ。
2. **折り返し**: $f_s=100$ Hz で 70 Hz の波はどの周波数に alias するか(答 30 Hz)。図で示せ。
3. **窓の比較**: Hann と Hamming、Blackman で漏れの裾と主葉幅を比較せよ。
4. **ゼロ詰め**: 信号にゼロを足すと「滑らかに」見えるが分解能は上がらないことを確かめよ。"""),
        md(r"""## Advanced Notes

```{admonition} なぜ FFT は速いのか
:class: note
DFT を偶数番号・奇数番号に分けると、半分サイズの DFT 二つに分解できる
(Cooley–Tukey)。これを再帰すると $O(N\log N)$。$N=10^6$ で $N^2$ と $N\log N$ は
$10^6$ 倍以上違う — リアルタイム信号処理が成立する理由。
```

- **標本化定理(Nyquist–Shannon)**: 帯域 $B$ に限られた信号は $f_s>2B$ で完全復元できる。
- 窓選択は「周波数分解能 vs ダイナミックレンジ(漏れ)」のトレードオフ。
- 実数信号は `rfft` で半分の計算。スペクトルは共役対称 $X_{N-k}=\overline{X_k}$。"""),
    ],
)
# ========================================================================== #
# 08 — PDE spectral methods
# ========================================================================== #
write_nb(
    "08_pde_spectral_methods",
    [
        md(r"""# 08. 偏微分方程式とスペクトル法

**この章のゴール**: フーリエ基底で展開すると **時間発展がモードごとに分離** されることを使い、
熱方程式・波動方程式を「各周波数の常微分方程式」に還元して解く。微分が周波数領域で
$ik$ 倍になることが心臓部。"""),
        md(r"""## Big Picture

周期境界で $u(x,t)=\sum_k \hat u_k(t)\,e^{ikx}$ と展開すると、空間微分は

$$ \frac{\partial}{\partial x}e^{ikx} = ik\,e^{ikx} $$

なので、線形・定数係数の PDE は **各モード $\hat u_k$ の独立な ODE** に分かれます。
モードごとに閉じた形で解けるので、空間微分の誤差がない高精度解法(スペクトル法)になります。"""),
        md(r"""## Problem

熱方程式

$$ \frac{\partial u}{\partial t} = \alpha\frac{\partial^2 u}{\partial x^2} $$

と波動方程式

$$ \frac{\partial^2 u}{\partial t^2} = c^2\frac{\partial^2 u}{\partial x^2} $$

を、差分格子ではなくフーリエ係数の上で解きます。"""),
        md(r"""## Intuition / Definition — 微分は $ik$ 倍

熱方程式を Fourier 変換すると、各モードは

$$ \frac{d\hat u_k}{dt} = -\alpha k^2\,\hat u_k
   \quad\Longrightarrow\quad \hat u_k(t)=\hat u_k(0)\,e^{-\alpha k^2 t}. $$

$|k|$ が大きい(高周波・細かい構造)ほど $e^{-\alpha k^2 t}$ で **速く消える**。
波動方程式では $\hat u_k(t)=\hat u_k(0)\cos(c|k|t)+\hat v_k(0)\frac{\sin(c|k|t)}{c|k|}$ で、
モードは減衰せず **振動** します。"""),
        code(SETUP),
        md(r"""## Computation 1 — スペクトル微分の精度

まず「微分を $ik$ 倍で計算する」だけで、滑らかな周期関数の微分が
**差分法より桁違いに正確**になることを確認します。"""),
        code("""\
# Spectral differentiation vs finite difference on a smooth periodic function.
L = 2 * np.pi
N = 64
x = np.linspace(0, L, N, endpoint=False)
u = np.exp(np.sin(x))
du_exact = np.cos(x) * np.exp(np.sin(x))

du_spec = spectral.spectral_derivative(u, L)
du_fd = np.gradient(u, x[1] - x[0])             # 2nd-order central difference

print(f"spectral  max error: {np.max(np.abs(du_spec - du_exact)):.2e}")
print(f"finite-diff max error: {np.max(np.abs(du_fd - du_exact)):.2e}")"""),
        md(r"""## Computation 2 — 熱方程式は高周波を先に消す

初期条件に低周波と高周波を混ぜておくと、時間とともに **高周波のさざ波が先に消えて**
滑らかになる様子が見えます。"""),
        code("""\
# Heat equation smooths: high-frequency ripples vanish first.
L = 2 * np.pi
N = 256
x = np.linspace(0, L, N, endpoint=False)
u0 = 1.0 + np.sin(x) + 0.5 * np.sin(8 * x) + 0.3 * np.sin(20 * x)
alpha = 0.02
times = [0.0, 0.02, 0.1, 0.5]

fig, ax = plt.subplots(figsize=(8, 3.4))
for ti in times:
    ax.plot(x, spectral.solve_heat_spectral(u0, L, alpha, ti), label=f"t = {ti}")
ax.set_xlabel("x"); ax.set_title("heat equation: diffusion smooths the high modes")
ax.legend(fontsize=8); ax.grid(alpha=.25)
plt.show()"""),
        code("""\
# Per-mode amplitude decays like exp(-α k² t): high k disappears far faster.
ts = np.linspace(0, 2, 200)
fig, ax = plt.subplots(figsize=(8, 3))
for k in [1, 8, 20]:
    ax.plot(ts, np.exp(-alpha * k**2 * ts), label=f"mode k = {k}")
ax.set_xlabel("time t"); ax.set_ylabel("relative amplitude")
ax.set_title("mode decay exp(-α k² t)"); ax.legend(); ax.grid(alpha=.25)
plt.show()"""),
        md(r"""### 熱方程式の時空間ヒートマップ

横=空間 $x$、縦=時間 $t$。高周波の細かい縞が時間とともに(上へ向かって)先に消え、滑らかになる。"""),
        code("""\
# Space-time view: high-frequency ripples fade upward (in time) -> smoothing.
xg = np.linspace(0, L, 256, endpoint=False)
u0_h = 1.0 + np.sin(xg) + 0.5 * np.sin(8 * xg) + 0.3 * np.sin(20 * xg)
ts_h = np.linspace(0, 1.0, 120)
field_h = np.array([spectral.solve_heat_spectral(u0_h, L, alpha, tt) for tt in ts_h])
plotting.plot_spacetime(field_h, xg, ts_h, title="heat: u(x, t) — high freq fades upward")
plt.show()"""),
        md(r"""## Invariant / Energy — 熱: 質量保存・エネルギー散逸

$k=0$ モード($\hat u_0$)は $e^{-\alpha\cdot 0\cdot t}=1$ で不変。つまり **総量(質量)
$\int u\,dx$ は保存**します。一方で **エネルギー $\int u^2\,dx$ は単調に減少**(散逸)します。"""),
        code("""\
# Mass (∫u dx) is conserved; energy (∫u² dx) dissipates. Use the periodic
# quadrature Σu·dx — np.trapezoid drops the wrap-around interval and would show
# a spurious drift on a periodic (endpoint-excluded) grid.
dx = x[1] - x[0]
print(f"{'t':>6} {'mass ∫u':>12} {'energy ∫u²':>14}")
for ti in [0.0, 0.05, 0.2, 1.0]:
    u = spectral.solve_heat_spectral(u0, L, alpha, ti)
    print(f"{ti:6.2f} {u.sum() * dx:12.4f} {(u**2).sum() * dx:14.4f}")"""),
        md(r"""## Computation 3 — 波動方程式: 山が左右へ割れて進む

局在した初期変位(速度 0)は、**左右に半分ずつ進む波** に分かれます(d'Alembert)。
熱と違い、各モードは減衰せず振動するので、形を保って伝わります。"""),
        code("""\
# Wave equation: a localized bump splits into left- and right-moving halves.
L = 2 * np.pi
N = 256
x = np.linspace(0, L, N, endpoint=False)
u0 = np.exp(-((x - np.pi) ** 2) / (2 * 0.08))   # localized pulse
v0 = np.zeros_like(x)
c = 1.0

fig, ax = plt.subplots(figsize=(8, 3.4))
for ti in [0.0, 0.4, 0.9, 1.4]:
    ax.plot(x, spectral.solve_wave_spectral(u0, v0, L, c, ti), label=f"t = {ti}")
ax.set_xlabel("x"); ax.set_title("wave equation: the pulse splits and travels")
ax.legend(fontsize=8); ax.grid(alpha=.25)
plt.show()"""),
        md(r"""### 波動方程式の時空間ヒートマップ

2 本の特性線(左右へ進む波)が、傾いた帯として現れる。熱と違い形を保って伝わる。"""),
        code("""\
# Space-time view: the two characteristics (left/right movers) are slanted bands.
xg = np.linspace(0, L, 256, endpoint=False)
u0_w = np.exp(-((xg - np.pi) ** 2) / (2 * 0.08))
ts_w = np.linspace(0, 2.0, 160)
field_w = np.array([spectral.solve_wave_spectral(u0_w, np.zeros_like(xg), L, c, tt) for tt in ts_w])
plotting.plot_spacetime(field_w, xg, ts_w, title="wave: u(x, t) — two characteristics")
plt.show()"""),
        md(r"""## Failure Mode — 周期境界・非線形・aliasing

- スペクトル法は **周期境界** を前提にします。非周期問題にそのまま使うと端で振動
  (Gibbs)が出る → Chebyshev など別の基底が必要。
- 非線形項(例 $u u_x$)は積で **高周波を生み**、折り返して低周波を汚す(aliasing)。
  対策が **dealiasing**(2/3 ルールなど)。
- 時間積分自体は別問題(ここでは線形なので各モード解析解を使い、時間離散誤差ゼロ)。"""),
        md(r"""## Application — スペクトル法が活きる場所

乱流の直接数値計算(DNS)、地球流体、量子力学の時間発展(split-step Fourier)など、
**滑らかな解 × 周期的(または周期化できる)領域**でスペクトル法は最高精度を発揮します。
05 章の畳み込み定理(微分・畳み込みが周波数で積になる)と同じ原理の延長です。"""),
        md(r"""## Exercises

1. **解析解照合**: 単一モード $u_0=\sin(mx)$ の熱方程式解が $e^{-\alpha m^2 t}\sin(mx)$ に
   一致することを `solve_heat_spectral` で確かめよ。
2. **収束次数**: スペクトル微分の誤差を $N$ に対してプロットし、差分法の多項式収束と比べよ。
3. **定在波**: $u_0=\sin(2x),\ v_0=0$ の波動解が $\cos(2ct)\sin(2x)$ になることを確認せよ。
4. **Poisson**: `spectral.solve_poisson_spectral` で $u''=f$ を解き、$u$ を 2 回微分して $f$ に戻るか確かめよ。"""),
        md(r"""## Advanced Notes

```{admonition} なぜ「スペクトル」精度なのか
:class: note
滑らかな周期関数のフーリエ係数は指数的に減衰する(03 章)。微分を $ik$ 倍で行うと、
打ち切り誤差も指数的に小さい — これが **spectral accuracy**(代数次数でなく指数収束)。
差分法の $O(h^p)$ とは質的に異なる。
```

- 熱方程式の解は任意の初期データを瞬時に $C^\infty$ にする(平滑化作用)。
- 波動方程式はエネルギー $\tfrac12\int(u_t^2+c^2u_x^2)dx$ を保存(各モードの振動の総和)。
- Laplace 方程式 $u_{xx}+u_{yy}=0$ も、各方向にフーリエ展開すると $\hat u_k$ の
  常微分方程式 $\hat u_k''=k^2\hat u_k$(指数解)に分離できる。"""),
    ],
)
# ========================================================================== #
# 04 — Fourier transform of non-periodic functions  (lighter, runnable)
# ========================================================================== #
(
    write_nb(
        "04_fourier_transform_nonperiodic_functions",
        [
            md(r"""# 04. フーリエ変換 — 非周期関数を周波数に分ける

**学習目標**: 周期 $\to\infty$ の極限としてフーリエ変換を理解し、ガウス関数・矩形関数の
変換を計算して、**時間幅と周波数幅のトレードオフ(不確定性)** を体感する。"""),
            md(r"""## Big Picture / Definition

周期を無限に伸ばすと、離散だった倍音が **連続スペクトル** になります。

$$ \hat f(\xi) = \int_{-\infty}^{\infty} f(x)\,e^{-2\pi i x\xi}\,dx, \qquad
   f(x) = \int_{-\infty}^{\infty} \hat f(\xi)\,e^{2\pi i x\xi}\,d\xi. $$

エネルギーは保存します(**Plancherel**): $\int|f|^2dx=\int|\hat f|^2d\xi$。"""),
            md(r"""## Intuition

- 周期関数 → 線スペクトル(とびとびの周波数)
- 非周期(局在)関数 → 連続スペクトル(周波数が連続に分布)
- 時間で局在するほど、周波数では広がる(その逆も)= **不確定性**"""),
            code(SETUP),
            code("""\
# Numerical continuous Fourier transform on a fine, centered grid.
def cont_ft(x, f):
    dt = x[1] - x[0]
    n = len(x)
    spec = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(f))) * dt
    xi = np.fft.fftshift(np.fft.fftfreq(n, d=dt))
    return xi, spec

x = np.linspace(-8, 8, 4096)"""),
            md(r"""## Visualization 1 — ガウス関数のフーリエ変換はガウス関数

$e^{-\pi x^2}$ はこの変換のもとで **自分自身に移る**(自己双対)、という美しい例です。"""),
            code("""\
# The Gaussian exp(-π x²) is its own Fourier transform.
f = np.exp(-np.pi * x**2)
xi, F = cont_ft(x, f)

fig, ax = plt.subplots(1, 2, figsize=(10, 3))
ax[0].plot(x, f, color="#1f77b4"); ax[0].set_xlim(-3, 3)
ax[0].set_title("f(x) = exp(-π x²)"); ax[0].set_xlabel("x"); ax[0].grid(alpha=.25)
ax[1].plot(xi, F.real, color="#d62728", label="numerical")
ax[1].plot(xi, np.exp(-np.pi * xi**2), "k--", label="exp(-π ξ²)")
ax[1].set_xlim(-3, 3); ax[1].set_title("Fourier transform"); ax[1].set_xlabel("ξ")
ax[1].legend(fontsize=8); ax[1].grid(alpha=.25)
plt.show()"""),
            md(r"""## Visualization 2 — 矩形関数 → sinc

幅 1 の矩形パルスの変換は $\operatorname{sinc}(\xi)=\dfrac{\sin\pi\xi}{\pi\xi}$。
時間で鋭く切ると、周波数では広く尾を引きます(06 章のスペクトル漏れと同根)。"""),
            code("""\
# A box becomes a sinc — sharp edges in time mean wide spread in frequency.
box = (np.abs(x) <= 0.5).astype(float)
xi, B = cont_ft(x, box)
fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(xi, B.real, color="#d62728", label="FT of box")
ax.plot(xi, np.sinc(xi), "k--", label="sinc(ξ)")
ax.set_xlim(-8, 8); ax.set_title("box -> sinc"); ax.set_xlabel("ξ")
ax.legend(fontsize=8); ax.grid(alpha=.25)
plt.show()"""),
            md(r"""## Failure Mode / Invariant — 不確定性原理

時間幅 $\Delta x$ と周波数幅 $\Delta\xi$ の積には下限があり、両方同時に小さくできません。

$$ \Delta x \cdot \Delta\xi \ \ge \ \frac{1}{4\pi}. $$

下で、ガウスの幅 $\sigma$ を変えると周波数側の幅が逆に変わることを見ます。"""),
            code("""\
# Narrow in time <-> wide in frequency: the uncertainty trade-off.
fig, ax = plt.subplots(1, 2, figsize=(10, 3))
for sigma in [0.3, 0.7, 1.5]:
    g = np.exp(-x**2 / (2 * sigma**2))
    xi, G = cont_ft(x, g)
    ax[0].plot(x, g, label=f"σ = {sigma}")
    ax[1].plot(xi, np.abs(G) / np.abs(G).max(), label=f"σ = {sigma}")
ax[0].set_xlim(-4, 4); ax[0].set_title("time domain"); ax[0].set_xlabel("x"); ax[0].legend(fontsize=8)
ax[1].set_xlim(-3, 3); ax[1].set_title("frequency domain (normalized)"); ax[1].set_xlabel("ξ")
ax[1].legend(fontsize=8)
for a in ax:
    a.grid(alpha=.25)
plt.show()"""),
            md(r"""### 時間シフトは位相だけを回す

$f(x-a)$ の変換は振幅 $|\hat f|$ を変えず、$e^{-2\pi i a\xi}$ の **線形位相** を掛けるだけ。"""),
            code("""\
# A time shift leaves |spectrum| unchanged and adds a linear phase ramp.
g = np.exp(-x**2)
g_shift = np.exp(-(x - 2) ** 2)
xi, G = cont_ft(x, g)
_, Gs = cont_ft(x, g_shift)
fig, ax = plt.subplots(1, 2, figsize=(11, 3.2))
ax[0].plot(xi, np.abs(G), label="|F{g}|")
ax[0].plot(xi, np.abs(Gs), "--", label="|F{shifted}|")
ax[0].set_xlim(-3, 3); ax[0].set_title("shift: |spectrum| unchanged"); ax[0].legend(fontsize=8)
ax[1].plot(xi, np.unwrap(np.angle(Gs)), color="#d62728")
ax[1].set_xlim(-3, 3); ax[1].set_title("...adds a linear phase ramp"); ax[1].set_xlabel("ξ")
for a in ax:
    a.grid(alpha=0.25)
plt.show()"""),
            md(r"""### 変調はスペクトルを平行移動する

$f(x)\cos(2\pi f_0 x)$ はスペクトルを $\pm f_0$ へずらす — AM 変調・ヘテロダインの核心。"""),
            code("""\
# Multiplying by a cosine shifts the spectrum to ±f0 (amplitude modulation).
f0 = 3.0
g = np.exp(-x**2)
gm = g * np.cos(2 * np.pi * f0 * x)
xi, G = cont_ft(x, g)
_, Gm = cont_ft(x, gm)
fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(xi, np.abs(G), label="baseband |F{g}|")
ax.plot(xi, np.abs(Gm), color="#d62728", label="modulated (±f0)")
ax.set_xlim(-6, 6); ax.set_title("modulation shifts the spectrum"); ax.legend(fontsize=8); ax.grid(alpha=0.25)
plt.show()"""),
            md(r"""### Plancherel の等式を数値で確かめる

$\int |f|^2 dx = \int |\hat f|^2 d\xi$。フーリエ変換は **エネルギーを保つ**(等長写像)。
03 章の Parseval(周期関数の級数版)と同じ主張の、非周期版です。"""),
            code("""\
# Plancherel: the transform is an isometry, so both integrals agree.
dt = x[1] - x[0]
for name, fx in [("gaussian exp(-π x²)", np.exp(-np.pi * x**2)),
                 ("rect(x)", (np.abs(x) <= 0.5).astype(float)),
                 ("two-sided exp(-|x|)", np.exp(-np.abs(x)))]:
    xi_, Fx = cont_ft(x, fx)
    dxi = xi_[1] - xi_[0]
    e_time = np.sum(np.abs(fx) ** 2) * dt
    e_freq = np.sum(np.abs(Fx) ** 2) * dxi
    print(f"{name:22s}  time {e_time:10.6f}   freq {e_freq:10.6f}   "
          f"rel.err {abs(e_time - e_freq) / e_time:.2e}")"""),
            md(r"""### 変換の性質を表にする

どれも「$\hat f$ を作り直さずに済ませる」ための道具です。数値で 1 本ずつ確認します。

| 時間領域 | 周波数領域 | 効果 |
|---|---|---|
| $f(x-a)$ | $e^{-2\pi i a\xi}\hat f(\xi)$ | 振幅は不変、線形位相が乗る |
| $f(x)e^{2\pi i b x}$ | $\hat f(\xi-b)$ | スペクトルの平行移動(変調) |
| $f(ax)$ | $\frac{1}{|a|}\hat f(\xi/a)$ | 時間で縮めると周波数で伸びる |
| $f'(x)$ | $2\pi i\xi\,\hat f(\xi)$ | 微分が掛け算になる(08 章の基礎) |
| $\overline{f(x)}$ | $\overline{\hat f(-\xi)}$ | 実信号なら共役対称 |"""),
            code("""\
# Each identity checked numerically against a directly computed transform.
g = np.exp(-np.pi * x**2)
xi, G = cont_ft(x, g)

def relerr(a, b):
    return float(np.max(np.abs(a - b)) / np.max(np.abs(b)))

# scaling: f(a x) <-> |a|^-1 fhat(xi / a)
a = 2.0
_, G_scaled = cont_ft(x, np.exp(-np.pi * (a * x) ** 2))
print(f"scaling      rel.err {relerr(G_scaled, np.interp(xi / a, xi, G) / abs(a)):.2e}")

# derivative: f'(x) <-> 2 pi i xi fhat(xi)
dg = np.gradient(g, x[1] - x[0])
_, Dg = cont_ft(x, dg)
print(f"derivative   rel.err {relerr(Dg, 2j * np.pi * xi * G):.2e}")

# conjugate symmetry of a real signal
print(f"conj. symm.  rel.err {relerr(G, np.conj(G[::-1])):.2e}")"""),
            md(r"""### デルタ関数と定数関数 — 超関数の入口

$\delta$ と $1$ は互いの変換になります。

$$ \hat\delta(\xi) = \int \delta(x) e^{-2\pi i x\xi} dx = 1, \qquad
   \widehat{1}(\xi) = \delta(\xi) $$

どちらも二乗可積分でないので、通常の積分では定義できません。
**超関数(distribution)** として、テスト関数に作用させたときの値で定義します。

数値的には、幅を狭めたガウス関数の列 $\frac{1}{\sigma}e^{-\pi x^2/\sigma^2}$ が
$\sigma \to 0$ で $\delta$ に近づく様子として見えます。
変換側では、同じ列が定数 1 に近づきます。"""),
            code("""\
# A narrowing Gaussian approaches delta; its transform flattens toward 1.
fig, ax = plt.subplots(1, 2, figsize=(11, 3.2))
for sigma in [1.0, 0.4, 0.15]:
    approx = np.exp(-np.pi * (x / sigma) ** 2) / sigma      # unit mass for all sigma
    xi_, A = cont_ft(x, approx)
    ax[0].plot(x, approx, label=f"σ = {sigma}")
    ax[1].plot(xi_, A.real, label=f"σ = {sigma}")
    print(f"σ = {sigma:4.2f}   ∫f dx = {np.trapezoid(approx, x):.6f}   "
          f"F at ξ=0 : {A[np.argmin(np.abs(xi_))].real:.6f}")
ax[0].set_xlim(-1.5, 1.5); ax[0].set_title("narrowing Gaussian -> δ"); ax[0].legend(fontsize=8)
ax[1].axhline(1.0, color="k", ls="--", lw=0.8)
ax[1].set_xlim(-8, 8); ax[1].set_ylim(0, 1.3); ax[1].set_title("...its transform -> 1")
ax[1].legend(fontsize=8)
for a_ in ax:
    a_.grid(alpha=0.25)
plt.show()"""),
            md(r"""### SymPy で解析的に導く

数値の裏取りとして、記号計算にも同じ変換を解かせます。
`sympy.fourier_transform` は本書と同じ $e^{-2\pi i x\xi}$ の規約を使います
(規約が違うと $2\pi$ が定数倍として現れるので、文献を読むときは必ず確認すること)。"""),
            code("""\
# Symbolic check of the transforms this chapter leans on.
import sympy as sp

xs, xis = sp.symbols("x xi", real=True)
a_sym = sp.symbols("a", positive=True)

print("F{exp(-pi x^2)} =", sp.fourier_transform(sp.exp(-sp.pi * xs**2), xs, xis))
print("F{exp(-a x^2)}  =", sp.simplify(sp.fourier_transform(sp.exp(-a_sym * xs**2), xs, xis)))
print("F{exp(-a|x|)}   =", sp.simplify(sp.fourier_transform(sp.exp(-a_sym * sp.Abs(xs)), xs, xis)))

# rect is easier as the defining integral: fourier_transform chokes on the
# Heaviside form (it ends up comparing a complex infinity to zero).
rect_ft = sp.integrate(sp.exp(-2 * sp.pi * sp.I * xs * xis),
                       (xs, sp.Rational(-1, 2), sp.Rational(1, 2)))
print("F{rect(x)}      =", sp.simplify(rect_ft))"""),
            md(r"""## Application

応用: 分光・回折(空間版フーリエ変換)、量子力学(位置と運動量の不確定性)、
通信(帯域と時間長)。本書では 06 章で離散版(DFT)、05 章で畳み込み定理へ接続します。"""),
            md(r"""## Exercises

1. **不確定性**: $e^{-\pi a x^2}$ の時間幅(標準偏差)と周波数幅を数値で求め、
   その積が $a$ によらず一定になることを確かめよ。$a$ を 0.25, 1, 4 で比較すること。
2. **矩形と sinc**: $\mathrm{rect}(x)$ の変換が $\mathrm{sinc}(\xi)=\sin(\pi\xi)/(\pi\xi)$ に
   なることを数値で示し、なぜ裾が $1/\xi$ でしか減らないのかを、
   関数の滑らかさと係数減衰の関係(03 章)から説明せよ。
3. **微分の性質**: $f'' \leftrightarrow -(2\pi\xi)^2 \hat f$ を数値で確かめ、
   高周波が増幅されることから「微分はノイズに弱い」と言われる理由を述べよ。
4. **変調の復元**: $g(x)\cos(2\pi f_0 x)$ から $g$ を取り出す手順(復調)を、
   もう一度 $\cos(2\pi f_0 x)$ を掛けてローパスする方法で実装せよ。
5. **Plancherel の破れ**: 上の数値検証で `rect` の相対誤差が他より大きい理由を、
   グリッドの有限性と不連続点から説明せよ。

解答は 10 章にある。"""),
        ],
    ),
)

# ========================================================================== #
# 05 — convolution, filtering, distributions  (lighter, runnable)
# ========================================================================== #
(
    write_nb(
        "05_convolution_filtering_distributions",
        [
            md(r"""# 05. 畳み込み・フィルタ・畳み込み定理

**学習目標**: **畳み込み**(周囲の値を混ぜる操作)と **フィルタ**(周波数ごとに残す/消す操作)を、
**畳み込み定理** で結びつける。平滑化とノイズ除去を実装する。"""),
            md(r"""## Big Picture / Definition

畳み込み:

$$ (f * g)(t) = \int_{-\infty}^{\infty} f(\tau)\,g(t-\tau)\,d\tau. $$

**畳み込み定理**(本章の心臓部):

$$ \widehat{f * g} = \hat f \cdot \hat g. $$

「時間で畳み込む」=「周波数で掛ける」。だから **フィルタ = 周波数領域での掛け算** です。"""),
            md(r"""## Intuition

- 畳み込み = カーネル $g$ で「ご近所の重み付き平均」を作る(ぼかし=平滑化)
- ローパス = 高周波を 0 倍、低周波を 1 倍する掛け算 = なめらかなカーネルでの畳み込み
- ハイパス/バンドパスも同様に「どの周波数を残すか」を選ぶだけ"""),
            code(SETUP),
            md(r"""## Computation 1 — 畳み込み定理を数値で確認"""),
            code("""\
# Convolution in time == multiplication in frequency (circular convolution is exact).
rng = np.random.default_rng(0)
x = rng.standard_normal(64)
h = filters.gaussian_kernel(64, sigma=3.0)
lhs = np.fft.fft(filters.circular_convolve(x, h))
rhs = np.fft.fft(x) * np.fft.fft(h)
print("‖fft(x*h) - fft(x)·fft(h)‖ =", np.max(np.abs(lhs - rhs)))"""),
            md(r"""### 畳み込みは「反転してずらす」

各シフト $t_0$ で $f(\tau)$ と $g(t_0-\tau)$ の重なり(積の面積)が $(f*g)(t_0)$ になる。"""),
            code("""\
# Convolution as flip-and-slide: the shaded product area is (f*g)(t0).
t, _ = signals.time_grid(2.0, 200.0)
f = ((t > 0.3) & (t < 0.8)).astype(float)
g = np.exp(-((t - 1.0) ** 2) / (2 * 0.02))
plotting.plot_convolution_slide(t, f, g)
plt.show()"""),
            md(r"""## Computation 2 — 平滑化(ガウス畳み込み)でノイズを抑える"""),
            code("""\
# Smoothing = convolution with a Gaussian kernel.
fs = 500.0
t, _ = signals.time_grid(1.0, fs)
clean = signals.sine(t, 3.0)
noisy = signals.add_noise(clean, snr_db=0.0, seed=0)
smooth = filters.smooth_gaussian(noisy, sigma=8.0)

fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(t, noisy, color="lightgray", lw=.8, label="noisy")
ax.plot(t, smooth, color="#1f77b4", lw=1.6, label="smoothed (Gaussian)")
ax.plot(t, clean, color="black", lw=1, ls="--", label="clean")
ax.set_xlabel("time t [s]"); ax.set_title("convolution smooths"); ax.legend(fontsize=8)
ax.grid(alpha=.25)
plt.show()"""),
            md(r"""## Computation 3 — ローパスフィルタでノイズ除去

周波数領域で高周波を切る = ノイズ(広帯域)を落とし、信号(低周波)を残す。"""),
            code("""\
# Low-pass filtering in the frequency domain removes broadband noise.
fs = 1000.0
t, x = datasets.make_multitone(fs=fs, duration=1.0, freqs=(5, 12), amps=(1.0, .6), snr_db=3)
y = filters.lowpass(x, fs, cutoff=20.0)
f0, a_in = transforms.amplitude_spectrum(x, fs)
_, a_out = transforms.amplitude_spectrum(y, fs)

fig, ax = plt.subplots(1, 2, figsize=(11, 3))
ax[0].plot(t, x, color="lightgray", lw=.8, label="noisy")
ax[0].plot(t, y, color="#1f77b4", lw=1.4, label="filtered")
ax[0].set_xlim(0, 0.5); ax[0].set_title("time domain"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.25)
ax[1].plot(f0, a_in, color="lightgray", label="before")
ax[1].plot(f0, a_out, color="#d62728", label="after")
ax[1].axvline(20, color="black", ls="--"); ax[1].set_xlim(0, 80)
ax[1].set_title("spectrum"); ax[1].set_xlabel("f [Hz]"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.25)
plt.show()"""),
            md(r"""### ロー/バンド/ハイパスを一望

同じ信号(5 + 40 + 150 Hz)から、残す周波数帯を選ぶ操作。"""),
            code("""\
# Three ideal filters on the same 3-tone signal: keep low / mid / high bands.
fs = 1000.0
t, _ = signals.time_grid(1.0, fs)
x = signals.harmonic_sum(t, [5, 40, 150], [1.0, 1.0, 1.0])
lo = filters.lowpass(x, fs, 20)
bd = filters.bandpass(x, fs, 25, 80)
hi = filters.highpass(x, fs, 100)
fig, ax = plt.subplots(2, 2, figsize=(11, 5), sharex=True)
for a_, sig, ttl in zip(ax.ravel(), [x, lo, bd, hi],
                        ["original (5+40+150 Hz)", "low-pass < 20", "band-pass 25-80", "high-pass > 100"],
                        strict=True):
    a_.plot(t, sig, lw=0.8); a_.set_title(ttl, fontsize=9); a_.set_xlim(0, 0.2); a_.grid(alpha=0.25)
fig.tight_layout()
plt.show()"""),
            md(r"""### δ は畳み込みの単位元

$(f * \delta)(x) = f(x)$。これが「$\delta$ とは何か」の一番実用的な答えです。
$\delta$ は値を持つ関数ではなく、**畳み込んだときに何もしない作用素** として定義されます。

数値では、幅を狭めた核との畳み込みが元の信号に近づく形で見えます。"""),
            code("""\
# Convolving with a narrowing kernel converges to the identity: f * delta = f.
fs_d = 500.0
t_d = np.arange(0, 1.0, 1 / fs_d)
sig = signals.gaussian_pulse(t_d, t0=0.5, width=0.05) + 0.5 * signals.sine(t_d, 7.0)

print(f"{'kernel width':>14} {'max |f*k - f|':>16}")
for width in [21, 9, 3, 1]:
    k = filters.gaussian_kernel(width, sigma=max(width / 6, 1e-3))
    k = k / k.sum()
    conv = np.convolve(sig, k, mode="same")
    print(f"{width:14d} {np.max(np.abs(conv - sig)):16.6f}")
print("\\nwidth -> 1 で誤差が 0 に落ちる。delta は畳み込みの単位元である")"""),
            md(r"""### Green 関数 — 線形 PDE の解は入力とインパルス応答の畳み込み

線形時間不変な系では、任意の入力に対する応答が

$$
u(x) = (f * G)(x)
$$

と書けます。$G$ は **インパルス応答**(PDE では Green 関数)で、
$\delta$ を入れたときの出力そのものです。

熱方程式 $u_t = \alpha u_{xx}$ の Green 関数はガウス核

$$
G(x, t) = \frac{1}{\sqrt{4\pi\alpha t}} \exp\!\left(-\frac{x^2}{4\alpha t}\right)
$$

なので、初期条件との畳み込みが解になります。08 章のスペクトル法と同じ答えが出ます。"""),
            code("""\
# Heat equation: convolution with the Gaussian Green function equals the
# spectral solution from chapter 08. Same operator, two representations.
L, n_x, alpha, t_end = 20.0, 1024, 0.5, 1.0
xg = np.linspace(-L / 2, L / 2, n_x, endpoint=False)
u0 = (np.abs(xg) < 1.0).astype(float)               # a box of heat

green = np.exp(-xg**2 / (4 * alpha * t_end)) / np.sqrt(4 * np.pi * alpha * t_end)
dx = xg[1] - xg[0]
u_green = np.fft.ifft(np.fft.fft(u0) * np.fft.fft(np.fft.ifftshift(green))).real * dx
u_spec = spectral.solve_heat_spectral(u0, L, alpha, t_end)

print(f"max |Green - spectral| = {np.max(np.abs(u_green - u_spec)):.3e}")
fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(xg, u0, color="#999", lw=1, label="u(x, 0)")
ax.plot(xg, u_spec, lw=2, label="spectral solver (ch.08)")
ax.plot(xg, u_green, "--", color="#d62728", lw=1.6, label="u0 * Green")
ax.set_xlim(-6, 6); ax.legend(fontsize=8); ax.grid(alpha=0.25)
ax.set_title("the heat kernel is a Green function")
plt.show()"""),
            md(r"""### 理想フィルタのリンギング — 掛け算の代償

周波数で矩形のマスクを掛けることは、時間で sinc と畳み込むことに等しい。
sinc の裾は $1/t$ でしか減らないので、**エッジの前後に振動(リンギング)が出ます**。
これは 03 章の Gibbs 現象と同じ原因です。

実用フィルタが遷移帯を滑らかにするのは、この裾を短くするためです。"""),
            code("""\
# A brick-wall mask rings; a smoothed transition does not.
fs_r = 1000.0
t_r = np.arange(0, 1.0, 1 / fs_r)
step = (t_r > 0.5).astype(float)
freqs_r = np.fft.rfftfreq(t_r.size, d=1 / fs_r)
spec_r = np.fft.rfft(step)

brick = (freqs_r <= 40).astype(float)
smooth = np.exp(-(freqs_r / 40.0) ** 2)             # Gaussian transition band

y_brick = np.fft.irfft(spec_r * brick, n=t_r.size)
y_smooth = np.fft.irfft(spec_r * smooth, n=t_r.size)

over_b = (y_brick.max() - step.max()) / step.max()
over_s = (y_smooth.max() - step.max()) / step.max()
print(f"brick-wall overshoot : {over_b * 100:6.2f} %")
print(f"smooth transition    : {over_s * 100:6.2f} %")

fig, ax = plt.subplots(figsize=(9, 3))
ax.plot(t_r, step, color="#999", lw=1, label="step")
ax.plot(t_r, y_brick, label="brick-wall low-pass")
ax.plot(t_r, y_smooth, "--", color="#2ca02c", label="smooth transition")
ax.set_xlim(0.35, 0.65); ax.legend(fontsize=8); ax.grid(alpha=0.25)
ax.set_title("ideal filters ring (Gibbs, again)")
plt.show()"""),
            md(r"""### バンドパスで特徴を取り出す

同じ波形でも、帯域を分けると別の情報が見えます。
下では低周波(トレンド)・中域(振動)・高周波(ノイズ)に分け、
それぞれの **帯域エネルギー** を特徴量として並べます。
音声・振動診断の前処理はほぼこの形です。"""),
            code("""\
# Band energies as features: the same waveform, three different questions.
fs_b = 1000.0
t_b = np.arange(0, 2.0, 1 / fs_b)
cases = {
    "trend only":  0.8 * np.sin(2 * np.pi * 1.5 * t_b),
    "trend+tone":  0.8 * np.sin(2 * np.pi * 1.5 * t_b) + 0.5 * np.sin(2 * np.pi * 60 * t_b),
    "with noise":  0.8 * np.sin(2 * np.pi * 1.5 * t_b) + 0.5 * np.sin(2 * np.pi * 60 * t_b)
                   + signals.add_noise(np.zeros_like(t_b), snr_db=0, seed=0) * 0.3,
}
bands = {"low < 5": (0, 5), "mid 20-120": (20, 120), "high > 200": (200, fs_b / 2)}

print(f"{'signal':>12} " + " ".join(f"{b:>12}" for b in bands))
for name, sig_b in cases.items():
    energies = []
    for lo_, hi_ in bands.values():
        band = filters.bandpass(sig_b, fs_b, max(lo_, 1e-9), hi_)
        energies.append(float(np.sum(band**2) / sig_b.size))
    print(f"{name:>12} " + " ".join(f"{e:12.5f}" for e in energies))
print("\\n帯域エネルギーだけで 3 つの信号が区別できる。これが特徴量である")"""),
            md(r"""## Application

応用: 画像のぼかし/輪郭抽出(09 章の 2D 版)、音声の帯域分割、移動平均(金融)、
微分方程式の Green 関数(畳み込みで解を表す)。"""),
            md(r"""## Exercises

1. **交換則**: $f * g = g * f$ を数値で確かめ、畳み込み定理
   $\widehat{f*g} = \hat f\,\hat g$ の側から見ると自明である理由を述べよ。
2. **移動平均の周波数応答**: 長さ $k$ の移動平均の周波数応答が
   $\frac{\sin(\pi k \xi)}{k \sin(\pi \xi)}$ になることを数値で示し、
   ゼロ点が $\xi = m/k$ に来ることを確かめよ。
3. **Green 関数の再利用**: 上の熱方程式の Green 関数を使って、
   初期条件をガウス関数に変えた場合の解を畳み込みで求め、
   ガウス同士の畳み込みが再びガウスになることを確かめよ。
4. **因果的フィルタ**: 上の平滑化は両側フィルタなので未来を使う。
   片側(因果的)の指数移動平均を実装し、位相遅れが出ることを示せ。
5. **リンギングの定量化**: 遷移帯の幅を変えてオーバーシュート量を測り、
   幅とリンギングの大きさの関係を図にせよ。

解答は 10 章にある。"""),
        ],
    ),
)
# ========================================================================== #
# 07 — time-frequency: STFT, spectrograms, wavelet intro  (lighter, runnable)
# ========================================================================== #
(
    write_nb(
        "07_time_frequency_stft_wavelets_intro",
        [
            md(r"""# 07. 時間周波数解析 — STFT・スペクトログラム

**学習目標**: 周波数が **時間とともに変わる** 信号には普通の FFT だけでは足りないことを知り、
**短時間フーリエ変換(STFT)** とスペクトログラムで「いつ・どの周波数が」鳴っているかを見る。
窓幅による時間/周波数分解能のトレードオフを体験する。"""),
            md(r"""## Big Picture / Problem

FFT は信号全体を 1 枚のスペクトルにまとめます。だから「前半は低い音、後半は高い音」でも、
スペクトルには両方の山が出るだけで **時間情報が失われ** ます。
短い窓で区切りながら FFT する STFT がこれを解決します。

$$ X(\tau, \omega) = \int_{-\infty}^{\infty} x(t)\,w(t-\tau)\,e^{-i\omega t}\,dt. $$"""),
            code(SETUP),
            md(r"""## Visualization 1 — チャープ(周波数が上がる音)のスペクトログラム"""),
            code("""\
# A linear chirp sweeps low -> high; the spectrogram shows a rising ridge.
fs = 2000.0
t, x = datasets.make_chirp(fs=fs, duration=2.0, f0=20.0, f1=400.0)
f, tt, S = transforms.spectrogram_db(x, fs, nperseg=256)
plotting.plot_spectrogram(f, tt, S, fmax=500, title="chirp spectrogram")
plt.show()"""),
            md(r"""## Visualization 2 — FFT は「いつ」を失う

前半 40 Hz・後半 300 Hz のバースト信号。FFT(左)は 2 本の山を出すだけで順番が分かりません。
スペクトログラム(右)は、どちらが先に鳴ったかをはっきり示します。"""),
            code("""\
# Two-tone burst: FFT sees both tones; only the spectrogram shows the timing.
fs = 2000.0
t, xb = datasets.make_two_tone_burst(fs=fs, duration=2.0, f_low=40.0, f_high=300.0)
freqs, amp = transforms.amplitude_spectrum(xb, fs)
f2, tt2, S2 = transforms.spectrogram_db(xb, fs, nperseg=256)

fig, ax = plt.subplots(1, 2, figsize=(11, 3.4))
ax[0].plot(freqs, amp, color="#d62728"); ax[0].set_xlim(0, 400)
ax[0].set_title("plain FFT (no time info)"); ax[0].set_xlabel("f [Hz]"); ax[0].grid(alpha=.25)
plotting.plot_spectrogram(f2, tt2, S2, ax=ax[1], fmax=400, title="spectrogram (when!)")
plt.show()"""),
            md(r"""## Failure Mode — 窓幅のトレードオフ

短い窓 → 時間分解能は高いが周波数はぼやける。長い窓 → 周波数は鋭いが「いつ」が曖昧。
両方同時に鋭くはできません(04 章の不確定性の時間周波数版)。"""),
            code("""\
# Short window: sharp in time, blurry in frequency. Long window: the opposite.
fig, ax = plt.subplots(1, 2, figsize=(11, 3.4))
for a, nperseg, label in zip(ax, [64, 512], ["short window (64)", "long window (512)"]):
    f, tt, S = transforms.spectrogram_db(xb, fs, nperseg=nperseg)
    plotting.plot_spectrogram(f, tt, S, ax=a, fmax=400, title=label)
plt.show()"""),
            md(r"""### STFT と wavelet の時間周波数タイル

STFT は一様なタイルで平面を覆う。wavelet は高周波ほど時間分解能を上げる(定 Q)— 同じ
不確定性の予算を、周波数帯ごとに違う配分で使う。"""),
            code("""\
# Heisenberg tiles: STFT tiles uniformly; wavelets give fine time at high freq.
plotting.plot_tf_tiling()
plt.show()"""),
            md(r"""### 連続 wavelet 変換を自前で書く

タイル図の主張を実際に計算します。Morlet wavelet

$$
\psi(t) = \pi^{-1/4} e^{2\pi i f_c t} e^{-t^2/2}
$$

をスケール $s$ で伸縮して信号と畳み込むだけなので、20 行で書けます。

$$
W(s, \tau) = \frac{1}{\sqrt{s}} \int x(t)\,
\overline{\psi\!\left(\frac{t-\tau}{s}\right)} dt
$$

スケールを周波数に読み替えると $f \approx f_c/s$。
**帯域幅が中心周波数に比例する**(定 Q)ので、高周波ほど時間分解能が上がります。

`pywt` も `scipy.signal.cwt` も使いません。前者は依存を増やし、
後者は本書が使う SciPy では削除済みだからです。"""),
            code("""\
# Continuous wavelet transform with a Morlet wavelet, written out.
def morlet_cwt(x_sig, fs_w, freqs_w, f_c=1.0, n_sigma=6.0):
    out = np.empty((freqs_w.size, x_sig.size), dtype=complex)
    for i, f in enumerate(freqs_w):
        s = f_c / f                                   # scale from target frequency
        half = int(n_sigma * s * fs_w / 2)
        tt = np.arange(-half, half + 1) / fs_w
        psi = np.pi**-0.25 * np.exp(2j * np.pi * f_c * tt / s) * np.exp(-(tt / s) ** 2 / 2)
        psi = psi / np.sqrt(s)
        out[i] = np.convolve(x_sig, np.conj(psi[::-1]), mode="same") / fs_w
    return out

fs_w = 1000.0
t_w = np.arange(0, 2.0, 1 / fs_w)
# two short bursts at different times and frequencies, plus a steady low tone
x_w = (np.exp(-((t_w - 0.4) / 0.03) ** 2) * np.sin(2 * np.pi * 200 * t_w)
       + np.exp(-((t_w - 1.3) / 0.12) ** 2) * np.sin(2 * np.pi * 40 * t_w)
       + 0.3 * np.sin(2 * np.pi * 8 * t_w))

freqs_w = np.logspace(np.log10(5), np.log10(300), 80)
W = morlet_cwt(x_w, fs_w, freqs_w)

fig, ax = plt.subplots(2, 1, figsize=(10, 5), sharex=True,
                       gridspec_kw={"height_ratios": [1, 2]})
ax[0].plot(t_w, x_w, lw=0.7); ax[0].set_ylabel("x(t)"); ax[0].grid(alpha=0.25)
ax[1].pcolormesh(t_w, freqs_w, np.abs(W), shading="auto", cmap="magma")
ax[1].set_yscale("log"); ax[1].set_ylabel("frequency [Hz]"); ax[1].set_xlabel("t [s]")
ax[0].set_title("scalogram: fine time at high frequency, fine frequency at low")
plt.tight_layout()
plt.show()"""),
            md(r"""スカログラムを読むと、200 Hz の短いバーストは **時間方向に鋭く**、
40 Hz のゆるいバーストは **時間方向に広く** 写っています。
STFT なら両方が同じ窓幅で見られるので、どちらか一方が必ずぼやけます。

定 Q の代償もここに出ています。低周波側は帯域が狭いので周波数分解能は良いが、
時間的な立ち上がりは追えません。**不確定性は消えず、配分が変わるだけ** です。"""),
            code("""\
# The constant-Q property, measured: bandwidth grows in proportion to frequency.
print(f"{'target f':>10} {'-3dB bandwidth':>16} {'Q = f / BW':>12}")
for f_target in [10.0, 40.0, 160.0]:
    s = 1.0 / f_target
    half = int(6 * s * fs_w / 2)
    tt = np.arange(-half, half + 1) / fs_w
    psi = np.pi**-0.25 * np.exp(2j * np.pi * tt / s) * np.exp(-(tt / s) ** 2 / 2)
    # the Morlet wavelet is complex, so this needs the full FFT, not rfft
    spec_psi = np.abs(np.fft.fft(psi, n=8192))
    fr = np.fft.fftfreq(8192, d=1 / fs_w)
    pos = fr > 0
    above = fr[pos][spec_psi[pos] >= spec_psi[pos].max() / np.sqrt(2)]
    bw = float(above.max() - above.min())
    print(f"{f_target:10.1f} {bw:16.2f} {f_target / bw:12.2f}")
print("\\nQ がほぼ一定 = 定 Q 変換。音階が対数的なので音楽の解析に向く")"""),
            md(r"""### 窓の選択と COLA 条件

STFT を **逆変換して元に戻せる** ためには、窓とホップの組が
COLA (constant overlap-add) 条件

$$
\sum_{m} w(t - mH) = \text{const}
$$

を満たす必要があります。Hann 窓は 50% 重ね合わせでこれを満たします。
満たさない組み合わせでは、再構成に周期的な振幅のうねりが出ます。"""),
            code("""\
# COLA: does the overlap-added window sum to a constant?
from scipy import signal as sps_signal

nperseg = 256
print(f"{'window':>10} {'hop':>6} {'COLA ripple':>14} {'scipy check':>13}")
for win_name in ["hann", "hamming", "boxcar"]:
    for hop in [nperseg // 2, nperseg // 4]:
        w = sps_signal.get_window(win_name, nperseg, fftbins=True)
        acc = np.zeros(nperseg * 8)
        for start in range(0, acc.size - nperseg, hop):
            acc[start:start + nperseg] += w
        core = acc[nperseg:-nperseg]
        ripple = float(core.max() - core.min()) / float(core.mean())
        ok = sps_signal.check_COLA(w, nperseg, nperseg - hop)
        print(f"{win_name:>10} {hop:6d} {ripple:14.2e} {str(ok):>13}")"""),
            code("""\
# Reconstruction error follows the COLA verdict.
fs_c = 1000.0
t_c = np.arange(0, 1.0, 1 / fs_c)
x_c = signals.chirp(t_c, 20.0, 300.0)
for win_name, hop in [("hann", nperseg // 2), ("hann", nperseg // 3), ("boxcar", nperseg // 2)]:
    f_, tt_, Z = transforms.stft(x_c, fs_c, nperseg=nperseg,
                                 noverlap=nperseg - hop, window=win_name)
    rec = transforms.istft(Z, fs_c, nperseg=nperseg,
                           noverlap=nperseg - hop, window=win_name)
    m = min(rec.size, x_c.size)
    err = float(np.max(np.abs(rec[:m] - x_c[:m])))
    print(f"{win_name:>8}  hop {hop:4d}   max reconstruction error {err:.3e}")"""),
            md(r"""## Application

応用: 音声・音楽(音符の検出)、機械の異常振動、脳波(EEG)、レーダー。

wavelet と STFT の使い分けは、**知りたいものが過渡か定常か** で決まります。
定常なトーンの周波数を精密に測るなら STFT、
立ち上がりの時刻を測るなら wavelet が向いています。"""),
            md(r"""## Exercises

1. **窓幅のトレードオフ**: 同じチャープに対し `nperseg` を 64, 256, 1024 と変えて
   STFT を取り、時間分解能と周波数分解能が逆向きに動くことを数値で示せ。
2. **バースト検出**: 上の CWT で、200 Hz バーストの中心時刻を
   $|W|$ の最大値から推定せよ。STFT(`nperseg=256`)で同じことをするとどれだけずれるか。
3. **COLA の破れ**: `boxcar` 窓と 50% 重ねの組で再構成誤差が大きくなる理由を、
   重ね合わせ和の形から説明せよ。
4. **定 Q の確認**: Morlet の中心周波数 $f_c$ を変えると Q がどう変わるか測れ。
   $f_c$ が大きいほど何が良くなり、何が悪くなるか。
5. **スペクトル漏れ**: 窓を掛けない(boxcar)場合と Hann 窓の場合で、
   非整数周期の正弦波のスペクトルを比較し、漏れの量を dB で示せ。

解答は 10 章にある。"""),
        ],
    ),
)

# ========================================================================== #
# 09 — applications: signal, image, finance, ML  (lighter, runnable)
# ========================================================================== #
write_nb(
    "09_applications_signal_image_finance_ml",
    [
        md(r"""# 09. 応用 — 信号・画像・金融・機械学習

**学習目標**: これまでの道具を実データ風の題材で使う。音(スペクトログラム)、画像
(2D FFT・圧縮)、金融時系列(探索的周波数解析と **その限界**)、そして ML への接続。"""),
        code(SETUP),
        md(r"""## 1. 音声信号 — スペクトログラム(07 章の再訪)

チャープ音の時間周波数表示。音の解析の基本図です。"""),
        code("""\
fs = 2000.0
t, x = datasets.make_chirp(fs=fs, duration=2.0, f0=30.0, f1=500.0)
f, tt, S = transforms.spectrogram_db(x, fs, nperseg=256)
plotting.plot_spectrogram(f, tt, S, fmax=600, title="audio-like chirp")
plt.show()"""),
        md(r"""## 2. 画像の 2D FFT

画像は 2 次元信号。2D FFT は「どの向き・どの細かさの縞模様」が含まれるかを示します。
中心が低周波(全体の明暗・なだらかな変化)、外側が高周波(エッジ・細部)です。"""),
        code("""\
img = datasets.make_test_image(128)
plotting.plot_image_and_spectrum(img)
plt.show()"""),
        md(r"""### 低周波だけで再構成(ぼかし)と係数間引き圧縮

中心の低周波だけ残すと **ぼけた**(なめらかな)画像になります。
大きい係数だけ残す(間引く)と、少ないデータで元画像を近似できます = 変換符号化(JPEG の精神)。"""),
        code("""\
# Keep only low frequencies (blur) vs keep only the largest coefficients (compress).
F = np.fft.fftshift(np.fft.fft2(img))

def keep_central(spec, frac):
    n = spec.shape[0]
    r = max(1, int(n * frac / 2))
    c = n // 2
    mask = np.zeros_like(spec, dtype=bool)
    mask[c - r:c + r, c - r:c + r] = True
    return spec * mask

low = np.fft.ifft2(np.fft.ifftshift(keep_central(F, 0.12))).real

mag = np.abs(F)
keep = int(0.03 * mag.size)                          # keep top 3% of coefficients
thr = np.partition(mag.ravel(), -keep)[-keep]
Fc = np.where(mag >= thr, F, 0)
comp = np.fft.ifft2(np.fft.ifftshift(Fc)).real
ratio = mag.size / np.count_nonzero(Fc)
rel_err = np.linalg.norm(img - comp) / np.linalg.norm(img)

fig, ax = plt.subplots(1, 3, figsize=(11, 3.6))
for a, im, title in zip(ax, [img, low, comp],
                        ["original", "low-freq only (blur)",
                         f"top-3% coeffs (~{ratio:.0f}x, err {rel_err:.1%})"]):
    a.imshow(im, cmap="gray"); a.set_title(title, fontsize=9); a.axis("off")
plt.show()"""),
        md(r"""### ハイパス=エッジ、方向フィルタ

高周波だけ残すと **エッジ** が出る。周波数面の中央の行(または列)だけ残すと、
特定方向のなめらかな構造だけが残る(方向選択フィルタ)。"""),
        code("""\
# High-pass = edges; keeping a center row/column band keeps one spatial direction.
F2 = np.fft.fftshift(np.fft.fft2(img))
nimg = F2.shape[0]
cc = nimg // 2
block = np.zeros_like(F2, dtype=bool)
block[cc - 8:cc + 8, cc - 8:cc + 8] = True
high = np.fft.ifft2(np.fft.ifftshift(F2 * ~block)).real      # drop low freqs -> edges
row = np.zeros_like(F2, dtype=bool); row[cc - 3:cc + 3, :] = True
col = np.zeros_like(F2, dtype=bool); col[:, cc - 3:cc + 3] = True
horiz = np.fft.ifft2(np.fft.ifftshift(F2 * row)).real        # keep low vertical freq
vert = np.fft.ifft2(np.fft.ifftshift(F2 * col)).real         # keep low horizontal freq
fig, ax = plt.subplots(1, 3, figsize=(11, 3.8))
for a, im_, ttl in zip(ax, [high, horiz, vert],
                       ["high-pass = edges", "keep low vertical freq", "keep low horizontal freq"],
                       strict=True):
    a.imshow(im_, cmap="gray"); a.set_title(ttl, fontsize=9); a.axis("off")
plt.show()"""),
        md(r"""## 3. 金融時系列 — 探索的周波数解析とその限界

合成した日次価格の対数リターンを FFT します。ただし金融では結果の解釈に強い注意が要ります。"""),
        code("""\
price = datasets.load_price_series(n=1024, seed=0)   # synthetic: random walk + faint 5-day cycle
ret = np.diff(np.log(price))
freqs, amp = transforms.amplitude_spectrum(ret - ret.mean(), fs=1.0)  # fs = 1 / day

fig, ax = plt.subplots(1, 2, figsize=(11, 3.2))
ax[0].plot(price, color="#1f77b4"); ax[0].set_title("synthetic price"); ax[0].set_xlabel("day")
ax[0].grid(alpha=.25)
ax[1].plot(freqs, amp, color="#d62728"); ax[1].set_title("amplitude spectrum of log-returns")
ax[1].set_xlabel("frequency [1/day]"); ax[1].grid(alpha=.25)
plt.show()"""),
        md(r"""```{admonition} 金融時系列でフーリエ解析を使うときの注意(必読)
:class: warning
- **非定常**: 株価・リターンは時間とともに統計的性質が変わりやすい。FFT は「定常で周期的」を
  暗に仮定するので、スペクトルの山を素朴に「周期」と読んではいけない。
- **見かけの周期性**: 有限データではランダムノイズでもスペクトルに山が立つ(偶然のピーク)。
  有意性は帰無分布やサロゲートデータと比較して評価すべき。
- **予測力の保証なし**: FFT は **探索的分析** には有用だが、過去のスペクトルが将来の値動きを
  予測する保証はない。
- **将来情報の混入(look-ahead)**: 周波数フィルタ(とくに位相ゼロ/両側フィルタ)は
  未来の値を使うため、バックテストに使うと **リーク** する。因果的(片側)フィルタを使うこと。
```"""),
        md(r"""## 4. 機械学習への接続(概念)

- **Fourier features**: 入力 $x$ を $[\cos(2\pi b x),\sin(2\pi b x)]$ に写すと、ニューラルネットが
  高周波関数を学習しやすくなる(座標 MLP・NeRF の鍵)。
- **スペクトル前処理**: 音声・振動の分類では、生波形より **スペクトログラム** を入力にすると強い。
- **Neural operators(FNO)**: 偏微分方程式の解作用素を **フーリエ空間** で学習する(08 章の延長)。
- 線形代数の PCA/SVD(`analytics/linear_algebra`)とも双子: どちらも「良い基底へ射影して
  少数成分で表す」発想。"""),
        md(r"""## 5. メル尺度スペクトログラム

人間の聴覚は周波数を対数的に聞きます。メル尺度

$$
m(f) = 2595 \log_{10}\!\left(1 + \frac{f}{700}\right)
$$

は、この非線形性を近似したものです。
メルスペクトログラムは、線形なスペクトログラムに **メル間隔の三角フィルタバンク** を掛けて
帯域を束ねたものです。音声認識・音楽解析の標準的な入力になっています。

`librosa` は使いません。フィルタバンクは 15 行で書けて、
中身を見せることが本書の目的だからです。"""),
        code("""\
# A mel filterbank, written out, applied to a synthesised two-note signal.
def mel_filterbank(n_mels, n_fft, fs_m, fmin=0.0, fmax=None):
    fmax = fmax or fs_m / 2
    to_mel = lambda f: 2595.0 * np.log10(1.0 + f / 700.0)
    to_hz = lambda m: 700.0 * (10.0 ** (m / 2595.0) - 1.0)
    edges = to_hz(np.linspace(to_mel(fmin), to_mel(fmax), n_mels + 2))
    bins = np.floor((n_fft + 1) * edges / fs_m).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for i in range(n_mels):
        lo, mid, hi = bins[i], bins[i + 1], bins[i + 2]
        if mid > lo:
            fb[i, lo:mid] = (np.arange(lo, mid) - lo) / (mid - lo)
        if hi > mid:
            fb[i, mid:hi] = (hi - np.arange(mid, hi)) / (hi - mid)
    return fb, edges[1:-1]

fs_m = 8000.0
t_m = np.arange(0, 1.2, 1 / fs_m)
note = lambda f0, t0, dur: (np.exp(-((t_m - t0) / dur) ** 2)
                            * sum(np.sin(2 * np.pi * k * f0 * t_m) / k for k in (1, 2, 3)))
x_m = note(220.0, 0.3, 0.10) + note(660.0, 0.85, 0.10)

nperseg_m = 512
f_m, tt_m, S = transforms.stft(x_m, fs_m, nperseg=nperseg_m, noverlap=nperseg_m * 3 // 4)
power = np.abs(S) ** 2
fb, mel_centers = mel_filterbank(40, nperseg_m, fs_m, fmin=50.0, fmax=3500.0)
mel_spec = fb @ power
mel_db = 10 * np.log10(mel_spec + 1e-12)

fig, ax = plt.subplots(1, 2, figsize=(11, 3.4))
ax[0].plot(np.fft.rfftfreq(nperseg_m, 1 / fs_m), fb.T, lw=0.7)
ax[0].set_xlim(0, 3500); ax[0].set_title("mel filterbank (40 bands)")
ax[0].set_xlabel("frequency [Hz]"); ax[0].grid(alpha=0.25)
ax[1].pcolormesh(tt_m, mel_centers, mel_db - mel_db.max(), shading="auto",
                 cmap="magma", vmin=-60, vmax=0)
ax[1].set_title("mel spectrogram [dB]"); ax[1].set_xlabel("t [s]")
ax[1].set_ylabel("mel-band centre [Hz]")
plt.tight_layout()
plt.show()
print(f"linear bins {power.shape[0]} -> mel bands {mel_spec.shape[0]}"
      f"  ({power.shape[0] / mel_spec.shape[0]:.1f}x compression)")"""),
        md(r"""低域は細かく、高域は粗く束ねられているのが図から読めます。
情報を捨てているのに音声認識の性能が上がるのは、
**捨てているのが人間が区別しない差だから** です。
表現の設計はいつも「何を捨てるか」の設計でもあります。"""),
        md(r"""## 6. Fourier features — 高周波を学習させる

素の座標 $x$ を入力にした MLP は高周波の関数を学習できません(spectral bias)。
$x$ を

$$
\gamma(x) = [\cos(2\pi b_1 x), \sin(2\pi b_1 x), \dots, \cos(2\pi b_m x), \sin(2\pi b_m x)]
$$

に写してから線形回帰すると、同じ容量で高周波が入ります。
ここでは線形回帰(閉形式)で効果だけを取り出します。"""),
        code("""\
# Raw coordinate vs Fourier features on a high-frequency target.
rng_ff = np.random.default_rng(0)
xt = np.sort(rng_ff.uniform(0, 1, 256))
target = lambda z: np.sin(2 * np.pi * 9 * z) + 0.4 * np.sin(2 * np.pi * 23 * z)
yt = target(xt)
xq = np.linspace(0, 1, 1000)

def poly_features(z, degree):
    return np.vander(z, degree + 1, increasing=True)

def fourier_features(z, m, scale=12.0):
    b = np.arange(1, m + 1) * scale / m
    ang = 2 * np.pi * np.outer(z, b)
    return np.column_stack([np.ones_like(z), np.cos(ang), np.sin(ang)])

print(f"{'representation':>26} {'params':>8} {'test RMSE':>11}")
for name, phi_fn in [("polynomial degree 15", lambda z: poly_features(z, 15)),
                     ("polynomial degree 31", lambda z: poly_features(z, 31)),
                     ("Fourier features m=16", lambda z: fourier_features(z, 16, 32.0))]:
    A = phi_fn(xt)
    w, *_ = np.linalg.lstsq(A, yt, rcond=None)
    pred = phi_fn(xq) @ w
    rmse = float(np.sqrt(np.mean((pred - target(xq)) ** 2)))
    print(f"{name:>26} {A.shape[1]:8d} {rmse:11.4f}")

A = fourier_features(xt, 16, 32.0)
w_ff, *_ = np.linalg.lstsq(A, yt, rcond=None)
w_poly, *_ = np.linalg.lstsq(poly_features(xt, 31), yt, rcond=None)
fig, ax = plt.subplots(figsize=(9, 3))
ax.plot(xq, target(xq), color="#999", lw=1.2, label="target")
ax.plot(xq, poly_features(xq, 31) @ w_poly, label="polynomial degree 31")
ax.plot(xq, fourier_features(xq, 16, 32.0) @ w_ff, "--", color="#d62728",
        label="Fourier features m=16")
ax.set_ylim(-2.5, 2.5); ax.legend(fontsize=8); ax.grid(alpha=0.25)
ax.set_title("the basis decides which frequencies are reachable")
plt.show()"""),
        md(r"""## 7. ウェルチ法とサロゲート検定 — 偶然のピークを棄却する

単一のピリオドグラムは分散が大きく、$n$ を増やしても減りません
(推定量として **一致性がない**)。ウェルチ法はデータを重なりのある区間に分け、
区間ごとのピリオドグラムを平均します。分散が下がる代わりに周波数分解能が落ちます。

そのうえで、「このピークは偶然か」に答えるにはサロゲートデータが要ります。
**位相をランダム化** して振幅スペクトルだけ保った系列を多数作り、
そこから得られるピーク高の分布と比べます。"""),
        code("""\
# Welch averaging, then a phase-randomised surrogate test for the peak.
from scipy import signal as sps_signal

rng_s = np.random.default_rng(1)
fs_s = 1.0
n_s = 2048
t_s = np.arange(n_s)
# AR(1) noise with a weak periodic component buried in it
noise = np.zeros(n_s)
for i in range(1, n_s):
    noise[i] = 0.6 * noise[i - 1] + rng_s.normal()
series = noise + 0.55 * np.sin(2 * np.pi * 0.11 * t_s)

f_p, P_single = sps_signal.periodogram(series, fs=fs_s)
f_w, P_welch = sps_signal.welch(series, fs=fs_s, nperseg=256, noverlap=128)
print(f"periodogram: {f_p.size} bins, relative sd of estimate stays ~1")
print(f"Welch      : {f_w.size} bins, averaged over "
      f"{(n_s - 128) // 128} segments")

def surrogate_max(x_obs, n_sur=500, seed=2):
    r = np.random.default_rng(seed)
    spec_obs = np.fft.rfft(x_obs)
    mags = np.abs(spec_obs)
    peaks = np.empty(n_sur)
    for i in range(n_sur):
        phases = r.uniform(0, 2 * np.pi, mags.size)
        phases[0] = 0.0
        sur = np.fft.irfft(mags * np.exp(1j * phases), n=x_obs.size)
        _, Pw = sps_signal.welch(sur, fs=fs_s, nperseg=256, noverlap=128)
        peaks[i] = Pw[1:].max()
    return peaks

peaks = surrogate_max(series)
observed = float(P_welch[1:].max())
thresh = float(np.quantile(peaks, 0.95))
print(f"\\nobserved peak      : {observed:.4f} at f = {f_w[1:][np.argmax(P_welch[1:])]:.4f}")
print(f"surrogate 95% level: {thresh:.4f}")
print(f"verdict            : {'significant' if observed > thresh else 'not distinguishable from noise'}")

fig, ax = plt.subplots(1, 2, figsize=(11, 3.2))
ax[0].semilogy(f_p[1:], P_single[1:], color="#bbb", lw=0.7, label="single periodogram")
ax[0].semilogy(f_w[1:], P_welch[1:], color="#1f77b4", lw=1.5, label="Welch average")
ax[0].axhline(thresh, color="#d62728", ls="--", lw=1, label="surrogate 95%")
ax[0].set_xlabel("frequency"); ax[0].legend(fontsize=8); ax[0].grid(alpha=0.25)
ax[0].set_title("averaging trades resolution for variance")
ax[1].hist(peaks, bins=30, color="#999")
ax[1].axvline(observed, color="#d62728", lw=2, label="observed")
ax[1].set_title("surrogate distribution of the peak"); ax[1].legend(fontsize=8)
plt.tight_layout()
plt.show()"""),
        md(r"""サロゲートは **振幅スペクトルを保ったまま位相だけを壊す** ので、
「同じ自己相関構造を持つが周期成分は無い」系列になります。
AR(1) のような有色ノイズは素朴なピリオドグラムに低周波の山を作るので、
白色ノイズを帰無仮説に置くと誤検出します。サロゲートはそこを正します。"""),
        md(r"""## 8. 実画像について

本書は外部データのダウンロードに依存しない方針なので、
`scikit-image` の `data.camera()` のような実写真は使いません。
代わりに §2 の合成テスト画像(`datasets.make_test_image`)で
同じ性質(方向性のあるエッジ ↔ スペクトルの十字、周期パターン ↔ 離散ピーク)を示しています。

実画像で試したい場合は、`skimage` を入れて画像を差し替えれば
以降のコードはそのまま動きます。**手法の側に画像固有の仮定は入っていません。**"""),
        md(r"""## Exercises

1. **2D の分離**: 合成テスト画像に対し、低周波だけを残した再構成と
   高周波だけを残した再構成を作り、前者がぼけ・後者がエッジになる理由を述べよ。
2. **メルの圧縮率**: メル帯域数を 20, 40, 80 と変えて、
   元のスペクトログラムとの再構成誤差がどう変わるか測れ。
3. **Fourier features のスケール**: `scale` を 4, 12, 64 と変えて汎化誤差を測り、
   大きすぎるとどうなるかを示せ。ノイズを加えた場合はどうか。
4. **ウェルチの分解能**: `nperseg` を 64, 256, 1024 と変え、
   分散と周波数分解能のトレードオフを、ピークの高さと幅で定量化せよ。
5. **サロゲートの必要性**: 白色ノイズを帰無仮説にした場合と
   位相ランダム化サロゲートを使った場合で、AR(1) ノイズに対する
   誤検出率がどれだけ違うか測れ。

解答は 10 章にある。"""),
    ],
)
print("part 8 (07, 09) done")

# ========================================================================== #
# 10 — exercise solutions
# ========================================================================== #
write_nb(
    "10_exercise_solutions",
    [
        md(r"""# 10. 演習の解答

01–09 章の演習 40 問の解答。問題文を 1 行で再掲したうえで、
導出を求めるものには式変形を、測定を求めるものには実行できるコードを置いた。

| 章 | 問題数 | 章 | 問題数 |
|---|---:|---|---:|
| 01 波・複素数・内積 | 4 | 06 DFT/FFT・標本化 | 4 |
| 02 フーリエ級数 | 4 | 07 時間周波数解析 | 5 |
| 03 収束・エネルギー | 4 | 08 PDE とスペクトル法 | 4 |
| 04 フーリエ変換 | 5 | 09 応用 | 5 |
| 05 畳み込みとフィルタ | 5 | | |"""),
        code(SETUP),
        md(r"""## 01 章 — 波・複素数・内積"""),
        md(r"""### 01-1 位相と余弦

> $\sin(\theta+\pi/2)=\cos\theta$ を Euler の公式から示せ。

$\sin\phi = \frac{e^{i\phi}-e^{-i\phi}}{2i}$ に $\phi=\theta+\pi/2$ を入れる。
$e^{\pm i\pi/2} = \pm i$ なので

$$
\sin(\theta+\tfrac{\pi}{2})
= \frac{i e^{i\theta} - (-i) e^{-i\theta}}{2i}
= \frac{e^{i\theta} + e^{-i\theta}}{2} = \cos\theta
$$

位相を $\pi/2$ 進めることは、複素平面で $i$ を掛けること(90 度回転)に等しい。"""),
        code("""\
th = np.linspace(0, 4 * np.pi, 2001)
print(f"max |sin(θ+π/2) - cos θ| = {np.max(np.abs(np.sin(th + np.pi / 2) - np.cos(th))):.2e}")"""),
        md(r"""### 01-2 直交の破れ

> Gram 行列を $[0, 2.3)$ で作ると単位行列からどれだけずれるか。

直交性は「周期の整数倍で積分する」ことに依存している。
$2.3$ は $2\pi$ の整数倍でないので、内積に **端数の寄与** が残る。"""),
        code("""\
def gram(upper, n_max=5, n_pts=20001):
    tt = np.linspace(0, upper, n_pts, endpoint=False)
    basis = np.array([np.exp(1j * k * tt) for k in range(1, n_max + 1)])
    return (basis @ basis.conj().T) * (tt[1] - tt[0]) / upper

for upper, label in [(2 * np.pi, "[0, 2π)  整数周期"), (2.3, "[0, 2.3)  端数あり")]:
    G = gram(upper)
    off = np.max(np.abs(G - np.eye(G.shape[0])))
    print(f"{label:22s}  max |G - I| = {off:.3e}")"""),
        md(r"""### 01-3 平均パワー

> $A\sin(2\pi f t)$ の 1 周期平均パワーが $A^2/2$ になることを確かめよ。

$$
\frac{1}{T}\int_0^T A^2\sin^2(2\pi f t)\,dt
= \frac{A^2}{T}\int_0^T \frac{1-\cos(4\pi f t)}{2}dt = \frac{A^2}{2}
$$

第 2 項は 1 周期の整数倍で積分すると消える。実効値が $A/\sqrt{2}$ になる根拠でもある。"""),
        code("""\
for A, f in [(1.0, 3.0), (2.5, 7.0)]:
    tt = np.linspace(0, 1 / f, 100001)
    print(f"A = {A}, f = {f}:  measured {np.mean((A * np.sin(2 * np.pi * f * tt)) ** 2):.6f}"
          f"   A²/2 = {A**2 / 2:.6f}")"""),
        md(r"""### 01-4 射影(のこぎり波)

> $f(x)=x$ の $b_n$ を数値計算し $2(-1)^{n+1}/n$ と比べよ。

$$
b_n = \frac{1}{\pi}\int_{-\pi}^{\pi} x \sin(nx)\,dx
= \frac{2}{\pi}\int_0^{\pi} x\sin(nx)\,dx
$$

部分積分して $\int_0^\pi x\sin(nx)dx = \frac{\pi(-1)^{n+1}}{n}$ なので $b_n = 2(-1)^{n+1}/n$。
$1/n$ の減衰は、$x$ を周期 $2\pi$ で延長したときに端点で **跳びが生じる** ことの帰結である。"""),
        code("""\
a, b = transforms.trig_coeffs(lambda z: z, n_max=8, period=2 * np.pi)
print(f"{'n':>3} {'numeric b_n':>13} {'2(-1)^(n+1)/n':>16}")
for n in range(1, 9):
    print(f"{n:3d} {b[n - 1]:13.6f} {2 * (-1) ** (n + 1) / n:16.6f}")"""),
        md(r"""## 02 章 — フーリエ級数"""),
        md(r"""### 02-1 のこぎり波の係数

01-4 と同じ。`trig_coeffs` の出力が $2(-1)^{n+1}/n$ に一致する。
上のセルで確認済みなので繰り返さない。"""),
        md(r"""### 02-2 三角波の滑らかさ

> 三角波の係数が $1/n^2$ で減衰することを log-log で確かめ、矩形波($1/n$)と比べよ。

減衰の速さは滑らかさで決まる。関数が $C^{k}$ で $k+1$ 階微分に跳びがあるとき、
係数は $|c_n| \sim n^{-(k+2)}$ で減る。矩形波は関数自体に跳びがあるので $1/n$、
三角波は連続だが微分に跳びがあるので $1/n^2$ になる。"""),
        code("""\
tt = np.linspace(-np.pi, np.pi, 8192, endpoint=False)
for name, fn, expect in [("square", lambda z: signals.square_wave(z, 1 / (2 * np.pi)), 1),
                         ("triangle", lambda z: signals.triangle_wave(z, 1 / (2 * np.pi)), 2)]:
    a_, b_ = transforms.trig_coeffs(fn, n_max=40, period=2 * np.pi)
    mag = np.hypot(a_[1:], b_[1:])
    ns = np.arange(1, mag.size + 1)
    keep = mag > 1e-9
    slope = np.polyfit(np.log(ns[keep]), np.log(mag[keep]), 1)[0]
    print(f"{name:>9}: measured slope {slope:6.2f}   expected {-expect}")

fig, ax = plt.subplots(figsize=(7, 3.2))
for name, fn in [("square", lambda z: signals.square_wave(z, 1 / (2 * np.pi))),
                 ("triangle", lambda z: signals.triangle_wave(z, 1 / (2 * np.pi)))]:
    a_, b_ = transforms.trig_coeffs(fn, n_max=40, period=2 * np.pi)
    mag = np.hypot(a_[1:], b_[1:])
    ns = np.arange(1, mag.size + 1)
    keep = mag > 1e-9
    ax.loglog(ns[keep], mag[keep], "o-", ms=3, label=name)
ax.set_xlabel("n"); ax.set_ylabel("|coefficient|"); ax.legend(); ax.grid(alpha=0.3, which="both")
ax.set_title("smoothness sets the decay rate")
plt.show()"""),
        md(r"""### 02-3 偶奇分解

> 偶部が余弦のみ、奇部が正弦のみで表せることを示せ。

$f_e(x)=\frac{f(x)+f(-x)}{2}$ は偶関数で、$\int f_e(x)\sin(nx)dx$ は
奇関数の対称区間積分なので 0。よって $b_n=0$。奇部も同様に $a_n=0$。"""),
        code("""\
rng_e = np.random.default_rng(0)
coef = rng_e.normal(size=6)
f_any = lambda z: sum(c * np.sin((k + 1) * z + 0.7 * k) for k, c in enumerate(coef))
f_even = lambda z: 0.5 * (f_any(z) + f_any(-z))
f_odd = lambda z: 0.5 * (f_any(z) - f_any(-z))

for name, fn in [("even part", f_even), ("odd part", f_odd)]:
    a_, b_ = transforms.trig_coeffs(fn, n_max=8, period=2 * np.pi)
    print(f"{name:>10}:  max|a_n| = {np.max(np.abs(a_)):.2e}   max|b_n| = {np.max(np.abs(b_)):.2e}")"""),
        md(r"""### 02-4 Gibbs のオーバーシュート

> 倍音数 $N$ を変えても overshoot 比が一定に近づくことを示せ。

跳びの大きさに対する行き過ぎの比は $N\to\infty$ で

$$
\frac{1}{\pi}\int_0^\pi \frac{\sin u}{u}du - \frac{1}{2} \approx 0.0895
$$

に収束する。**振動の幅は縮むが高さは縮まない**。有限個の滑らかな関数で
不連続を表そうとする限り消えない、原理的な現象である。"""),
        code("""\
tt = np.linspace(-np.pi, np.pi, 20001)
print(f"{'N':>5} {'overshoot ratio':>18}")
for N in [5, 11, 25, 51, 101, 201]:
    partial = signals.square_wave_partial_sum(tt, 1 / (2 * np.pi), N)
    print(f"{N:5d} {(partial.max() - 1.0) / 2.0:18.5f}")
print(f"{'limit':>5} {0.0894898722:18.5f}")"""),
        md(r"""## 03 章 — 収束・エネルギー・Parseval"""),
        md(r"""### 03-1 Basel 型の和

> 矩形波の Parseval から $\sum_{n\ \text{odd}} 1/n^2 = \pi^2/8$ を導け。

振幅 1 の矩形波は $f(x)=\frac{4}{\pi}\sum_{n\ \text{odd}} \frac{\sin nx}{n}$。
Parseval は $\frac{1}{\pi}\int_{-\pi}^{\pi}|f|^2 dx = \sum_n (a_n^2+b_n^2)$ で、
左辺は $2$、右辺は $\sum_{n\ \text{odd}} \left(\frac{4}{\pi n}\right)^2$。したがって

$$
2 = \frac{16}{\pi^2}\sum_{n\ \text{odd}} \frac{1}{n^2}
\;\Longrightarrow\;
\sum_{n\ \text{odd}} \frac{1}{n^2} = \frac{\pi^2}{8}
$$"""),
        code("""\
odd = np.arange(1, 200001, 2)
print(f"partial sum       = {np.sum(1 / odd.astype(float) ** 2):.10f}")
print(f"π²/8              = {np.pi**2 / 8:.10f}")"""),
        md(r"""### 03-2 三角波の Parseval

> 三角波で Parseval を数値確認し、累積エネルギー図を描け。"""),
        code("""\
tt = np.linspace(-np.pi, np.pi, 16384, endpoint=False)
tri = signals.triangle_wave(tt, 1 / (2 * np.pi))
a_, b_ = transforms.trig_coeffs(lambda z: signals.triangle_wave(z, 1 / (2 * np.pi)),
                                n_max=60, period=2 * np.pi)
lhs = np.mean(tri**2) * 2
rhs = a_[0] ** 2 / 2 * 2 + np.sum(a_[1:] ** 2 + b_[1:] ** 2)
print(f"(1/π)∫|f|²  = {lhs:.6f}")
print(f"Σ (aₙ²+bₙ²) = {rhs:.6f}   (60 harmonics)")

cum = np.cumsum(a_[1:] ** 2 + b_[1:] ** 2) / rhs
fig, ax = plt.subplots(figsize=(7, 3))
ax.plot(np.arange(1, cum.size + 1), cum, "o-", ms=3)
ax.axhline(0.99, color="#d62728", ls="--", lw=1, label="99 % of energy")
ax.set_xlabel("harmonics kept"); ax.set_ylabel("cumulative energy fraction")
ax.legend(fontsize=8); ax.grid(alpha=0.3)
plt.show()
print(f"99 % のエネルギーに必要な倍音数: {int(np.argmax(cum >= 0.99)) + 1}")"""),
        md(r"""### 03-3 MSE は小さいが max error は大きい例

> そのような例を作って図で示せ。

矩形波の部分和がまさにこれである。Gibbs の耳が跳びの近傍に残るので
$\|f - S_N\|_\infty$ は 0 に行かない。一方エネルギー(2 乗)で測ると、
耳の幅が $O(1/N)$ で縮むので $\|f-S_N\|_2 \to 0$ になる。
**収束は測り方で結論が変わる。**"""),
        code("""\
tt = np.linspace(-np.pi, np.pi, 20001)
target = signals.square_wave(tt, 1 / (2 * np.pi))
print(f"{'N':>5} {'L2 error':>12} {'max error':>12}")
for N in [5, 21, 81, 321]:
    partial = signals.square_wave_partial_sum(tt, 1 / (2 * np.pi), N)
    l2 = float(np.sqrt(np.mean((partial - target) ** 2)))
    print(f"{N:5d} {l2:12.5f} {float(np.max(np.abs(partial - target))):12.5f}")
print("\\nL2 は 0 に落ちるが max は落ちない")"""),
        md(r"""### 03-4 $|\sin x|$ の係数減衰

> 減衰の次数を測り、滑らかさと整合するか調べよ。

$|\sin x|$ は連続だが $x=0,\pi$ で微分に跳びがある($C^0$)。
予測される減衰は $1/n^2$。実際、$|\sin x|$ は周期 $\pi$ を持つので
偶数次の余弦係数だけが残り $a_{2k} = -\frac{4}{\pi(4k^2-1)} \sim k^{-2}$ になる。"""),
        code("""\
a_, b_ = transforms.trig_coeffs(lambda z: np.abs(np.sin(z)), n_max=40, period=2 * np.pi)
mag = np.hypot(a_[1:], b_[1:])
ns = np.arange(1, mag.size + 1)
keep = mag > 1e-8
slope = np.polyfit(np.log(ns[keep]), np.log(mag[keep]), 1)[0]
print(f"measured decay slope = {slope:.2f}  (expected -2 for a C⁰ function)")
print(f"{'k':>3} {'a_2k numeric':>14} {'-4/(π(4k²-1))':>16}")
for k in range(1, 6):
    print(f"{k:3d} {a_[2 * k]:14.6f} {-4 / (np.pi * (4 * k**2 - 1)):16.6f}")"""),
        md(r"""## 04 章 — フーリエ変換"""),
        md(r"""### 04-1 不確定性

> $e^{-\pi a x^2}$ の時間幅と周波数幅の積が $a$ によらないことを確かめよ。

ガウス関数 $e^{-\pi a x^2}$ の変換は $a^{-1/2}e^{-\pi\xi^2/a}$。
密度として正規化した標準偏差は $\sigma_x = \frac{1}{2\sqrt{\pi a}}$、
$\sigma_\xi = \frac{\sqrt a}{2\sqrt\pi}$ なので

$$
\sigma_x \sigma_\xi = \frac{1}{4\pi}
$$

$a$ が消える。これは不確定性原理 $\sigma_x\sigma_\xi \ge \frac{1}{4\pi}$ の
**等号が成り立つ唯一の関数** がガウス関数であることの現れである。"""),
        code("""\
xg = np.linspace(-12, 12, 8192)
def spread(grid, dens):
    w = np.abs(dens) ** 2
    w = w / np.trapezoid(w, grid)
    mu = np.trapezoid(grid * w, grid)
    return float(np.sqrt(np.trapezoid((grid - mu) ** 2 * w, grid)))

print(f"{'a':>6} {'σ_x':>10} {'σ_ξ':>10} {'product':>10} {'1/(4π)':>10}")
for a_val in [0.25, 1.0, 4.0]:
    fx = np.exp(-np.pi * a_val * xg**2)
    dt_ = xg[1] - xg[0]
    Fx = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(fx))) * dt_
    xi_ = np.fft.fftshift(np.fft.fftfreq(xg.size, d=dt_))
    sx, sxi = spread(xg, fx), spread(xi_, Fx)
    print(f"{a_val:6.2f} {sx:10.5f} {sxi:10.5f} {sx * sxi:10.6f} {1 / (4 * np.pi):10.6f}")"""),
        md(r"""### 04-2 矩形と sinc

> $\mathrm{rect}$ の変換が sinc になることを示し、裾が $1/\xi$ でしか減らない理由を述べよ。

$$
\int_{-1/2}^{1/2} e^{-2\pi i x\xi} dx
= \frac{\sin(\pi\xi)}{\pi\xi} = \mathrm{sinc}(\xi)
$$

裾の減衰は 03 章と同じ論理である。$\mathrm{rect}$ は **関数自体に跳び** があるので、
変換の減衰は $1/\xi$ にしかならない。滑らかさと減衰は変換の両側で対になっている。"""),
        code("""\
xg = np.linspace(-16, 16, 16384)
rect = (np.abs(xg) <= 0.5).astype(float)
dt_ = xg[1] - xg[0]
R = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(rect))) * dt_
xi_ = np.fft.fftshift(np.fft.fftfreq(xg.size, d=dt_))
sinc = np.sinc(xi_)
band = np.abs(xi_) < 12
print(f"max |numeric - sinc| on |ξ|<12 = {np.max(np.abs(R[band].real - sinc[band])):.2e}")
peaks = np.abs(xi_[(np.abs(xi_) > 1) & (np.abs(xi_) < 40)])
print("envelope check: |sinc(ξ)| * |ξ| stays O(1) ->",
      f"{np.max(np.abs(np.sinc(peaks)) * peaks):.4f}")"""),
        md(r"""### 04-3 微分は高周波を増幅する

> $f'' \leftrightarrow -(2\pi\xi)^2\hat f$ を確かめ、微分がノイズに弱い理由を述べよ。

微分は周波数に $2\pi i\xi$ を掛ける。$n$ 階なら $(2\pi i \xi)^n$ で、
**高周波ほど強く増幅される**。信号のノイズは典型的に広帯域なので、
微分すると高周波のノイズだけが持ち上がり SN 比が落ちる。
実務で微分の前に平滑化を入れるのはこのためである。"""),
        code("""\
xg = np.linspace(-8, 8, 4096)
dt_ = xg[1] - xg[0]
g = np.exp(-np.pi * xg**2)
G = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(g))) * dt_
xi_ = np.fft.fftshift(np.fft.fftfreq(xg.size, d=dt_))
d2 = np.gradient(np.gradient(g, dt_), dt_)
D2 = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(d2))) * dt_
print(f"max rel.err of f'' <-> -(2πξ)² fhat : "
      f"{np.max(np.abs(D2 - (-(2 * np.pi * xi_) ** 2) * G)) / np.max(np.abs(D2)):.2e}")

rng_d = np.random.default_rng(0)
noisy = g + 0.01 * rng_d.normal(size=g.size)
print(f"\\nSNR of signal            : {np.std(g) / 0.01:8.1f}")
print(f"SNR after one derivative : "
      f"{np.std(np.gradient(g, dt_)) / np.std(np.gradient(noisy - g, dt_)):8.1f}")"""),
        md(r"""### 04-4 復調

> $g(x)\cos(2\pi f_0x)$ から $g$ を取り出せ。

もう一度 $\cos(2\pi f_0 x)$ を掛けると

$$
g\cos^2(2\pi f_0 x) = \frac{g}{2} + \frac{g}{2}\cos(4\pi f_0 x)
$$

第 1 項がベースバンド、第 2 項が $2f_0$ 付近。ローパスで第 2 項を落とし、2 倍すれば $g$ に戻る。"""),
        code("""\
fs_dm = 2000.0
t_dm = np.arange(0, 1.0, 1 / fs_dm)
g_base = signals.gaussian_pulse(t_dm, t0=0.5, width=0.05) + 0.4 * signals.sine(t_dm, 6.0)
f0_dm = 200.0
modulated = g_base * np.cos(2 * np.pi * f0_dm * t_dm)
demod = filters.lowpass(modulated * np.cos(2 * np.pi * f0_dm * t_dm), fs_dm, 60.0) * 2
print(f"max |demodulated - g| = {np.max(np.abs(demod - g_base)):.4f}"
      f"   (peak of g = {np.max(np.abs(g_base)):.4f})")

fig, ax = plt.subplots(figsize=(9, 3))
ax.plot(t_dm, g_base, color="#999", lw=1.4, label="original g")
ax.plot(t_dm, demod, "--", color="#d62728", label="demodulated")
ax.set_xlim(0.2, 0.8); ax.legend(fontsize=8); ax.grid(alpha=0.25)
plt.show()"""),
        md(r"""### 04-5 rect で Plancherel の誤差が大きい理由

グリッドが有限なので、$\mathrm{rect}$ の変換 sinc は **打ち切られる**。
sinc の裾は $1/\xi$ でしか減らないため、切り捨てたエネルギーが無視できない。
ガウス関数は両側とも急速に減衰するので、同じグリッドでも誤差が桁違いに小さい。

さらに、不連続点をグリッド上でどう表現するかにも依存する
(端点の値を 1 にするか 1/2 にするかで $O(dx)$ の差が出る)。"""),
        code("""\
print(f"{'grid points':>12} {'gaussian rel.err':>18} {'rect rel.err':>14}")
for n_pts in [1024, 4096, 16384]:
    xg = np.linspace(-8, 8, n_pts)
    dt_ = xg[1] - xg[0]
    for label, fx in [("g", np.exp(-np.pi * xg**2)), ("r", (np.abs(xg) <= 0.5).astype(float))]:
        F = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(fx))) * dt_
        xi_ = np.fft.fftshift(np.fft.fftfreq(n_pts, d=dt_))
        e_t = np.sum(np.abs(fx) ** 2) * dt_
        e_f = np.sum(np.abs(F) ** 2) * (xi_[1] - xi_[0])
        if label == "g":
            eg = abs(e_t - e_f) / e_t
        else:
            er = abs(e_t - e_f) / e_t
    print(f"{n_pts:12d} {eg:18.2e} {er:14.2e}")"""),
        md(r"""## 05 章 — 畳み込みとフィルタ"""),
        md(r"""### 05-1 交換則

> $f*g = g*f$ を確かめ、畳み込み定理から見ると自明である理由を述べよ。

畳み込み定理は $\widehat{f*g} = \hat f\,\hat g$。右辺は複素数の掛け算なので可換である。
変換が単射(逆変換が存在する)ことから、時間側でも $f*g=g*f$ が従う。
定義の積分で変数変換 $u \to x-u$ をしても示せるが、周波数側なら 1 行で済む。"""),
        code("""\
rng_c = np.random.default_rng(0)
f_c, g_c = rng_c.normal(size=64), rng_c.normal(size=40)
print(f"max |f*g - g*f| = {np.max(np.abs(np.convolve(f_c, g_c) - np.convolve(g_c, f_c))):.2e}")
n_pad = f_c.size + g_c.size - 1
prod = np.fft.rfft(f_c, n_pad) * np.fft.rfft(g_c, n_pad)
print(f"max |conv - IFFT(F·G)| = "
      f"{np.max(np.abs(np.convolve(f_c, g_c) - np.fft.irfft(prod, n_pad))):.2e}")"""),
        md(r"""### 05-2 移動平均の周波数応答

> 応答が $\frac{\sin(\pi k\xi)}{k\sin(\pi\xi)}$ になり、零点が $\xi=m/k$ に来ることを示せ。

長さ $k$ の移動平均は $h[n]=1/k$($0\le n<k$)。その DTFT は等比級数の和で

$$
H(\xi) = \frac{1}{k}\sum_{n=0}^{k-1} e^{-2\pi i n\xi}
= \frac{1}{k}\,\frac{1-e^{-2\pi i k\xi}}{1-e^{-2\pi i \xi}}
$$

絶対値を取ると $\left|\frac{\sin(\pi k\xi)}{k\sin(\pi\xi)}\right|$。
分子が 0 になるのは $k\xi$ が整数のとき、つまり $\xi=m/k$。
ただし $m$ が $k$ の倍数のときは分母も 0 になり、そこは通過域(利得 1)である。"""),
        code("""\
k = 8
xi_d = np.linspace(0, 0.5, 4001)
H = np.abs(np.sin(np.pi * k * xi_d) / (k * np.sin(np.pi * xi_d) + 1e-300))
h = np.ones(k) / k
H_num = np.abs(np.fft.rfft(h, 8000))[: xi_d.size]
xi_num = np.fft.rfftfreq(8000)[: xi_d.size]
print(f"zeros predicted at ξ = m/k: {[round(m / k, 4) for m in range(1, k // 2 + 1)]}")
dips = xi_num[1:-1][(H_num[1:-1] < H_num[:-2]) & (H_num[1:-1] < H_num[2:])]
print(f"zeros measured           : {[round(float(v), 4) for v in dips[:4]]}")

fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(xi_d, H, label="|sin(πkξ)/(k sin πξ)|")
for m in range(1, k // 2 + 1):
    ax.axvline(m / k, color="#d62728", ls=":", lw=0.8)
ax.set_xlabel("normalised frequency ξ"); ax.legend(fontsize=8); ax.grid(alpha=0.25)
ax.set_title(f"moving average, k = {k}")
plt.show()"""),
        md(r"""### 05-3 ガウス同士の畳み込み

> 熱方程式の Green 関数で初期条件をガウスにし、結果が再びガウスになることを示せ。

分散が足し算になる。$N(0,\sigma_1^2) * N(0,\sigma_2^2) = N(0,\sigma_1^2+\sigma_2^2)$。
熱方程式では $\sigma^2_{\text{kernel}} = 2\alpha t$ なので、
初期幅 $\sigma_0$ のガウスは時刻 $t$ で $\sqrt{\sigma_0^2 + 2\alpha t}$ に広がる。"""),
        code("""\
L_h, n_h, alpha_h = 40.0, 2048, 0.5
xh = np.linspace(-L_h / 2, L_h / 2, n_h, endpoint=False)
dxh = xh[1] - xh[0]
sigma0 = 0.8
u0_h = np.exp(-xh**2 / (2 * sigma0**2)) / (sigma0 * np.sqrt(2 * np.pi))
print(f"{'t':>6} {'measured σ':>12} {'sqrt(σ0²+2αt)':>16}")
for t_h in [0.5, 2.0, 8.0]:
    green_h = np.exp(-xh**2 / (4 * alpha_h * t_h)) / np.sqrt(4 * np.pi * alpha_h * t_h)
    u_h = np.fft.ifft(np.fft.fft(u0_h) * np.fft.fft(np.fft.ifftshift(green_h))).real * dxh
    w = u_h / np.trapezoid(u_h, xh)
    sig = float(np.sqrt(np.trapezoid(xh**2 * w, xh)))
    print(f"{t_h:6.1f} {sig:12.5f} {np.sqrt(sigma0**2 + 2 * alpha_h * t_h):16.5f}")"""),
        md(r"""### 05-4 因果的フィルタと位相遅れ

> 片側の指数移動平均を実装し、位相遅れが出ることを示せ。

両側フィルタ(対称なカーネル)は周波数応答が実数なので位相を回さない。
その代わり **未来の値を使う**。因果的フィルタは過去だけを使うので実装できるが、
応答が複素数になり、周波数ごとに位相が遅れる。

バックテストで両側フィルタを使うと未来情報が漏れる(look-ahead bias)。
09 章で触れた注意点の実体がこれである。"""),
        code("""\
fs_p = 500.0
t_p = np.arange(0, 2.0, 1 / fs_p)
x_p = signals.sine(t_p, 3.0)

def ema(x, alpha):
    out = np.empty_like(x)
    out[0] = x[0]
    for i in range(1, x.size):
        out[i] = alpha * x[i] + (1 - alpha) * out[i - 1]
    return out

y_causal = ema(x_p, 0.05)
y_two_sided = filters.smooth_gaussian(x_p, sigma=12.0)
lag = int(np.argmax(np.correlate(x_p, y_causal, mode="full")) - (x_p.size - 1))
print(f"causal EMA   lag = {abs(lag) / fs_p * 1000:6.1f} ms")
lag2 = int(np.argmax(np.correlate(x_p, y_two_sided, mode="full")) - (x_p.size - 1))
print(f"two-sided    lag = {abs(lag2) / fs_p * 1000:6.1f} ms  (uses the future)")

fig, ax = plt.subplots(figsize=(9, 3))
ax.plot(t_p, x_p, color="#999", lw=1, label="input")
ax.plot(t_p, y_causal, label="causal EMA")
ax.plot(t_p, y_two_sided, "--", label="two-sided Gaussian")
ax.set_xlim(0.5, 1.5); ax.legend(fontsize=8); ax.grid(alpha=0.25)
plt.show()"""),
        md(r"""### 05-5 遷移帯とリンギング

> 遷移帯の幅を変えてオーバーシュートを測れ。

遷移帯が広いほど、時間側のインパルス応答が短くなり、リンギングが減る。
極限で遷移帯 0(理想フィルタ)は sinc になり、Gibbs の 8.95% が残る。"""),
        code("""\
fs_r2 = 1000.0
t_r2 = np.arange(0, 1.0, 1 / fs_r2)
step2 = (t_r2 > 0.5).astype(float)
fr2 = np.fft.rfftfreq(t_r2.size, d=1 / fs_r2)
spec2 = np.fft.rfft(step2)
cut = 40.0
print(f"{'transition width':>18} {'overshoot %':>13}")
for width in [1e-6, 5.0, 20.0, 60.0, 150.0]:
    mask = 0.5 * (1 - np.tanh((fr2 - cut) / max(width, 1e-6)))
    y = np.fft.irfft(spec2 * mask, n=t_r2.size)
    print(f"{width:18.1f} {(y.max() - 1.0) * 100:13.2f}")
print("\\n遷移帯を広げるとリンギングが単調に減る")"""),
        md(r"""## 06 章 — DFT・FFT・標本化"""),
        md(r"""### 06-1 ビンの周波数刻み

> $f_s=1000$、$N=250$ のときの刻みは何 Hz か。

$\Delta f = f_s / N = 1000/250 = 4$ Hz。分解能は **観測時間の逆数** でもある
($N/f_s = 0.25$ s なので $1/0.25 = 4$ Hz)。同じことを 2 通りに言っているだけである。"""),
        code("""\
fs_b, N_b = 1000.0, 250
fr = transforms.fft_freqs(N_b, fs_b)
print(f"Δf = fs/N = {fs_b / N_b} Hz   measured spacing = {fr[1] - fr[0]} Hz")
print(f"observation time = N/fs = {N_b / fs_b} s   -> 1/T = {fs_b / N_b} Hz")"""),
        md(r"""### 06-2 折り返し

> $f_s=100$ Hz で 70 Hz の波はどこに alias するか。

Nyquist は 50 Hz。$70 > 50$ なので折り返して $|100 - 70| = 30$ Hz に現れる。
一般に $f_{\text{alias}} = |f - f_s \cdot \mathrm{round}(f/f_s)|$。"""),
        code("""\
fs_a = 100.0
t_a = np.arange(0, 1.0, 1 / fs_a)
x_a = signals.sine(t_a, 70.0)
fr_a, amp_a = transforms.amplitude_spectrum(x_a, fs_a)
print(f"peak at {fr_a[np.argmax(amp_a)]:.1f} Hz  (input was 70 Hz, fs = 100 Hz)")

t_fine = np.arange(0, 0.2, 1 / 2000.0)
fig, ax = plt.subplots(figsize=(9, 3))
ax.plot(t_fine, signals.sine(t_fine, 70.0), color="#bbb", lw=1, label="70 Hz (true)")
ax.plot(t_fine, signals.sine(t_fine, 30.0), color="#2ca02c", lw=1, label="30 Hz (alias)")
ax.plot(t_a[t_a < 0.2], x_a[t_a < 0.2], "o", color="#d62728", ms=5, label="samples")
ax.set_xlim(0, 0.2); ax.legend(fontsize=8); ax.grid(alpha=0.25)
ax.set_title("the samples cannot tell 70 Hz from 30 Hz")
plt.show()"""),
        md(r"""### 06-3 窓の比較

> Hann・Hamming・Blackman で漏れの裾と主葉幅を比べよ。

トレードオフは常に「主葉の幅 対 サイドローブの高さ」である。
Blackman は裾が最も低いが主葉が広く、近接した 2 つのトーンを分離できなくなる。"""),
        code("""\
from scipy import signal as sps_w
n_w = 512
print(f"{'window':>10} {'main lobe (bins)':>18} {'peak sidelobe (dB)':>20}")
for name in ["boxcar", "hann", "hamming", "blackman"]:
    w = sps_w.get_window(name, n_w)
    W = np.abs(np.fft.rfft(w, 8192))
    W = W / W.max()
    db = 20 * np.log10(W + 1e-16)
    first_null = int(np.argmax(np.diff(db) > 0))
    side = float(db[first_null:].max())
    print(f"{name:>10} {first_null * n_w / 8192 * 2:18.2f} {side:20.1f}")"""),
        md(r"""### 06-4 ゼロ詰め

> ゼロを足すと滑らかに見えるが分解能は上がらないことを示せ。

ゼロ詰めは DTFT を **細かく標本化し直す** だけで、新しい情報を足さない。
2 つのトーンを分離できるかは観測時間 $T$ が決めるので、
ゼロを足しても $1/T$ より細かい構造は現れない。"""),
        code("""\
fs_z = 1000.0
T_z = 0.1                                  # -> resolution 10 Hz
t_z = np.arange(0, T_z, 1 / fs_z)
x_z = signals.sine(t_z, 200.0) + signals.sine(t_z, 206.0)   # 6 Hz apart: unresolvable
print(f"observation time {T_z}s -> resolution {1 / T_z:.0f} Hz; tones are 6 Hz apart\\n")
fig, ax = plt.subplots(1, 3, figsize=(12, 3), sharey=True)
for a_, pad in zip(ax, [1, 8, 64], strict=True):
    n_pad = int(x_z.size * pad)
    sp = np.abs(np.fft.rfft(x_z, n_pad))
    fr_z = np.fft.rfftfreq(n_pad, d=1 / fs_z)
    sel = (fr_z > 180) & (fr_z < 230)
    a_.plot(fr_z[sel], sp[sel] / sp.max(), "o-", ms=2.5)
    a_.set_title(f"zero-pad ×{pad}", fontsize=9); a_.grid(alpha=0.25)
    peaks = fr_z[sel][1:-1][(sp[sel][1:-1] > sp[sel][:-2]) & (sp[sel][1:-1] > sp[sel][2:])]
    print(f"zero-pad ×{pad:2d}: {len(peaks)} peak(s) in 180-230 Hz")
plt.tight_layout()
plt.show()
print("\\nどれだけ詰めても山は 1 つのまま。分解能は観測時間で決まっている")"""),
        md(r"""## 07 章 — 時間周波数解析"""),
        md(r"""### 07-1 窓幅のトレードオフ

> `nperseg` を変えて時間分解能と周波数分解能が逆に動くことを示せ。

時間分解能は $\Delta t \approx N/f_s$、周波数分解能は $\Delta f \approx f_s/N$。
積は $\Delta t \cdot \Delta f \approx 1$ で、$N$ をどう選んでも改善しない。"""),
        code("""\
fs_tf = 2000.0
t_tf = np.arange(0, 2.0, 1 / fs_tf)
x_tf = signals.chirp(t_tf, 50.0, 700.0)
print(f"{'nperseg':>9} {'Δt [ms]':>10} {'Δf [Hz]':>10} {'product':>9}")
for nps in [64, 256, 1024]:
    f_, tt_, S_ = transforms.stft(x_tf, fs_tf, nperseg=nps, noverlap=nps // 2)
    dt_res = nps / fs_tf * 1000
    df_res = fs_tf / nps
    print(f"{nps:9d} {dt_res:10.2f} {df_res:10.2f} {dt_res / 1000 * df_res:9.2f}")"""),
        md(r"""### 07-2 バースト検出

> CWT で 200 Hz バーストの中心時刻を推定し、STFT と比べよ。"""),
        code("""\
def morlet_cwt2(x_sig, fs_w, freqs_w, f_c=1.0, n_sigma=6.0):
    out = np.empty((freqs_w.size, x_sig.size), dtype=complex)
    for i, f in enumerate(freqs_w):
        s = f_c / f
        half = int(n_sigma * s * fs_w / 2)
        tt = np.arange(-half, half + 1) / fs_w
        psi = np.pi**-0.25 * np.exp(2j * np.pi * f_c * tt / s) * np.exp(-(tt / s) ** 2 / 2)
        out[i] = np.convolve(x_sig, np.conj((psi / np.sqrt(s))[::-1]), mode="same") / fs_w
    return out

fs_b2 = 1000.0
t_b2 = np.arange(0, 2.0, 1 / fs_b2)
true_centre = 0.4
x_b2 = np.exp(-((t_b2 - true_centre) / 0.03) ** 2) * np.sin(2 * np.pi * 200 * t_b2) \
       + 0.3 * np.sin(2 * np.pi * 8 * t_b2)

fq = np.logspace(np.log10(120), np.log10(320), 30)
W2 = np.abs(morlet_cwt2(x_b2, fs_b2, fq))
cwt_centre = t_b2[np.unravel_index(np.argmax(W2), W2.shape)[1]]

f_s2, t_s2, S2 = transforms.stft(x_b2, fs_b2, nperseg=256, noverlap=192)
band = (f_s2 > 150) & (f_s2 < 250)
stft_centre = t_s2[int(np.argmax(np.abs(S2[band]).sum(axis=0)))]
print(f"true centre {true_centre:.3f} s")
print(f"CWT  estimate {cwt_centre:.3f} s   error {abs(cwt_centre - true_centre) * 1000:5.1f} ms")
print(f"STFT estimate {stft_centre:.3f} s   error {abs(stft_centre - true_centre) * 1000:5.1f} ms")"""),
        md(r"""### 07-3 COLA が破れる理由

矩形窓を 50% ずつ重ねると、重なり和は $1+1=2$ の区間と $1$ の区間が交互になり、
**定数にならない**。逆変換で振幅が周期的に脈打つ。
Hann 窓は $w(t)+w(t+N/2)=1$ を満たすので和が定数になる。"""),
        code("""\
from scipy import signal as sps_c
nps = 256
for name in ["hann", "boxcar"]:
    w = sps_c.get_window(name, nps, fftbins=True)
    acc = np.zeros(nps * 6)
    for start in range(0, acc.size - nps, nps // 2):
        acc[start:start + nps] += w
    core = acc[nps:-nps]
    print(f"{name:>8}: overlap-add sum ranges [{core.min():.3f}, {core.max():.3f}]"
          f"  ripple {(core.max() - core.min()) / core.mean():.3f}")"""),
        md(r"""### 07-4 中心周波数と Q

$f_c$ を上げると wavelet の振動回数が増え、包絡が同じでも **Q が上がる**。
周波数分解能は良くなるが、時間的な広がりが増えて過渡を追えなくなる。
不確定性の予算配分を変えているだけである。"""),
        code("""\
fs_q = 1000.0
print(f"{'f_c':>6} {'Q at 40 Hz':>12} {'time support [ms]':>19}")
for f_c in [0.5, 1.0, 3.0]:
    f_target = 40.0
    s = f_c / f_target
    half = int(6 * s * fs_q / 2)
    tt = np.arange(-half, half + 1) / fs_q
    psi = np.pi**-0.25 * np.exp(2j * np.pi * f_c * tt / s) * np.exp(-(tt / s) ** 2 / 2)
    sp = np.abs(np.fft.fft(psi, n=8192))          # complex wavelet -> full FFT
    fr = np.fft.fftfreq(8192, d=1 / fs_q)
    pos = fr > 0
    above = fr[pos][sp[pos] >= sp[pos].max() / np.sqrt(2)]
    bw = float(above.max() - above.min())
    print(f"{f_c:6.1f} {f_target / bw:12.2f} {tt.size / fs_q * 1000:19.1f}")"""),
        md(r"""### 07-5 スペクトル漏れ

> 窓なしと Hann 窓で、非整数周期の正弦波の漏れを dB で比べよ。

矩形窓(窓なし)は端で信号が跳ぶので、その不連続が広帯域の漏れを生む。
Hann 窓は端で 0 に落ちるので跳びが無く、裾が急速に下がる。"""),
        code("""\
from scipy import signal as sps_l
fs_l, N_l = 1000.0, 512
t_l = np.arange(N_l) / fs_l
x_l = np.sin(2 * np.pi * 100.5 * t_l)          # 100.5 Hz: not an integer number of bins
for name in ["boxcar", "hann"]:
    w = sps_l.get_window(name, N_l)
    sp = np.abs(np.fft.rfft(x_l * w))
    db = 20 * np.log10(sp / sp.max() + 1e-16)
    fr_l = np.fft.rfftfreq(N_l, d=1 / fs_l)
    far = np.abs(fr_l - 100.5) > 20
    print(f"{name:>8}: leakage 20 Hz away from the tone = {db[far].max():6.1f} dB")"""),
        md(r"""## 08 章 — PDE とスペクトル法"""),
        md(r"""### 08-1 単一モードの熱方程式

> $u_0=\sin(mx)$ の解が $e^{-\alpha m^2 t}\sin(mx)$ になることを確かめよ。

$\sin(mx)$ は $\partial_{xx}$ の固有関数で固有値 $-m^2$。
熱方程式は各モードについて $\dot{\hat u} = -\alpha m^2 \hat u$ になるので、
指数減衰する。**高いモードほど速く消える** ので、熱伝導は平滑化作用素である。"""),
        code("""\
L_s, n_s2, alpha_s = 2 * np.pi, 512, 0.2
xs2 = np.linspace(0, L_s, n_s2, endpoint=False)
print(f"{'m':>3} {'t':>5} {'max error':>12} {'decay factor':>14}")
for m in [1, 3, 6]:
    u0_s = np.sin(m * xs2)
    for t_s in [0.5, 2.0]:
        u = spectral.solve_heat_spectral(u0_s, L_s, alpha_s, t_s)
        exact = np.exp(-alpha_s * m**2 * t_s) * np.sin(m * xs2)
        print(f"{m:3d} {t_s:5.1f} {np.max(np.abs(u - exact)):12.2e}"
              f" {np.exp(-alpha_s * m**2 * t_s):14.6f}")"""),
        md(r"""### 08-2 スペクトル微分の収束次数

> 誤差を $N$ に対して描き、差分法と比べよ。

滑らかで周期的な関数に対し、スペクトル微分の誤差は **指数的**($N$ の多項式より速く)に落ちる。
差分法は $O(h^2)$ などの多項式収束にとどまる。
片対数で直線になれば指数収束、両対数で直線なら多項式収束である。"""),
        code("""\
L_d = 2 * np.pi
print(f"{'N':>6} {'spectral':>12} {'2nd-order FD':>14}")
Ns, es, ef = [], [], []
for N_d in [16, 32, 64, 128, 256]:
    xd = np.linspace(0, L_d, N_d, endpoint=False)
    u = np.exp(np.sin(xd))
    exact = np.cos(xd) * u
    spec_err = float(np.max(np.abs(spectral.spectral_derivative(u, L_d, 1) - exact)))
    h = xd[1] - xd[0]
    fd = (np.roll(u, -1) - np.roll(u, 1)) / (2 * h)
    fd_err = float(np.max(np.abs(fd - exact)))
    Ns.append(N_d); es.append(spec_err); ef.append(fd_err)
    print(f"{N_d:6d} {spec_err:12.2e} {fd_err:14.2e}")

fig, ax = plt.subplots(figsize=(7, 3))
ax.semilogy(Ns, es, "o-", label="spectral")
ax.semilogy(Ns, ef, "s--", label="2nd-order finite difference")
ax.set_xlabel("N"); ax.set_ylabel("max error"); ax.legend(fontsize=8); ax.grid(alpha=0.3)
ax.set_title("spectral accuracy is exponential for smooth periodic data")
plt.show()"""),
        md(r"""### 08-3 定在波

> $u_0=\sin(2x)$、$v_0=0$ の波動解が $\cos(2ct)\sin(2x)$ になることを確認せよ。

波動方程式でも $\sin(2x)$ は固有関数で、時間側は $\ddot{\hat u} = -(2c)^2\hat u$。
初速 0 なので余弦解が選ばれる。節(node)が動かないので定在波になる。"""),
        code("""\
L_w2, n_w2, c_w = 2 * np.pi, 512, 1.5
xw = np.linspace(0, L_w2, n_w2, endpoint=False)
u0_w = np.sin(2 * xw)
v0_w = np.zeros_like(xw)
for t_w2 in [0.3, 1.0, 2.5]:
    u = spectral.solve_wave_spectral(u0_w, v0_w, L_w2, c_w, t_w2)
    exact = np.cos(2 * c_w * t_w2) * np.sin(2 * xw)
    print(f"t = {t_w2:4.1f}   max error = {np.max(np.abs(u - exact)):.2e}"
          f"   amplitude = {np.cos(2 * c_w * t_w2):+.4f}")"""),
        md(r"""### 08-4 Poisson を解いて戻す

> $u''=f$ を解き、2 回微分して $f$ に戻るか確かめよ。

周期境界の Poisson は $\hat u_k = -\hat f_k / k^2$($k\ne0$)。
$k=0$ は決まらないので、$f$ の平均が 0 であることが可解条件になり、
解も定数分の不定性を持つ。"""),
        code("""\
L_p, n_p = 2 * np.pi, 512
xp = np.linspace(0, L_p, n_p, endpoint=False)
f_p2 = np.sin(3 * xp) + 0.5 * np.cos(5 * xp)          # zero mean
u_p = spectral.solve_poisson_spectral(f_p2, L_p)
back = spectral.spectral_derivative(u_p, L_p, 2)
print(f"mean of f              = {f_p2.mean():.2e}  (solvability needs 0)")
print(f"max |u'' - f|          = {np.max(np.abs(back - f_p2)):.2e}")
print(f"analytic check: u = -sin(3x)/9 - cos(5x)/50 up to a constant")
analytic = -np.sin(3 * xp) / 9 - 0.5 * np.cos(5 * xp) / 25
print(f"max |u - analytic| after removing means = "
      f"{np.max(np.abs((u_p - u_p.mean()) - (analytic - analytic.mean()))):.2e}")"""),
        md(r"""## 09 章 — 応用"""),
        md(r"""### 09-1 2D の低周波と高周波

> 低周波だけ・高周波だけの再構成を作り、ぼけとエッジになる理由を述べよ。

2 次元でも話は同じである。低周波は緩やかな明暗(面)、高周波は急な変化(輪郭)を担う。
ローパスはエッジを消してぼかし、ハイパスは面を消して輪郭だけを残す。"""),
        code("""\
img = datasets.make_test_image(128)
F2 = np.fft.fftshift(np.fft.fft2(img))
ky, kx = np.meshgrid(np.fft.fftshift(np.fft.fftfreq(128)),
                     np.fft.fftshift(np.fft.fftfreq(128)), indexing="ij")
radius = np.hypot(kx, ky)
low = np.fft.ifft2(np.fft.ifftshift(F2 * (radius < 0.06))).real
high = np.fft.ifft2(np.fft.ifftshift(F2 * (radius >= 0.06))).real
fig, ax = plt.subplots(1, 3, figsize=(11, 3.4))
for a_, im, ttl in zip(ax, [img, low, high],
                       ["original", "low-pass (blur)", "high-pass (edges)"], strict=True):
    a_.imshow(im, cmap="gray"); a_.set_title(ttl, fontsize=9); a_.axis("off")
plt.tight_layout()
plt.show()
print(f"energy kept by low-pass : {np.sum(low**2) / np.sum(img**2) * 100:5.1f} %")
print(f"energy kept by high-pass: {np.sum(high**2) / np.sum(img**2) * 100:5.1f} %")"""),
        md(r"""### 09-2 メル帯域数と再構成誤差

帯域を減らすほど圧縮率は上がるが、細かい周波数構造が失われる。
擬似逆行列でスペクトルを復元し、その誤差で測る。"""),
        code("""\
def mel_fb(n_mels, n_fft, fs_m, fmin=50.0, fmax=3500.0):
    to_mel = lambda f: 2595.0 * np.log10(1.0 + f / 700.0)
    to_hz = lambda m: 700.0 * (10.0 ** (m / 2595.0) - 1.0)
    edges = to_hz(np.linspace(to_mel(fmin), to_mel(fmax), n_mels + 2))
    bins = np.floor((n_fft + 1) * edges / fs_m).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for i in range(n_mels):
        lo_, mid, hi_ = bins[i], bins[i + 1], bins[i + 2]
        if mid > lo_:
            fb[i, lo_:mid] = (np.arange(lo_, mid) - lo_) / (mid - lo_)
        if hi_ > mid:
            fb[i, mid:hi_] = (hi_ - np.arange(mid, hi_)) / (hi_ - mid)
    return fb

fs_m2 = 8000.0
t_m2 = np.arange(0, 1.0, 1 / fs_m2)
x_m2 = sum(np.sin(2 * np.pi * f * t_m2) for f in (220, 440, 880, 1760))
_, _, S_m2 = transforms.stft(x_m2, fs_m2, nperseg=512, noverlap=384)
P = np.abs(S_m2) ** 2
print(f"{'mel bands':>11} {'compression':>13} {'reconstruction rel.err':>24}")
for n_mels in [20, 40, 80]:
    fb = mel_fb(n_mels, 512, fs_m2)
    M = fb @ P
    back = np.linalg.pinv(fb) @ M
    err = float(np.linalg.norm(back - P) / np.linalg.norm(P))
    print(f"{n_mels:11d} {P.shape[0] / n_mels:12.1f}x {err:24.4f}")"""),
        md(r"""### 09-3 Fourier features のスケール

`scale` は使う最高周波数を決める。小さすぎると目的の高周波に届かず、
大きすぎると **ノイズまで当てはめる**(過学習)。
最適値は目的関数の帯域とノイズ水準で決まる。"""),
        code("""\
rng_ff2 = np.random.default_rng(0)
xt2 = np.sort(rng_ff2.uniform(0, 1, 128))
target2 = lambda z: np.sin(2 * np.pi * 9 * z) + 0.4 * np.sin(2 * np.pi * 23 * z)
xq2 = np.linspace(0, 1, 1000)

def ff(z, m, scale):
    b = np.arange(1, m + 1) * scale / m
    ang = 2 * np.pi * np.outer(z, b)
    return np.column_stack([np.ones_like(z), np.cos(ang), np.sin(ang)])

print(f"{'scale':>7} {'clean RMSE':>12} {'noisy RMSE':>12}")
for scale in [4.0, 12.0, 32.0, 64.0]:
    row = []
    for noise in [0.0, 0.25]:
        yt2 = target2(xt2) + noise * rng_ff2.normal(size=xt2.size)
        A = ff(xt2, 16, scale)
        w, *_ = np.linalg.lstsq(A, yt2, rcond=None)
        row.append(float(np.sqrt(np.mean((ff(xq2, 16, scale) @ w - target2(xq2)) ** 2))))
    print(f"{scale:7.1f} {row[0]:12.4f} {row[1]:12.4f}")
print("\\nノイズがあると大きすぎる scale が損をする")"""),
        md(r"""### 09-4 ウェルチの分解能

区間長 `nperseg` を伸ばすと分解能は上がるが、平均する区間数が減って分散が増える。
ピークの高さのばらつきと幅の両方で見ると、トレードオフがはっきりする。"""),
        code("""\
from scipy import signal as sps_w2
rng_w = np.random.default_rng(3)
n_w2 = 4096
t_w3 = np.arange(n_w2)
print(f"{'nperseg':>9} {'segments':>10} {'peak sd over 20 runs':>22} {'half-width [bins]':>19}")
for nps in [64, 256, 1024]:
    peaks = []
    for r in range(20):
        rg = np.random.default_rng(100 + r)
        s = rg.normal(size=n_w2) + 0.6 * np.sin(2 * np.pi * 0.13 * t_w3)
        f_w4, P_w = sps_w2.welch(s, fs=1.0, nperseg=nps, noverlap=nps // 2)
        peaks.append(float(P_w.max()))
    f_w4, P_w = sps_w2.welch(rng_w.normal(size=n_w2) + 0.6 * np.sin(2 * np.pi * 0.13 * t_w3),
                             fs=1.0, nperseg=nps, noverlap=nps // 2)
    half = int(np.sum(P_w >= P_w.max() / 2))
    print(f"{nps:9d} {n_w2 // (nps // 2):10d} {np.std(peaks):22.4f} {half:19d}")"""),
        md(r"""### 09-5 サロゲートの必要性

白色ノイズを帰無仮説に置くと、AR(1) の有色ノイズは低周波にエネルギーが偏っているだけで
「有意なピーク」と判定されてしまう。位相ランダム化サロゲートは
**観測系列自身の振幅スペクトルを保つ** ので、この偏りを帰無分布に織り込む。"""),
        code("""\
from scipy import signal as sps_s2

def peak_stat(x):
    _, P = sps_s2.welch(x, fs=1.0, nperseg=256, noverlap=128)
    return float(P[1:].max())

def ar1(n, phi, rng):
    e = np.zeros(n)
    for i in range(1, n):
        e[i] = phi * e[i - 1] + rng.normal()
    return e

n_trials = 60
white_reject = surrogate_reject = 0
rng_t = np.random.default_rng(7)
for _ in range(n_trials):
    series = ar1(1024, 0.7, rng_t)                   # pure noise: no periodicity
    obs = peak_stat(series)
    white_null = [peak_stat(rng_t.normal(size=1024)) for _ in range(40)]
    mags = np.abs(np.fft.rfft(series))
    sur_null = []
    for _ in range(40):
        ph = rng_t.uniform(0, 2 * np.pi, mags.size)
        ph[0] = 0.0
        sur_null.append(peak_stat(np.fft.irfft(mags * np.exp(1j * ph), n=1024)))
    white_reject += obs > np.quantile(white_null, 0.95)
    surrogate_reject += obs > np.quantile(sur_null, 0.95)
print(f"AR(1) noise, no real periodicity, {n_trials} trials, nominal 5 %:")
print(f"  white-noise null    -> false positives {white_reject / n_trials * 100:5.1f} %")
print(f"  phase-surrogate null-> false positives {surrogate_reject / n_trials * 100:5.1f} %")"""),
        md(r"""---

以上で 01–09 章の演習 40 問の解答が終わりである。

繰り返し出てきたのは **「滑らかさ ↔ 減衰」と「時間 ↔ 周波数」の 2 つの対** である。
矩形波の $1/n$、三角波の $1/n^2$、rect の $1/\xi$、理想フィルタのリンギング、
ゼロ詰めで分解能が上がらないこと、CWT の定 Q — すべて同じ 1 つの構造の別の顔である。

09-5 は少し毛色が違う。ここでの誤りは変換の性質ではなく **帰無仮説の置き方** にある。
道具が正しくても、比較対象を間違えれば結論は間違う。"""),
    ],
)
print("part 9 (10 solutions) done")

# ========================================================================== #
# 11 — capstone: one signal, three lenses
# ========================================================================== #
write_nb(
    "11_capstone_three_lenses",
    [
        md(r"""# 11. キャップストーン — 1 つの信号、3 つの視点

**学習目標**: 同じ 1 つの信号を **フーリエ級数・フーリエ変換・DFT** の 3 つで解析し、
3 者が一致する所と、有限のデータゆえに割れる所を、数値で突き止める。

本書はここまで 3 つの道具を別々の章で扱ってきた。
どれも「関数を波に分ける」という同じことをしているのに、
前提が違うので出てくる数字も違う。その違いを 1 つの信号の上で並べる。

| 視点 | 前提 | 出てくるもの |
|---|---|---|
| フーリエ級数(02–03 章) | 信号は **周期的** | 離散な係数 $c_n$ |
| フーリエ変換(04–05 章) | 信号は **非周期・無限長** | 連続スペクトル $\hat f(\xi)$ |
| DFT / FFT(06–07 章) | 信号は **有限個の標本** | $N$ 個のビン |"""),
        code(SETUP),
        md(r"""## 1. 対象の信号

周期 $T_0 = 1/f_0$ の矩形波を取る。理由は 3 つある。

- 級数の係数が **解析的に分かっている**($c_n \propto 1/n$、奇数次のみ)ので、答え合わせができる
- 不連続を持つので Gibbs・スペクトル漏れ・エイリアシングが **すべて観測できる**
- 03 章の Parseval、06 章の標本化定理が同じ信号で確かめられる

$$
f(t) = \mathrm{sgn}\!\left(\sin(2\pi f_0 t)\right), \qquad
c_n = \frac{2}{i\pi n} \;\;(n \text{ odd}), \quad c_n = 0 \;\;(n \text{ even})
$$"""),
        code("""\
F0 = 5.0                     # fundamental frequency [Hz]
FS = 2000.0                  # sampling rate [Hz]
DURATION = 2.0               # exactly 10 periods

t = np.arange(0, DURATION, 1 / FS)
x = signals.square_wave(t, F0)
print(f"f0 = {F0} Hz   fs = {FS} Hz   duration = {DURATION} s")
print(f"periods captured = {DURATION * F0:.0f}   samples = {t.size}")

fig, ax = plt.subplots(figsize=(9, 2.6))
ax.plot(t, x, lw=1)
ax.set_xlim(0, 0.6); ax.set_xlabel("t [s]"); ax.grid(alpha=0.25)
ax.set_title("the signal every lens will look at")
plt.show()"""),
        md(r"""## 2. 視点 A — フーリエ級数

周期を仮定すると、答えは **可算個の係数** になる。
$b_n = \frac{4}{\pi n}$(奇数 $n$)で、偶数次は消える。"""),
        code("""\
a_ser, b_ser = transforms.trig_coeffs(lambda z: signals.square_wave(z, 1 / (2 * np.pi)),
                                      n_max=15, period=2 * np.pi)
print(f"{'n':>3} {'b_n numeric':>13} {'4/(π n) if odd':>16}")
for n in range(1, 12):
    expect = 4 / (np.pi * n) if n % 2 else 0.0
    print(f"{n:3d} {b_ser[n - 1]:13.6f} {expect:16.6f}")
print(f"\\nmax deviation = "
      f"{max(abs(b_ser[n - 1] - (4 / (np.pi * n) if n % 2 else 0.0)) for n in range(1, 16)):.2e}")"""),
        md(r"""## 3. 視点 B — フーリエ変換

周期性を仮定せず、**有限長の窓を切り出した非周期関数** として変換する。
連続スペクトルが出てくるが、そのピークは級数の線スペクトルと同じ位置に立つ。

違いは「線」か「山」かである。有限の観測窓は、
線スペクトルを窓の変換(矩形窓なら sinc)で **たたみ込んで太らせる**。
これがスペクトル漏れの正体で、07 章で窓関数を選んだ理由でもある。"""),
        code("""\
def cont_ft(tt, ff):
    dt_ = tt[1] - tt[0]
    spec = np.fft.fftshift(np.fft.fft(np.fft.ifftshift(ff))) * dt_
    xi_ = np.fft.fftshift(np.fft.fftfreq(tt.size, d=dt_))
    return xi_, spec

xi, X = cont_ft(t, x)
mag = np.abs(X)
sel = (xi > 0) & (xi < 80)
peak_idx = np.where(sel)[0]
local = peak_idx[1:-1][(mag[peak_idx][1:-1] > mag[peak_idx][:-2])
                       & (mag[peak_idx][1:-1] > mag[peak_idx][2:])]
top = local[np.argsort(mag[local])[::-1][:5]]
print(f"{'peak [Hz]':>11} {'harmonic':>10} {'|X| relative':>14}")
for i in sorted(top, key=lambda j: xi[j]):
    print(f"{xi[i]:11.2f} {xi[i] / F0:10.1f} {mag[i] / mag[top].max():14.4f}")

fig, ax = plt.subplots(figsize=(9, 3))
ax.plot(xi[sel], mag[sel], lw=1)
for n in range(1, 16, 2):
    ax.axvline(n * F0, color="#d62728", ls=":", lw=0.7)
ax.set_xlabel("ξ [Hz]"); ax.set_title("continuous transform: peaks at the odd harmonics")
ax.grid(alpha=0.25)
plt.show()"""),
        md(r"""## 4. 視点 C — DFT

標本化して有限個にすると、答えは $N$ 個のビンになる。
観測長が周期の **整数倍** なので、この場合に限って漏れがほぼ起きない。
基本波のビンは $f_0 / \Delta f = f_0 T$ 番目にちょうど乗る。"""),
        code("""\
freqs, amp = transforms.amplitude_spectrum(x, FS)
df = freqs[1] - freqs[0]
print(f"Δf = fs/N = {df:.4f} Hz   f0 sits on bin {F0 / df:.1f}")
print(f"\\n{'harmonic':>9} {'bin freq [Hz]':>15} {'DFT amplitude':>15} {'4/(π n)':>10}")
for n in range(1, 12, 2):
    idx = int(round(n * F0 / df))
    print(f"{n:9d} {freqs[idx]:15.2f} {amp[idx]:15.5f} {4 / (np.pi * n):10.5f}")"""),
        md(r"""## 5. 3 者を重ねる

同じ図に載せると、3 つが **同じ 1 つの対象の違う標本化** であることが見える。"""),
        code("""\
fig, ax = plt.subplots(figsize=(10, 3.6))
sel_c = (xi > 0) & (xi < 60)
ax.plot(xi[sel_c], mag[sel_c] / mag[sel_c].max(), color="#bbb", lw=1.2,
        label="B: continuous transform (windowed)")
sel_d = (freqs > 0) & (freqs < 60)
ax.stem(freqs[sel_d], amp[sel_d] / amp[sel_d].max(), linefmt="C0-", markerfmt="C0o",
        basefmt=" ", label="C: DFT bins")
ns = np.arange(1, 12, 2)
ax.stem(ns * F0, (4 / (np.pi * ns)) / (4 / np.pi), linefmt="C3--", markerfmt="C3x",
        basefmt=" ", label="A: Fourier series 4/(πn)")
ax.set_xlabel("frequency [Hz]"); ax.set_ylabel("normalised magnitude")
ax.legend(fontsize=8); ax.grid(alpha=0.25)
ax.set_title("one signal, three lenses")
plt.show()"""),
        md(r"""## 6. 一致するところ

### 6a. Parseval — エネルギーは 3 者で同じ

級数でも変換でも DFT でも、エネルギーは保存する。
表現を変えても **総量は動かない** というのが、この本を通じた一番硬い事実である。"""),
        code("""\
e_time = float(np.mean(x**2))
e_series = float(np.sum(b_ser**2) / 2 + a_ser[0] ** 2 / 4 + np.sum(a_ser[1:] ** 2) / 2)
spec_full = np.fft.rfft(x) / x.size
e_dft = float(np.sum(np.abs(spec_full) ** 2 * np.where(
    np.arange(spec_full.size) == 0, 1.0, 2.0)))
print(f"time domain  mean |x|²                = {e_time:.6f}")
print(f"DFT          Σ |X_k|²  (Parseval)     = {e_dft:.6f}")
print(f"series       Σ (aₙ²+bₙ²)/2, 15 terms  = {e_series:.6f}"
      f"   ({e_series / e_time * 100:.1f} % captured)")
print("\\n級数は 15 項で切っているのでその分だけ足りない。切らなければ一致する")"""),
        md(r"""### 6b. 部分和と DFT の低域再構成は同じもの

級数を $N$ 項で切ることと、DFT で高いビンを 0 にすることは同じ操作である。
どちらも「低い波だけで作り直す」。したがって同じ Gibbs が出る。"""),
        code("""\
n_terms = 9
partial = signals.square_wave_partial_sum(t, F0, n_terms)
spec_lp = np.fft.rfft(x)
cutoff_hz = (n_terms + 1) * F0
spec_lp[np.fft.rfftfreq(x.size, 1 / FS) > cutoff_hz] = 0
lowpassed = np.fft.irfft(spec_lp, n=x.size)
print(f"max |series partial sum - DFT low-pass| = {np.max(np.abs(partial - lowpassed)):.4f}")
print(f"overshoot: series {(partial.max() - 1) * 100:5.2f} %"
      f"   DFT {(lowpassed.max() - 1) * 100:5.2f} %   (Gibbs limit 8.95 %)")

fig, ax = plt.subplots(figsize=(9, 3))
ax.plot(t, x, color="#ddd", lw=1, label="square wave")
ax.plot(t, partial, lw=1.4, label=f"series, {n_terms} harmonics")
ax.plot(t, lowpassed, "--", color="#d62728", lw=1.2, label="DFT low-pass, same cutoff")
ax.set_xlim(0.05, 0.35); ax.legend(fontsize=8); ax.grid(alpha=0.25)
plt.show()"""),
        md(r"""## 7. 割れるところ

### 7a. 観測長が周期の整数倍でないと DFT が漏れる

級数と変換は「無限に続く」前提を持つ。DFT は持たない。
観測窓が周期の整数倍でないとき、DFT は端の不連続を **信号の一部として** 読み、
本来無いはずの周波数にエネルギーを配る。"""),
        code("""\
print(f"{'duration [s]':>13} {'periods':>9} {'leakage into non-harmonic bins':>32}")
for dur in [2.0, 2.05, 2.137]:
    tt = np.arange(0, dur, 1 / FS)
    xx = signals.square_wave(tt, F0)
    fr, am = transforms.amplitude_spectrum(xx, FS)
    harmonic = np.zeros(fr.size, dtype=bool)
    for n in range(1, 60, 2):
        harmonic |= np.abs(fr - n * F0) < (fr[1] - fr[0]) * 1.5
    inside = (fr > 0) & (fr < 150)
    leak = float(np.sum(am[inside & ~harmonic] ** 2) / np.sum(am[inside] ** 2))
    print(f"{dur:13.3f} {dur * F0:9.2f} {leak * 100:31.2f} %")
print("\\n整数周期からずれるほど、非調和なビンへエネルギーが漏れる")"""),
        md(r"""### 7b. 標本化が足りないと折り返す

矩形波は帯域無限(高調波が無限に続く)なので、**どんな $f_s$ でも標本化定理を満たせない**。
高調波が必ず折り返してくる。帯域制限は仮定であって、
実信号については確かめるべきことである。"""),
        code("""\
print(f"{'fs [Hz]':>9} {'Nyquist':>9} {'harmonics below Nyquist':>25} "
      f"{'error vs 2000 Hz ref':>22}")
ref_t = np.arange(0, DURATION, 1 / 8000.0)
ref = signals.square_wave(ref_t, F0)
for fs_try in [2000.0, 200.0, 60.0, 30.0]:
    tt = np.arange(0, DURATION, 1 / fs_try)
    xx = signals.square_wave(tt, F0)
    n_harm = int((fs_try / 2) // F0)
    up = np.interp(ref_t, tt, xx)
    err = float(np.sqrt(np.mean((up - ref) ** 2)))
    print(f"{fs_try:9.0f} {fs_try / 2:9.0f} {n_harm:25d} {err:22.4f}")
print("\\n矩形波は帯域無限なので、どの fs でもエイリアシングは残る")"""),
        md(r"""### 7c. 3 者の「周波数」が指しているものは違う

同じ「50 Hz」でも意味が違う。

| 視点 | 50 Hz の意味 |
|---|---|
| 級数 | 第 10 倍音という **番号** |
| 変換 | 連続スペクトルの **1 点** |
| DFT | 幅 $\Delta f$ を持つ **ビン** |

DFT のビンは点ではなく区間なので、
「ピークがビン $k$ に立った」は「周波数が $k\Delta f$ ちょうど」を意味しない。
真の周波数がビンの間にあると、隣り合う 2 本に分かれる(この分割から補間で
真の周波数を推定するのが周波数補間の技法である)。"""),
        code("""\
fs_i = 1000.0
n_i = 512
t_i = np.arange(n_i) / fs_i
df_i = fs_i / n_i
print(f"Δf = {df_i:.4f} Hz")
print(f"{'true f [Hz]':>13} {'top bin':>9} {'2nd bin':>9} {'ratio':>8} {'parabolic est.':>16}")
for f_true in [100.0, 100.5, 101.0]:
    sig_i = np.sin(2 * np.pi * f_true * t_i)
    sp = np.abs(np.fft.rfft(sig_i))
    k = int(np.argmax(sp))
    alpha, beta, gamma = sp[k - 1], sp[k], sp[k + 1]
    delta = 0.5 * (alpha - gamma) / (alpha - 2 * beta + gamma)
    nb = k - 1 if alpha > gamma else k + 1
    print(f"{f_true:13.2f} {k * df_i:9.2f} {nb * df_i:9.2f} "
          f"{min(alpha, gamma) / beta:8.3f} {(k + delta) * df_i:16.3f}")"""),
        md(r"""## 8. まとめ — どれを使うか

```{admonition} 3 つの視点の選び方
:class: tip
- **本当に周期的** で、係数そのものに意味があるなら **級数**(倍音構造・音色)
- **理論を導きたい** なら **変換**(畳み込み定理・微分・不確定性はここが一番きれい)
- **手元にデータがある** なら **DFT** 以外の選択肢は無い。ただし
  「有限長」「離散」という 2 つの仮定が、漏れとエイリアシングとして必ず現れる

3 者は同じ対象の違う近似であって、優劣ではない。
DFT の結果を読むときに級数と変換の言葉で考えられることが、この本の目的だった。
```"""),
        md(r"""```{admonition} 姉妹本との接続
:class: note
- `analytics/linear_algebra` — DFT は正規直交基底への射影であり、DFT 行列はユニタリ行列である。
  基底変換としての見方はそちらが詳しい
- `analytics/laplace` — ラプラス変換は $s = \sigma + i\omega$ の複素平面に広げた版で、
  $\sigma = 0$ の虚軸上がフーリエ変換にあたる
- `analytics/differential_equation` — 08 章のスペクトル法は PDE 側から見ると
  固有関数展開そのものである
```"""),
        md(r"""## Exercises

1. **三角波で同じことをする**: 本章の 3 視点を三角波で繰り返し、
   係数減衰が $1/n^2$ になること、Gibbs が出ないことを確かめよ。
2. **窓を変える**: 7a の漏れの実験で Hann 窓を掛けると漏れがどれだけ減るか測れ。
   減る代わりに何を失うか。
3. **帯域制限した矩形波**: 高調波を 15 次で打ち切った信号を作り、
   標本化定理を満たす $f_s$ を求め、7b の誤差が 0 に落ちることを確かめよ。
4. **周波数補間**: 7c の放物線補間の誤差を、真の周波数をビンの間で動かして測れ。
   どの位置で最も誤差が大きいか。
5. **逆問題**: DFT の振幅だけを保って位相をランダム化した信号を作り、
   波形がどう変わるかを見よ。位相が担っている情報は何か。"""),
    ],
)
print("part 10 (11 capstone) done")

print("ALL NOTEBOOKS GENERATED")
