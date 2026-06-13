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
        md(r"""## Invariant / Energy — 熱: 質量保存・エネルギー散逸

$k=0$ モード($\hat u_0$)は $e^{-\alpha\cdot 0\cdot t}=1$ で不変。つまり **総量(質量)
$\int u\,dx$ は保存**します。一方で **エネルギー $\int u^2\,dx$ は単調に減少**(散逸)します。"""),
        code("""\
# Mass (∫u dx) is conserved; energy (∫u² dx) dissipates.
print(f"{'t':>6} {'mass ∫u':>12} {'energy ∫u²':>14}")
for ti in [0.0, 0.05, 0.2, 1.0]:
    u = spectral.solve_heat_spectral(u0, L, alpha, ti)
    print(f"{ti:6.2f} {np.trapezoid(u, x):12.4f} {np.trapezoid(u**2, x):14.4f}")"""),
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
            md(r"""## Application & TODO

応用: 分光・回折(空間版フーリエ変換)、量子力学(位置と運動量の不確定性)、
通信(帯域と時間長)。本書では 06 章で離散版(DFT)、05 章で畳み込み定理へ接続します。

```{admonition} TODO(発展として追記予定)
:class: tip
- Plancherel の数値検証(時間と周波数のエネルギー一致)
- 微分・平行移動・スケーリングの変換性質(表)
- デルタ関数と定数関数の変換(超関数、05 章と接続)
- 解析的フーリエ変換を SymPy で導出(`sympy.fourier_transform`)
```"""),
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
            md(r"""## Application & TODO

応用: 画像のぼかし/輪郭抽出(09 章の 2D 版)、音声の帯域分割、移動平均(金融)、
微分方程式の Green 関数(畳み込みで解を表す)。

```{admonition} TODO(発展として追記予定)
:class: tip
- デルタ関数 δ(畳み込みの単位元)と超関数の入口を丁寧に
- Green 関数: 線形 PDE の解 = 入力 ∗ インパルス応答
- 理想フィルタ(ブリックウォール)の弊害(リンギング)と実用フィルタ(Butterworth 等)
- バンドパス/ハイパスでの特徴抽出デモ
```"""),
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
            md(r"""## Application & TODO

応用: 音声・音楽(音符の検出)、機械の異常振動、脳波(EEG)、レーダー。

```{admonition} TODO(発展として追記予定)
:class: tip
- wavelet 変換: 低周波は長い窓・高周波は短い窓と、周波数で分解能を変える
- 連続 wavelet 変換(CWT)のスカログラム(`scipy.signal.cwt` か `pywt`)
- 窓関数の種類(Hann/Gaussian)と再構成(COLA 条件)
- 定 Q 変換(音楽の音階に合わせた対数周波数軸)
```"""),
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
        md(r"""## TODO(発展として追記予定)

```{admonition} TODO
:class: tip
- 実画像(`scikit-image` の `data.camera()` 等)での 2D FFT(`pip install -e ".[extras]"`)
- 音声 WAV の読み込みとメル尺度スペクトログラム
- Fourier features を使った小さな回帰デモ(高周波関数の学習)
- 金融: ウェルチ法(平均ピリオドグラム)とサロゲート検定で偶然のピークを棄却
```"""),
    ],
)
print("part 8 (07, 09) done")
print("ALL NOTEBOOKS GENERATED")
